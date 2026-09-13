#!/usr/bin/env python3
"""Run from any working directory. Library root = parent of this application."""
import argparse
import json
import logging
from pathlib import Path
import sys

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP / 'vendor'))
sys.dont_write_bytecode = True
from musiclib.storage import Library
from musiclib.engine import Engine
from musiclib.ui import UI


def main():
    parser = argparse.ArgumentParser(description='Portable Music Library')
    parser.add_argument('--root', type=Path, help='Explicit isolated library root (testing / setup)')
    parser.add_argument('--init', action='store_true')
    parser.add_argument('--import', dest='do_import', action='store_true')
    parser.add_argument('--format', choices=['flac', 'mp3', 'both'])
    parser.add_argument('--rebuild', nargs='?', const='*', metavar='PLAYLIST')
    args = parser.parse_args()
    lib = Library(args.root or APP.parent)
    logging.basicConfig(filename=lib.app / 'import.log', level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8', force=True)
    try:
        with lib.lock():
            recovered = lib.recover()
            config = lib.config()
            if args.format:
                config['format_policy'] = args.format
                lib.save_config(config)
            if recovered:
                logging.warning('Recovered interrupted transactions: %s', recovered)
                print('Importación interrumpida recuperada; los originales están restaurados.')
            if args.init:
                print('Biblioteca preparada:', lib.root)
            elif args.do_import:
                print(json.dumps(Engine(lib).run(), ensure_ascii=False, indent=2))
            elif args.rebuild is not None:
                print(json.dumps(Engine(lib).rebuild(None if args.rebuild == '*' else args.rebuild), indent=2))
            else:
                UI(lib).run()
        return 0
    except (Exception, KeyboardInterrupt) as error:
        logging.exception('Application failed')
        print('FAILED\n' + (str(error) or 'Operación interrumpida.') + '\nDetalle: ' + str(lib.app / 'import.log'))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
