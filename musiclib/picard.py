"""Isolated Picard 2.13.3 exec integration; two fresh passes, checked saves."""
import logging
import os
from pathlib import Path
import plistlib
import shlex
import shutil
import subprocess
import time
from . import metadata
from .storage import atomic


def locate(app):
    candidates = [app / 'Tools/MusicBrainz Picard.app',
                  Path('/Applications/MusicBrainz Picard.app'),
                  Path.home() / 'Applications/MusicBrainz Picard.app']
    for bundle in candidates:
        info = bundle / 'Contents/Info.plist'
        if info.exists():
            data = plistlib.loads(info.read_bytes())
            if data.get('CFBundleShortVersionString') != '2.13.3':
                continue
            return bundle / 'Contents/MacOS' / data['CFBundleExecutable']
    raise RuntimeError('No encuentro Picard 2.13.3. Instálalo en Aplicaciones o en Music Library App/Tools.')


def commands(paths, kind, strategy):
    lines = ['LOAD ' + shlex.quote(str(p)) for p in paths] + ['PAUSE 1']
    if strategy == 'lookup':
        lines += ['CLUSTER', 'PAUSE 1', 'LOOKUP clustered', 'PAUSE 1', 'LOOKUP unclustered'] if kind == 'releases' else ['LOOKUP unclustered']
    else:
        lines += ['SCAN']
    # Picard 2.13.3 can finish SCAN before its async callback schedules the
    # release request. PAUSE is itself tracked by Picard's command queue;
    # the first save also drains pending web requests, the second saves
    # tracks attached during that drain. REMOVE_ALL releases the file objects
    # before the parent stops the worker. Only confirmed disk writes count.
    return lines + ['PAUSE 1', 'SAVE_MATCHED', 'PAUSE 1', 'SAVE_MATCHED',
                    'PAUSE 1', 'REMOVE_ALL']


def config_text(strategy):
    """Return an isolated, non-interactive Picard profile for staging copies."""
    return ('[General]\n\n[setting]\n'
            'rename_files=false\nmove_files=false\nmove_additional_files=false\n'
            'delete_empty_dirs=false\ndont_write_tags=false\npreserve_timestamps=false\n'
            'clear_existing_tags=false\nsave_images_to_files=false\nsave_images_to_tags=false\n'
            'enable_tagger_scripts=false\ncheck_for_updates=false\n'
            'show_new_user_dialog=false\nfile_save_warning=false\nquit_confirmation=false\n'
            'ignore_file_mbids=' + ('true' if strategy == 'scan' else 'false') + '\n'
            'file_lookup_threshold=0.85\ncluster_lookup_threshold=0.80\n'
            'track_matching_threshold=0.80\n')


def stop_worker(process):
    """Stop an idle isolated worker without Picard's unstable Qt teardown."""
    # SIGTERM is handled by Picard as a normal quit and still reaches the
    # crashing PyQt/SIP finalizer. SIGKILL skips that third-party teardown.
    # At this point SAVE_MATCHED, its settling pause and REMOVE_ALL have all
    # completed, so Picard has no open music file or pending operation.
    process.kill()
    process.wait()


class Picard:
    def __init__(self, library, timeout=600, progress=lambda *a: None):
        self.library, self.timeout, self.progress = library, timeout, progress
        self.executable = locate(library.app)
        self.warnings = []

    def run_pass(self, paths, kind, strategy, work):
        work.mkdir(parents=True, exist_ok=True)
        config = work / 'picard.ini'
        # Never share user profiles/plugins or alter files outside this staging area.
        atomic(config, config_text(strategy))
        command_file = work / 'commands.txt'
        atomic(command_file, '\n'.join(commands(paths, kind, strategy)) + '\n')
        # Timestamp sentinel on COPIES: an existing MBID alone is not proof of this run's success.
        sentinel = 946684800
        for path in paths:
            os.utime(path, (sentinel, sentinel))
        command = [str(self.executable), '-s', '-P', '-N', '-M', '-d', '--no-crash-dialog',
                   '-c', str(config), '-e', 'FROM_FILE', str(command_file)]
        logging.info('Picard %s %s: %s', kind, strategy, command)
        log_path = self.library.app / 'import.log'
        with log_path.open('a', encoding='utf-8') as log:
            log.flush()
            log_start = log_path.stat().st_size
            process = subprocess.Popen(command, stdout=log, stderr=log, start_new_session=True)
            deadline = time.monotonic() + self.timeout
            commands_finished = False
            try:
                while True:
                    with log_path.open('rb') as capture:
                        capture.seek(log_start)
                        diagnostics = capture.read().decode('utf-8', 'replace')
                    if 'Completed command: REMOVE_ALL' in diagnostics:
                        commands_finished = True
                        break
                    if process.poll() is not None:
                        break
                    if time.monotonic() > deadline:
                        raise TimeoutError('Picard ha agotado el tiempo. Comprueba Internet; las entradas originales siguen intactas.')
                    self.progress('Picard · ' + strategy.upper(), len(paths))
                    time.sleep(0.5)
                if commands_finished and process.poll() is None:
                    # SAVE_MATCHED and REMOVE_ALL have completed. Stop without
                    # entering the intermittent PyQt/SIP finalizer crash in the
                    # x86_64 macOS build under Rosetta.
                    stop_worker(process)
                logging.info('Picard exit code: %s', process.returncode)
            finally:
                if process.poll() is None:
                    stop_worker(process)
        with log_path.open('rb') as capture:
            capture.seek(log_start)
            diagnostics = capture.read().decode('utf-8', 'replace')
        if 'Completed command: SAVE_MATCHED' not in diagnostics:
            raise RuntimeError('Picard no confirmó el guardado. Los originales se conservan; consulta import.log.')
        result = {}
        for path in paths:
            try:
                tags = metadata.read(path)
                if path.stat().st_mtime > sentinel + 1 and tags.identified:
                    result[path] = tags
            except Exception:
                logging.exception('Tags unreadable after Picard: %s', path)
        if not commands_finished:
            raise RuntimeError('Picard no pudo terminar. Los originales siguen intactos; consulta import.log.')
        if len(result) < len(paths) and ('Network request error' in diagnostics or 'Network error' in diagnostics):
            raise RuntimeError('MusicBrainz o AcoustID no respondió correctamente. Comprueba Internet y repite Import Music; los originales siguen intactos.')
        return result

    def identify(self, paths, kind, work):
        # Picard SAVE_MATCHED deliberately skips tracks with multiple linked files.
        # Separate formats and repeated recording IDs into lanes so each can be saved.
        lanes = []
        occupied = []
        for path in paths:
            try:
                tags = metadata.read(path)
                key = tags.release_track or tags.recording or (tags.artist, tags.album, tags.track, tags.title)
            except Exception:
                key = str(path)
            slot = (path.suffix.lower(), str(key))
            lane = next((i for i, used in enumerate(occupied) if slot not in used and all(x[0] == slot[0] for x in used)), None)
            if lane is None:
                lane = len(lanes)
                lanes.append([])
                occupied.append(set())
            occupied[lane].add(slot)
            lanes[lane].append(path)
        resolved = {}
        for i, lane in enumerate(lanes):
            found = self.run_pass(lane, kind, 'lookup', work / f'lookup-{i}')
            resolved.update(found)
            remaining = [p for p in lane if p not in found]
            if remaining:
                # Fresh loading places previously clustered/unmatched files back into unclustered.
                # One file per scan also avoids two editions attaching to the same recording.
                for j, path in enumerate(remaining):
                    resolved.update(self.run_pass([path], kind, 'scan', work / f'scan-{i}-{j}'))
        return resolved
