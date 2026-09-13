"""Plan an entire import on copies, then commit audio, catalog and M3Us together."""
from collections import defaultdict
import logging
from pathlib import Path
import shutil
import uuid
from . import metadata, playlists
from .metadata import Tags
from .picard import Picard
from .storage import Transaction, digest, json_bytes


def inventory(lib):
    batches = []
    releases_root = lib.paths['releases_incoming']
    # Scan at any depth. Direct parents merely keep Picard jobs manageable; they
    # never define release identity. Picard can split a mixed folder, and the
    # commit later merges files from unrelated folders by Release Group MBID.
    release_files = metadata.files(releases_root)
    release_groups = defaultdict(list)
    for path in release_files:
        release_groups[path.parent].append(path)
    for folder, audio in sorted(release_groups.items(), key=lambda item: str(item[0]).casefold()):
        relative = folder.relative_to(releases_root)
        if relative == Path('.'):
            # Loose files remain independent jobs. Their MBIDs can still reunite
            # them into the same final release after identification.
            for path in audio:
                batches.append({'kind': 'releases', 'name': path.stem,
                                'folder': releases_root, 'files': [path]})
        else:
            name = ' — '.join(relative.parts)
            batches.append({'kind': 'releases', 'name': name, 'folder': folder, 'files': audio})

    playlists_root = lib.paths['playlists']
    for folder in sorted(playlists_root.iterdir()):
        lib.safe(folder)
        if folder.name.startswith('.'):
            continue
        if folder.is_dir():
            audio = metadata.files(folder)
            if audio:
                batches.append({'kind': 'playlists', 'name': folder.name,
                                'folder': folder, 'files': audio})
        elif folder.suffix.lower() in metadata.AUDIO:
            batches.append({'kind': 'playlists', 'name': folder.stem,
                            'folder': playlists_root, 'files': [folder]})
    return batches


def unique(path, occupied, identity):
    original = path
    i = 0
    while str(path).casefold() in occupied:
        i += 1
        suffix = identity.replace('mb:', '').replace('sha:', '')[:8]
        path = original.with_name(f'{original.stem} ({suffix}{"-" + str(i) if i > 1 else ""}){original.suffix}')
    occupied.add(str(path).casefold())
    return path


def scan_catalog(lib):
    old = lib.catalog()
    cached = {e['path']: e for e in old['files']}
    entries = []
    for kind in ('releases', 'tracks'):
        for path in metadata.files(lib.paths[kind]):
            rel = lib.rel(path)
            sha = digest(path)
            tags = metadata.read(path)
            entries.append({'path': rel, 'id': tags.identity(path), 'sha256': sha,
                            'tags': tags.dict(), 'kind': kind, 'existing': True})
    aliases = old.get('aliases', {}).copy()
    aliases.update({path: e['id'] for path, e in cached.items()})
    return {'version': 1, 'files': entries, 'aliases': aliases}


