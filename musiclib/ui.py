"""Small phosphor-green TUI with successive screens and a final summary."""
import atexit
import logging
import shutil
import sys
import time
from .engine import Engine, inventory
from .playlists import discover


# A soft turquoise-green inspired by late phosphor CRT monitors. True-colour
# ANSI escapes work in macOS Terminal and leave the user's Terminal profile
# untouched. Non-interactive output remains plain text for logs and tests.
PHOSPHOR = '\033[38;2;53;255;168m'
DEEP_BLACK = '\033[48;2;0;7;5m'
BRIGHT = '\033[1m'
NORMAL_WEIGHT = '\033[22m'
RESET = '\033[0m'
CLEAR = '\033[2J\033[H'


def terminal_mode():
    return sys.stdout.isatty()


def reset_terminal():
    if terminal_mode():
        print(RESET, end='', flush=True)


atexit.register(reset_terminal)


def screen(title, lines):
    styled = terminal_mode()
    if styled:
        print(CLEAR + DEEP_BLACK + PHOSPHOR, end='')
    width = min(72, max(42, shutil.get_terminal_size((72, 24)).columns - 2))
    emphasis = BRIGHT if styled else ''
    normal = NORMAL_WEIGHT if styled else ''
    print(emphasis + '╔' + '═' * width + '╗')
    print('║' + title.center(width) + '║')
    print('╚' + '═' * width + '╝' + normal + '\n')
    print('\n'.join(lines), flush=True)


def choice():
    try:
        cursor = BRIGHT + '> ' + NORMAL_WEIGHT if terminal_mode() else '> '
        return input('\n' + cursor).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return 'exit'


class UI:
    def __init__(self, lib):
        self.lib = lib
        self.last_progress = 0
        self.started = 0

    def progress(self, message, count):
        if time.monotonic() - self.last_progress < 0.5:
            return
        self.last_progress = time.monotonic()
        elapsed = int(time.monotonic() - self.started)
        screen('IMPORT MUSIC', ['IMPORTING', '', message, f'Archivos / elementos: {count}',
                                f'Tiempo: {elapsed // 60:02d}:{elapsed % 60:02d}', '',
                                'Puedes dejar que termine; no necesita confirmaciones.'])

    def format(self):
        while True:
            screen('IMPORT MUSIC', ['Format policy', '', '[1] FLAC', '[2] MP3', '[3] Keep both', '[B] Back', '',
                                   'Preferencia entre copias equivalentes; no convierte audio.',
                                   'Si solo existe otro formato, se conserva.'])
            selected = choice()
            if selected in ('b', 'exit'):
                return False
            if selected in ('1', '2', '3'):
                config = self.lib.config()
                config['format_policy'] = {'1':'flac', '2':'mp3', '3':'both'}[selected]
                self.lib.save_config(config)
                return True

    def result(self, title, lines):
        screen(title, lines + ['', '[M] Main Menu    [E] Exit'])
        while True:
            selected = choice()
            if selected in ('m', 'b'):
                return True
            if selected in ('e', 'exit', '3'):
                return False

    def import_music(self):
        first = self.lib.config()['format_policy'] is None
        if first and not self.format():
            return True
        while True:
            batches = inventory(self.lib)
            policy = self.lib.config()['format_policy']
            screen('IMPORT MUSIC', [f'Releases:    {sum(b["kind"] == "releases" for b in batches)}',
                                   f'Playlists:   {sum(b["kind"] == "playlists" for b in batches)}',
                                   f'Audio files: {sum(len(b["files"]) for b in batches)}', '',
                                   'Format policy: ' + policy.upper(), '',
                                   '[Enter] Start Import', '[R] Refresh folders',
                                   '[F] Change format', '[B] Back'])
            selected = choice()
            if selected in ('b', 'exit'):
                return True
            if selected == 'r':
                continue
            if selected == 'f':
                self.format()
            elif selected == '':
                break
        self.started = time.monotonic()
        result = Engine(self.lib, self.progress).run()
        lines = [result['status'], '', f'Imported:             {result["imported"]}',
                 f'Duplicates resolved:  {result["duplicates"]}', f'Tracks promoted:      {result["promoted"]}',
                 f'Pending:              {result["pending"]}', f'Playlists updated:    {result["playlists"]}']
        if result['warnings']:
            lines += ['', 'Revisa 2. New Downloads/3. Pending y vuelve a colocar lo corregido en incoming.']
            lines += result['warnings'][:6]
            if len(result['warnings']) > 6:
                lines.append(f'+ {len(result["warnings"]) - 6} avisos en import.log')
        return self.result('IMPORT MUSIC', lines)

    def rebuild(self):
        while True:
            paths = discover(self.lib)
            screen('REBUILD PLAYLISTS', [f'[{i}] {p.name}' for i, p in enumerate(paths, 1)] + ['', '[A] Rebuild All', '[B] Back'])
            selected = choice()
            if selected in ('b', 'exit'):
                return True
            if selected == 'a':
                name = None
                break
            if selected.isdigit() and 1 <= int(selected) <= len(paths):
                name = paths[int(selected) - 1].name
                break
        screen('REBUILD PLAYLISTS', ['REBUILDING…'])
        result = Engine(self.lib).rebuild(name)
        return self.result('REBUILD PLAYLISTS', ['COMPLETE WITH WARNINGS' if result['missing'] else 'REBUILD COMPLETE', '',
                           f'Playlists: {result["playlists"]}', f'Tracks checked: {result["checked"]}',
                           f'Paths repaired: {result["changed"]}', f'Unresolved: {result["missing"]}',
                           'Las entradas no localizadas se conservan.'])

    def run(self):
        while True:
            screen('MUSIC LIBRARY', ['[1] Import Music', '[2] Rebuild Playlists', '[3] Exit', '', str(self.lib.root)])
            selected = choice()
            try:
                if selected in ('3', 'exit'):
                    return
                if selected == '1' and not self.import_music():
                    return
                if selected == '2' and not self.rebuild():
                    return
            except (Exception, KeyboardInterrupt) as error:
                logging.exception('Operation failed')
                self.lib.recover()
                if not self.result('MUSIC LIBRARY', ['FAILED', '', str(error) or 'Operación interrumpida.', '',
                                                    'Los originales se conservan o se recuperan al abrir la app.',
                                                    'Detalle técnico: Music Library App/import.log']):
                    return
