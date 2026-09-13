import sys
from pathlib import Path
APP = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(APP), str(APP / 'vendor')]
import json
import io
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import uuid
from musiclib import metadata, playlists
from musiclib.storage import Library, Transaction, atomic, digest
from musiclib.engine import Engine, inventory, scan_catalog
from musiclib.metadata import Tags
from musiclib.picard import commands, config_text
from musiclib import ui


def ident(number):
    return str(uuid.UUID(int=number))


class TaggedIdentifier:
    """Deterministic integration seam: real audio/tags, no external services."""
    def identify(self, paths, kind, work):
        result = {}
        for path in paths:
            try:
                tags = metadata.read(path)
                if tags.identified:
                    result[path] = tags
            except Exception:
                pass
        return result


class LibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = tempfile.TemporaryDirectory()
        cls.samples = {}
        ffmpeg = shutil.which('ffmpeg') or '/opt/homebrew/bin/ffmpeg'
        for ext in ('.flac', '.mp3', '.m4a'):
            p = Path(cls.fixtures.name) / ('tone' + ext)
            subprocess.run([ffmpeg, '-loglevel', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=0.1', str(p)], check=True)
            cls.samples[ext] = p

    @classmethod
    def tearDownClass(cls):
        cls.fixtures.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lib = Library(Path(self.tmp.name) / 'Music')
        c = self.lib.config()
        c['format_policy'] = 'flac'
        self.lib.save_config(c)
        self.engine = Engine(self.lib, identifier=TaggedIdentifier())

    def tearDown(self):
        self.tmp.cleanup()

    def audio(self, relative, record=1, group=10, track=1, disc=1, discs=1, artist='Artist', albumartist='Artist', album='Album'):
        path = self.lib.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.samples[path.suffix], path)
        tags = Tags(artist=artist, albumartist=albumartist, album=album, title='Song ' + str(record),
                    year='1997', track=track, disc=disc, discs=discs, total=2,
                    recording=ident(record), release=ident(group + 100), group=ident(group), release_track=ident(1000 + disc * 100 + track))
        metadata.write_release(path, tags)
        return path

    def incoming(self, kind, folder, ext='.flac', **kwargs):
        key = 'releases_incoming' if kind == 'releases' else 'playlists'
        relative = self.lib.rel(self.lib.paths[key] / folder / ('input-' + str(uuid.uuid4()) + ext))
        return self.audio(relative, **kwargs)

    def test_roundtrip_tags_three_formats(self):
        for ext in self.samples:
            p = self.incoming('playlists', ext, ext=ext, albumartist='Various Artists', discs=2, disc=2)
            t = metadata.read(p)
            self.assertTrue(t.identified)
            self.assertEqual(t.albumartist, 'Various Artists')
            self.assertEqual((t.disc, t.discs, t.year), (2, 2, '1997'))

    def test_first_run_remembers_policy(self):
        other = Library(Path(self.tmp.name) / 'Other')
        self.assertIsNone(other.config()['format_policy'])
        c = other.config(); c['format_policy'] = 'both'; other.save_config(c)
        self.assertEqual(Library(other.root).config()['format_policy'], 'both')
        for p in other.paths.values():
            self.assertTrue(p.is_dir())

    def test_legacy_albums_incoming_is_renamed_without_copying(self):
        root = Path(self.tmp.name) / 'Legacy'
        legacy = root / '2. New Downloads/1. Albums incoming'
        legacy.mkdir(parents=True)
        marker = legacy / 'release-marker.txt'
        marker.write_text('unchanged')
        inode = marker.stat().st_ino
        migrated = Library(root)
        new_marker = migrated.paths['releases_incoming'] / marker.name
        self.assertFalse(legacy.exists())
        self.assertEqual(new_marker.read_text(), 'unchanged')
        self.assertEqual(new_marker.stat().st_ino, inode)

    def test_flat_playlist_and_relative_paths(self):
        src = self.incoming('playlists', 'Sunday')
        original = digest(src)
        report = self.engine.run()
        self.assertEqual(report['status'], 'IMPORT COMPLETE')
        self.assertFalse(src.exists())
        files = metadata.files(self.lib.paths['tracks'])
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].parent, self.lib.paths['tracks'])
        m3u = next(self.lib.paths['m3u'].glob('*.m3u'))
        self.assertTrue(all(not Path(line).is_absolute() for line in m3u.read_text().splitlines() if line and not line.startswith('#')))
        backups = list((self.lib.recovery / report['transaction'] / 'before').iterdir())
        self.assertIn(original, [digest(p) for p in backups])

    def test_format_preference_both_and_fallback(self):
        for policy, expected in [('flac', {'.flac'}), ('mp3', {'.mp3'}), ('both', {'.flac', '.mp3'})]:
            with self.subTest(policy=policy):
                other = Library(Path(self.tmp.name) / policy)
                previous = self.lib; self.lib = other
                c = other.config(); c['format_policy'] = policy; other.save_config(c)
                self.incoming('playlists', 'Mix', ext='.flac')
                self.incoming('playlists', 'Mix', ext='.mp3')
                Engine(other, identifier=TaggedIdentifier()).run()
                self.assertEqual({p.suffix for p in metadata.files(other.paths['tracks'])}, expected)
                self.lib = previous
        self.incoming('playlists', 'Only MP3', ext='.mp3')
        self.engine.run()
        self.assertEqual(metadata.files(self.lib.paths['tracks'])[0].suffix, '.mp3')

    def test_promotion_prefers_loose_flac_and_retags(self):
        self.incoming('playlists', 'First', group=20, ext='.flac')
        self.engine.run()
        self.incoming('releases', 'Full release', group=10, ext='.mp3')
        report = self.engine.run()
        self.assertEqual(report['promoted'], 1)
        self.assertEqual(metadata.files(self.lib.paths['tracks']), [])
        files = metadata.files(self.lib.paths['releases'])
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].suffix, '.flac')
        self.assertEqual(metadata.read(files[0]).group, ident(10))
        m3u = next(self.lib.paths['m3u'].glob('*.m3u'))
        self.assertIn('1. Releases', m3u.read_text())
        for line in m3u.read_text().splitlines():
            if line and not line.startswith('#'):
                self.assertTrue((m3u.parent / line).is_file())

    def test_compilation_multidisc_one_folder(self):
        self.incoming('releases', 'Compilation', record=1, disc=1, discs=2, artist='One', albumartist='Various Artists')
        self.incoming('releases', 'Compilation', record=2, disc=2, discs=2, artist='Two', albumartist='Various Artists')
        self.engine.run()
        files = metadata.files(self.lib.paths['releases'])
        self.assertEqual(len(files), 2)
        self.assertEqual(len({p.parent for p in files}), 1)
        self.assertIn('Various Artists [1997]', files[0].parent.name)
        self.assertTrue(any('01-01' in p.name for p in files))
        self.assertTrue(any('02-01' in p.name for p in files))

    def test_same_recording_repeated_release_slots_preserved(self):
        self.incoming('releases', 'Release', track=1)
        self.incoming('releases', 'Release', track=2)
        self.engine.run()
        self.assertEqual(len(metadata.files(self.lib.paths['releases'])), 2)

    def test_mixed_releases_in_one_folder_are_split_by_mbid(self):
        self.incoming('releases', 'Mixed', record=1, group=10)
        self.incoming('releases', 'Mixed', record=2, group=20)
        report = self.engine.run()
        self.assertEqual(report['pending'], 0)
        files = metadata.files(self.lib.paths['releases'])
        self.assertEqual(len(files), 2)
        self.assertEqual(len({p.parent for p in files}), 2)

    def test_unresolved_file_does_not_block_identified_release_sibling(self):
        self.incoming('releases', 'Mixed', record=1, group=10)
        broken = self.lib.paths['releases_incoming'] / 'Mixed/unknown.mp3'
        broken.write_bytes(b'not audio')
        report = self.engine.run()
        self.assertEqual(report['pending'], 1)
        self.assertEqual(len(metadata.files(self.lib.paths['releases'])), 1)
        self.assertTrue((self.lib.paths['pending'] / 'releases/Mixed/unknown.mp3').exists())

    def test_invalid_audio_pending_playlist_preserves_entry(self):
        p = self.lib.paths['playlists'] / 'Broken/no tags.mp3'
        p.parent.mkdir(parents=True); p.write_bytes(b'not audio')
        report = self.engine.run()
        self.assertEqual(report['status'], 'COMPLETE WITH WARNINGS')
        m3u = next(self.lib.paths['m3u'].glob('*.m3u'))
        lines = [x for x in m3u.read_text().splitlines() if x and not x.startswith('#')]
        self.assertEqual(len(lines), 1)
        self.assertTrue((m3u.parent / lines[0]).exists())

    def test_rebuild_after_manual_move_and_relocation(self):
        self.incoming('playlists', 'Mix')
        self.engine.run()
        audio = metadata.files(self.lib.paths['tracks'])[0]
        audio.rename(audio.with_name('Manual name.flac'))
        relocated = self.lib.root.with_name('Renamed Device')
        self.lib.root.rename(relocated)
        lib = Library(relocated)
        result = Engine(lib).rebuild()
        self.assertEqual(result['changed'], 1)
        self.assertEqual(result['missing'], 0)
        self.assertIn('Manual name.flac', next(lib.paths['m3u'].glob('*.m3u')).read_text())

    def test_rebuild_one_missing_preserved(self):
        p = self.lib.paths['m3u'] / 'Missing.m3u'
        p.write_text('#EXTM3U\n#EXTINF:1,unknown\n../gone.mp3\n')
        untouched = self.lib.paths['m3u'] / 'Untouched.m3u'
        untouched.write_text('#hello\n')
        result = self.engine.rebuild('Missing.m3u')
        self.assertEqual(result['missing'], 1)
        self.assertIn('../gone.mp3', p.read_text())
        self.assertEqual(untouched.read_text(), '#hello\n')

    def test_input_m3u_order_and_repeats(self):
        a = self.incoming('playlists', 'Order', record=1)
        b = self.incoming('playlists', 'Order', record=2)
        (a.parent / 'Order.m3u').write_text(f'#EXTM3U\n{b.name}\n{a.name}\n{b.name}\n')
        self.engine.run()
        m3u = self.lib.paths['m3u'] / 'Order.m3u'
        lines = [x for x in m3u.read_text().splitlines() if x and not x.startswith('#')]
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], lines[2])
        self.assertIn('Song 2', lines[0])

    def test_two_playlists_shared_recording(self):
        self.incoming('playlists', 'One')
        self.incoming('playlists', 'Two')
        self.engine.run()
        self.assertEqual(len(metadata.files(self.lib.paths['tracks'])), 1)
        self.assertEqual(len(list(self.lib.paths['m3u'].glob('*.m3u'))), 2)

    def test_real_collision_disambiguates(self):
        self.incoming('releases', 'First', group=10)
        self.incoming('releases', 'Second', group=20)
        self.engine.run()
        self.assertEqual(len({p.parent for p in metadata.files(self.lib.paths['releases'])}), 2)

    def test_symbolic_link_rejected(self):
        target = Path(self.tmp.name) / 'outside.flac'; target.write_bytes(b'untouched')
        (self.lib.paths['playlists'] / 'link.flac').symlink_to(target)
        with self.assertRaises(ValueError):
            self.engine.run()
        self.assertEqual(target.read_bytes(), b'untouched')

    def test_same_size_not_identity(self):
        a = self.incoming('playlists', 'Mix', record=1)
        b = self.incoming('playlists', 'Mix', record=2)
        self.engine.run()
        self.assertEqual(len(metadata.files(self.lib.paths['tracks'])), 2)

    def test_transaction_failure_rolls_back(self):
        path = self.lib.paths['tracks'] / 'old'; path.write_bytes(b'original')
        new = self.lib.paths['tracks'] / 'new'
        tx = Transaction(self.lib); tx.add(path, data=b'replaced'); tx.add(new, data=b'new')
        def fault(index):
            if index == 1: raise OSError('disk failure')
        with self.assertRaises(OSError): tx.commit(fault)
        self.assertEqual(path.read_bytes(), b'original')
        self.assertFalse(new.exists())

    def test_crash_recovery_with_root_move(self):
        path = self.lib.paths['tracks'] / 'old'; path.write_bytes(b'original')
        tx = Transaction(self.lib); tx.add(path, data=b'replaced')
        def crash(index): raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt): tx.commit(crash)
        renamed = self.lib.root.with_name('Moved'); self.lib.root.rename(renamed)
        lib = Library(renamed); self.assertEqual(len(lib.recover()), 1)
        self.assertEqual((lib.paths['tracks'] / 'old').read_bytes(), b'original')
        self.assertEqual(lib.recover(), [])

    def test_recovery_refuses_external_edits(self):
        path = self.lib.paths['tracks'] / 'old'; path.write_bytes(b'original')
        tx = Transaction(self.lib); tx.add(path, data=b'replaced')
        def crash(index): raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt): tx.commit(crash)
        path.write_bytes(b'edited outside')
        with self.assertRaises(RuntimeError): self.lib.recover()
        self.assertEqual(path.read_bytes(), b'edited outside')

    def test_identifier_failure_leaves_originals(self):
        src = self.incoming('releases', 'Keep')
        before = digest(src)
        with patch.object(TaggedIdentifier, 'identify', side_effect=TimeoutError('service unavailable')):
            with self.assertRaises(TimeoutError): self.engine.run()
        self.assertEqual(digest(src), before)
        self.assertFalse(metadata.files(self.lib.paths['releases']))

    def test_keep_both_promotion_retains_formats_and_next_scan(self):
        c = self.lib.config(); c['format_policy'] = 'both'; self.lib.save_config(c)
        self.incoming('playlists', 'Loose', ext='.flac', group=20)
        self.engine.run()
        self.incoming('releases', 'Release', ext='.mp3', group=10)
        self.engine.run()
        catalog = scan_catalog(self.lib)
        self.assertEqual(len(catalog['files']), 2)
        self.assertEqual({e['tags']['group'] for e in catalog['files']}, {ident(10)})
        self.assertEqual({e['kind'] for e in catalog['files']}, {'releases'})
        self.assertFalse(metadata.files(self.lib.paths['tracks']))
        self.assertEqual(self.engine.rebuild()['missing'], 0)

    def test_recovery_exports_original_names(self):
        from recover_originals import export
        source = self.incoming('playlists', 'Recover me')
        relative = self.lib.rel(source)
        original_hash = digest(source)
        result = self.engine.run()
        dest = export(self.lib, self.lib.recovery / result['transaction'])
        self.assertEqual(digest(dest / relative), original_hash)
        self.assertEqual(len(metadata.files(self.lib.paths['tracks'])), 1)

    def test_lock_prevents_second_writer(self):
        with self.lib.lock():
            with self.assertRaises(RuntimeError):
                with Library(self.lib.root).lock():
                    pass

    def test_transaction_rejects_changed_source_before_commit(self):
        path = self.lib.paths['tracks'] / 'original'; path.write_bytes(b'one')
        tx = Transaction(self.lib); tx.add(path, data=b'two')
        path.write_bytes(b'changed')
        with self.assertRaises(RuntimeError): tx.commit()
        self.assertEqual(path.read_bytes(), b'changed')

    def test_transaction_crash_each_boundary(self):
        for boundary in range(3):
            with self.subTest(boundary=boundary):
                lib = Library(Path(self.tmp.name) / ('boundary' + str(boundary)))
                a = lib.paths['tracks'] / 'a'; a.write_bytes(b'old-a')
                b = lib.paths['tracks'] / 'b'; b.write_bytes(b'old-b')
                c = lib.paths['m3u'] / 'playlist.m3u'
                tx = Transaction(lib)
                tx.add(a, data=b'new-a'); tx.add(b); tx.add(c, data=b'#EXTM3U\n')
                def crash(index):
                    if index == boundary: raise KeyboardInterrupt()
                with self.assertRaises(KeyboardInterrupt): tx.commit(crash)
                lib.recover()
                self.assertEqual(a.read_bytes(), b'old-a')
                self.assertEqual(b.read_bytes(), b'old-b')
                self.assertFalse(c.exists())

    def test_pending_rebuild_keeps_existing_audio(self):
        p = self.lib.paths['playlists'] / 'Broken/input.mp3'
        p.parent.mkdir(parents=True); p.write_bytes(b'invalid')
        self.engine.run()
        self.assertEqual(self.engine.rebuild()['missing'], 0)

    def test_appledouble_m3u_ignored(self):
        self.incoming('playlists', 'Mix')
        (self.lib.paths['playlists'] / 'Mix/._Mix.m3u').write_bytes(b'\x00\xffmetadata')
        self.engine.run()
        (self.lib.paths['m3u'] / '._Mix.m3u').write_bytes(b'\x00\xffmetadata')
        self.assertEqual(len(playlists.discover(self.lib)), 1)
        self.assertEqual(self.engine.rebuild()['playlists'], 1)

    def test_tui_uses_phosphor_colour_only_in_terminal(self):
        class Terminal(io.StringIO):
            def isatty(self):
                return True

        terminal = Terminal()
        with patch.object(sys, 'stdout', terminal):
            ui.screen('MUSIC LIBRARY', ['[1] Import Music'])
        output = terminal.getvalue()
        self.assertIn(ui.PHOSPHOR, output)
        self.assertIn(ui.DEEP_BLACK, output)

        plain = io.StringIO()
        with patch.object(sys, 'stdout', plain):
            ui.screen('MUSIC LIBRARY', ['[1] Import Music'])
        self.assertNotIn('\033[', plain.getvalue())

    def test_import_screen_refreshes_folder_counts(self):
        batch = {'kind': 'releases', 'name': 'New release', 'folder': self.lib.paths['releases_incoming'],
                 'files': [Path('one.flac'), Path('two.flac')]}
        shown = []
        with patch('musiclib.ui.inventory', side_effect=[[], [batch]]), \
             patch('musiclib.ui.choice', side_effect=['r', 'b']), \
             patch('musiclib.ui.screen', side_effect=lambda title, lines: shown.append(lines)):
            self.assertTrue(ui.UI(self.lib).import_music())
        self.assertIn('Releases:    0', shown[0])
        self.assertIn('Releases:    1', shown[1])
        self.assertIn('Audio files: 2', shown[1])

    def test_nested_artist_releases_are_separate_batches(self):
        self.audio(self.lib.rel(self.lib.paths['releases_incoming'] / 'Artist/First/01.flac'),
                   record=1, group=10, album='First')
        self.audio(self.lib.rel(self.lib.paths['releases_incoming'] / 'Artist/Second/01.flac'),
                   record=2, group=20, album='Second')
        batches = inventory(self.lib)
        self.assertEqual([b['name'] for b in batches],
                         ['Artist — First', 'Artist — Second'])
        result = self.engine.run()
        self.assertEqual(result['pending'], 0)
        self.assertEqual(len({p.parent for p in metadata.files(self.lib.paths['releases'])}), 2)

    def test_picard_commands_no_obsolete_alias(self):
        result = commands([Path('/a space/track.mp3')], 'releases', 'lookup')
        self.assertIn('LOOKUP clustered', result)
        self.assertNotIn('LOOKUP_CLUSTERED', result)
        self.assertEqual(result[-1], 'REMOVE_ALL')
        self.assertNotIn('QUIT force', result)
        scan = commands([Path('/a')], 'releases', 'scan')
        self.assertNotIn('CLUSTER', scan)
        self.assertIn('SCAN', scan)

    def test_picard_staging_profile_never_prompts(self):
        for strategy in ('lookup', 'scan'):
            profile = config_text(strategy)
            self.assertIn('show_new_user_dialog=false', profile)
            self.assertIn('file_save_warning=false', profile)
            self.assertIn('quit_confirmation=false', profile)
        self.assertIn('ignore_file_mbids=false', config_text('lookup'))
        self.assertIn('ignore_file_mbids=true', config_text('scan'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