class Engine:
    def __init__(self, lib, progress=lambda *a: None, identifier=None):
        self.lib, self.progress = lib, progress
        self.identifier = identifier

    def rebuild(self, selected=None):
        catalog = scan_catalog(self.lib)
        policy = self.lib.config()['format_policy'] or 'flac'
        tx = Transaction(self.lib)
        totals = {'checked': 0, 'changed': 0, 'missing': 0, 'playlists': 0}
        targets = playlists.discover(self.lib)
        if selected is not None:
            targets = [p for p in targets if p.name == selected]
            if not targets:
                raise ValueError('La playlist seleccionada ya no existe.')
        for path in targets:
            self.lib.safe(path)
            self.progress('Reconstruyendo ' + path.name, totals['playlists'])
            original = path.read_text(encoding='utf-8-sig')
            content, counts = playlists.repair(original, path, self.lib, catalog, policy)
            if content != original:
                tx.add(path, data=content)
            for key, value in counts.items():
                totals[key] += value
            totals['playlists'] += 1
        tx.add(self.lib.catalog_path, data=json_bytes(catalog))
        tx.commit()
        return totals

    def run(self):
        lib = self.lib
        policy = lib.config()['format_policy']
        if policy is None:
            raise ValueError('Selecciona primero FLAC, MP3 o Keep both.')
        batches = inventory(lib)
        report = {'imported': 0, 'duplicates': 0, 'promoted': 0, 'pending': 0,
                  'playlists': 0, 'warnings': [], 'status': 'IMPORT COMPLETE'}
        if not batches:
            return report
        identifier = self.identifier or Picard(lib, lib.config().get('picard_timeout', 600), self.progress)
        stage = lib.app / 'Staging' / uuid.uuid4().hex
        stage.mkdir(parents=True)
        catalog = scan_catalog(lib)
        old_entries = catalog['files'][:]
        incoming, pending, batch_entries = [], [], []
        original_hashes = {}
        # An exception before commit leaves every input and existing library file intact.
        for bi, batch in enumerate(batches):
            self.progress('Preparando ' + batch['name'], len(batch['files']))
            paths, originals = [], {}
            for i, src in enumerate(batch['files']):
                lib.safe(src)
                sha = digest(src)
                dest = stage / str(bi) / f'{i:06d}{src.suffix.lower()}'
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                if digest(dest) != sha:
                    raise IOError('Error verificando la copia: ' + str(src))
                paths.append(dest)
                originals[dest] = src
                original_hashes[src] = sha
            identified = identifier.identify(paths, batch['kind'], stage / 'picard' / str(bi))
            items = []
            for path in paths:
                src = originals[path]
                tags = identified.get(path)
                if tags is None:
                    pending.append((src, batch, 'Sin identificación fiable; revisa etiquetas y vuelve a colocarlo en incoming.'))
                    items.append({'pending_source': src})
                    continue
                entry = {'path': str(path), 'id': tags.identity(path), 'sha256': digest(path),
                         'tags': tags.dict(), 'kind': 'releases' if batch['kind'] == 'releases' else 'tracks',
                         'source': str(src), 'stage': str(path), 'batch': bi, 'existing': False}
                incoming.append(entry)
                items.append(entry)
            batch_entries.append((batch, items))
        report['warnings'].extend(getattr(identifier, 'warnings', []))
        # Existing releases determine the canonical folder for their release group.
        release_folders = {}
        folder_owners = {}
        for e in old_entries:
            if e['kind'] == 'releases':
                key = Tags(**e['tags']).release_key
                folder = str(Path(e['path']).parent)
                if key:
                    release_folders.setdefault(key, folder)
                    folder_owners.setdefault(folder.casefold(), key)
        for e in incoming:
            if e['kind'] == 'releases':
                t = Tags(**e['tags'])
                if t.release_key not in release_folders:
                    folder = lib.rel(lib.paths['releases'] / t.folder())
                    base = folder
                    counter = 0
                    while folder.casefold() in folder_owners and folder_owners[folder.casefold()] != t.release_key:
                        counter += 1
                        folder = base + f' ({t.release_key[:8]}{("-" + str(counter)) if counter > 1 else ""})'
                    folder_owners[folder.casefold()] = t.release_key
                    release_folders[t.release_key] = folder
        # Release slots distinguish repeated recordings and discs. Loose tracks dedup by recording.
        groups = defaultdict(list)
        for e in old_entries + incoming:
            t = Tags(**e['tags'])
            if e['kind'] == 'releases':
                key = ('release', t.release_key or str(Path(e['path']).parent), t.disc, t.track, e['id'])
            else:
                key = ('track', e['id'])
            groups[key].append(e)
        # Promote loose copies into a release occurrence, preserving other release occurrences.
        slots_by_id = defaultdict(list)
        for key in groups:
            if key[0] == 'release':
                slots_by_id[key[-1]].append(key)
        for key in list(groups):
            if key[0] == 'track' and key[1] in slots_by_id:
                target_key = sorted(slots_by_id[key[1]], key=str)[0]
                for e in groups.pop(key):
                    if e['existing']:
                        report['promoted'] += 1
                    groups[target_key].append(e)
        # Reserve existing filesystem names, including artwork and manual folders.
        occupied = {str(p).casefold() for root in (lib.paths['releases'], lib.paths['tracks'], lib.paths['pending']) for p in root.rglob('*')}
        final, mapping, payloads = [], {}, {}
        for key, members in groups.items():
            # Untouched existing groups are left alone (no historical migration).
            affected = any(not e['existing'] for e in members) or any(e['kind'] == 'tracks' for e in members) and key[0] == 'release'
            if not affected:
                for e in members:
                    final.append(e)
                    mapping[e['path']] = e
                continue
            if policy == 'both':
                formats = defaultdict(list)
                for e in members:
                    formats[Path(e['path']).suffix.lower()].append(e)
                winners = [max(v, key=lambda e: metadata.rank(e, policy)) for v in formats.values()]
            else:
                winners = [max(members, key=lambda e: metadata.rank(e, policy))]
            # Use the release's own tags to name promoted audio; do not fragment compilations.
            release_member = next((e for e in members if e['kind'] == 'releases'), None)
            outputs = []
            for winner in winners:
                e = dict(winner)
                t = Tags(**(release_member or winner)['tags'])
                extension = Path(winner['path']).suffix.lower()
                if key[0] == 'release':
                    folder = release_folders.get(t.release_key, str(Path(release_member['path']).parent))
                    desired = lib.safe(folder) / t.filename(extension)
                    e['kind'] = 'releases'
                else:
                    desired = lib.paths['tracks'] / t.filename(extension)
                if winner['existing'] and winner['kind'] == e['kind']:
                    dest = lib.safe(winner['path'])
                else:
                    dest = unique(desired, occupied, e['id'])
                e['path'] = lib.rel(dest)
                audio_source = Path(winner.get('stage') or lib.safe(winner['path']))
                if release_member and winner is not release_member and winner['tags'] != release_member['tags']:
                    promoted = stage / 'promoted' / (uuid.uuid4().hex + extension)
                    promoted.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(audio_source, promoted)
                    metadata.write_release(promoted, t)
                    audio_source = promoted
                    e['tags'] = metadata.read(promoted).dict()
                    e['sha256'] = digest(promoted)
                if not winner['existing'] or e['path'] != winner['path'] or audio_source != lib.safe(winner['path']):
                    payloads[e['path']] = audio_source
                final.append(e)
                outputs.append(e)
            for member in members:
                same_format = [e for e in outputs if Path(e['path']).suffix.lower() == Path(member['path']).suffix.lower()]
                mapped = max(same_format or outputs, key=lambda e: metadata.rank(e, policy))
                mapping[member['path']] = mapped
                if member['existing']:
                    catalog['aliases'][member['path']] = member['id']
            report['duplicates'] += len(members) - len(winners)
        # Pending originals retain their tags and relative subfolders, avoiding loss of context.
        pending_map = {}
        for src, batch, reason in pending:
            sub = src.relative_to(batch['folder'])
            desired = lib.paths['pending'] / batch['kind'] / metadata.clean(batch['name']) / sub
            dest = unique(desired, occupied, original_hashes[src])
            rel = lib.rel(dest)
            payloads[rel] = src
            entry = {'path': rel, 'id': 'sha:' + original_hashes[src], 'tags': {}, 'kind': 'pending'}
            pending_map[src] = entry
            report['pending'] += 1
            report['warnings'].append(src.name + ': ' + reason)
            logging.warning('Pending %s: %s', src, reason)
        for e in incoming:
            catalog['aliases'][lib.rel(Path(e['source']))] = e['id']
            catalog['aliases']['sha:' + original_hashes[Path(e['source'])]] = e['id']
        catalog['files'] = [{k: v for k, v in e.items() if k not in ('source', 'stage', 'batch', 'existing')} for e in final]
        # Build playlist contents after all deduplication and promotions have resolved paths.
        m3u_writes = {}
        playlist_occupied = {str(p).casefold() for p in playlists.discover(lib)}
        for batch, items in batch_entries:
            if batch['kind'] != 'playlists':
                continue
            entries = [pending_map[e['pending_source']] if 'pending_source' in e else mapping[e['path']] for e in items]
            # If the incoming folder includes an M3U, honor its order, repeats and comments.
            input_m3us = sorted(p for p in batch['folder'].glob('*') if not p.name.startswith('.') and p.suffix.lower() in ('.m3u', '.m3u8'))
            source_entries = {str(Path(e['source']).resolve()): mapping[e['path']] for e in items if 'source' in e}
            source_entries.update({str(src.resolve()): entry for src, entry in pending_map.items()})
            if input_m3us:
                for source_m3u in input_m3us:
                    lib.safe(source_m3u)
                    out = unique(lib.paths['m3u'] / source_m3u.name, playlist_occupied, uuid.uuid4().hex)
                    lines = ['#EXTM3U']
                    used = set()
                    for line in source_m3u.read_text(encoding='utf-8-sig').splitlines():
                        if not line or line.startswith('#'):
                            if line != '#EXTM3U' and not line.startswith(playlists.PREFIX):
                                lines.append(line)
                            continue
                        source_path = str((source_m3u.parent / line).resolve())
                        entry = source_entries.get(source_path)
                        if entry:
                            used.add(source_path)
                            lines.extend(playlists.render([entry], out, lib).splitlines()[1:])
                        else:
                            # Preserve missing entries at their original resolved location.
                            lines.append(playlists.relative(Path(source_path), out))
                            report['warnings'].append(source_m3u.name + ': entrada no localizada: ' + line)
                    m3u_writes[out] = '\n'.join(lines) + '\n'
            else:
                out = unique(lib.paths['m3u'] / (metadata.clean(batch['name'], 210) + '.m3u'), playlist_occupied, uuid.uuid4().hex)
                m3u_writes[out] = playlists.render(entries, out, lib)
        # Add Pending identities for M3U repair during this commit; Pending isn't library content.
        repair_catalog = dict(catalog, files=catalog['files'] + list(pending_map.values()))
        for path in playlists.discover(lib):
            lib.safe(path)
            original = path.read_text(encoding='utf-8-sig')
            updated, counts = playlists.repair(original, path, lib, repair_catalog, policy)
            if updated != original:
                m3u_writes[path] = updated
            if counts['missing']:
                report['warnings'].append(f'{path.name}: {counts["missing"]} entradas sin localizar; se conservan.')
        # No mutation until every payload, backup, M3U and catalog has been prepared.
        self.progress('Guardando de forma recuperable', len(payloads))
        tx = Transaction(lib)
        old_by_path = {e['path']: e['sha256'] for e in old_entries}
        for rel, source in payloads.items():
            tx.add(lib.safe(rel), source=source, expected=old_by_path.get(rel))
        final_paths = {e['path'] for e in final}
        for e in old_entries:
            if e['path'] not in final_paths:
                tx.add(lib.safe(e['path']), expected=e['sha256'])
        for src, sha in original_hashes.items():
            tx.add(src, expected=sha)
        for path, content in m3u_writes.items():
            tx.add(path, data=content)
        tx.add(lib.catalog_path, data=json_bytes(catalog))
        tx.commit()
        try:
            shutil.rmtree(stage)
        except OSError:
            logging.exception('Committed successfully, but staging cleanup failed')
            report['warnings'].append('Importación guardada; no se pudo limpiar una copia temporal de Staging.')
        report['imported'] = len(incoming)
        report['playlists'] = len(m3u_writes)
        report['transaction'] = tx.directory.name
        if report['warnings']:
            report['status'] = 'COMPLETE WITH WARNINGS'
        logging.info('Import result: %s', report)
        return report
