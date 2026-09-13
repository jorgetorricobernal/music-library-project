#!/usr/bin/env python3
"""Export transaction preimages without rolling back later imports."""
from pathlib import Path
import json
import sys
import uuid
APP = Path(__file__).resolve().parent
sys.path[:0] = [str(APP), str(APP / 'vendor')]
from musiclib.storage import Library, Transaction, digest, copy_durable
from musiclib.ui import screen, choice


def export(lib, directory):
    tx = Transaction.open(lib, directory)
    destination = lib.paths['others'] / ('Recovered originals ' + directory.name[:8] + '-' + uuid.uuid4().hex[:6])
    # Validate every backup before exporting anything.
    originals = [op for op in tx.data['operations'] if op['old'] is not None]
    for op in originals:
        lib.safe(op['path'])
        if digest(directory / 'before' / op['index']) != op['old']:
            raise IOError('Copia dañada: ' + op['path'])
    for op in originals:
        target = destination / op['path']
        lib.safe(target)
        copy_durable(directory / 'before' / op['index'], target)
    return destination


def main():
    lib = Library(APP.parent)
    with lib.lock():
        lib.recover()
        choices = []
        for p in sorted(lib.recovery.glob('*/transaction.json'), key=lambda p: p.stat().st_mtime, reverse=True):
            tx = json.loads(p.read_text())
            count = sum(op['old'] is not None for op in tx['operations'])
            if count:
                choices.append((p.parent, tx['state'], count))
        screen('RECOVER ORIGINALS', [f'[{i}] {p.name[:12]} · {status} · {count} archivos' for i, (p, status, count) in enumerate(choices, 1)] + ['', '[B] Back / Exit', 'Exporta copias a 4. Others, conservando las rutas originales.'])
        selected = choice()
        if selected.isdigit() and 1 <= int(selected) <= len(choices):
            result = export(lib, choices[int(selected)-1][0])
            print('Originales recuperados en:', result)
            input('Pulsa Enter para cerrar…')


if __name__ == '__main__':
    main()
