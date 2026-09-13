"""Portable paths and durable, reversible filesystem transactions."""
import contextlib
import fcntl
import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
import tempfile
import uuid

DIRS = {
    'releases': '1. Music Library/1. Releases',
    'tracks': '1. Music Library/2. Tracks',
    'releases_incoming': '2. New Downloads/1. Releases incoming',
    'playlists': '2. New Downloads/2. Playlists incoming',
    'pending': '2. New Downloads/3. Pending',
    'm3u': '3. Playlists M3U',
    'others': '4. Others',
    'app': 'Music Library App',
}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        try:
            os.fsync(fd)
        except OSError as e:
            # Some removable filesystems do not support fsync on directories.
            if e.errno not in (22, 45, 95):
                raise
    finally:
        os.close(fd)


def atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.musiclib-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data.encode('utf-8') if isinstance(data, str) else data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
        sync_dir(path.parent)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def json_bytes(data):
    return (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def copy_durable(src, dst):
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Path(src).open('rb') as a, dst.open('wb') as b:
        shutil.copyfileobj(a, b, 1024 * 1024)
        b.flush()
        os.fsync(b.fileno())
    sync_dir(dst.parent)


class Library:
    def __init__(self, root):
        self.root = Path(root).resolve()
        legacy_incoming = self.root / '2. New Downloads/1. Albums incoming'
        releases_incoming = self.root / DIRS['releases_incoming']
        if legacy_incoming.exists() and not releases_incoming.exists():
            legacy_incoming.rename(releases_incoming)
        elif legacy_incoming.exists() and releases_incoming.exists():
            raise RuntimeError(
                'Existen a la vez Albums incoming y Releases incoming. '
                'No se mezclan automáticamente para evitar sobrescribir descargas.'
            )
        self.paths = {key: self.root / value for key, value in DIRS.items()}
        for path in self.paths.values():
            self.safe(path)
            path.mkdir(parents=True, exist_ok=True)
        self.app = self.paths['app']
        self.recovery = self.app / 'Recovery'
        self.safe(self.recovery)
        self.recovery.mkdir(exist_ok=True)
        self.config_path = self.app / 'config.json'
        self.catalog_path = self.app / 'catalog.json'

    def safe(self, path):
        path = Path(path)
        if not path.is_absolute():
            path = self.root / path
        try:
            parts = path.relative_to(self.root).parts
        except ValueError:
            raise ValueError('Ruta fuera de la biblioteca: ' + str(path))
        if '..' in parts:
            raise ValueError('No se permiten rutas con .. dentro del catálogo.')
        current = self.root
        for part in parts:
            current /= part
            if current.is_symlink():
                raise ValueError('No se admiten enlaces simbólicos: ' + str(current))
        if not path.resolve().is_relative_to(self.root):
            raise ValueError('Ruta fuera de la biblioteca: ' + str(path))
        return path

    def rel(self, path):
        return self.safe(path).relative_to(self.root).as_posix()

    @contextlib.contextmanager
    def lock(self):
        with (self.app / '.lock').open('a') as f:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('La biblioteca ya está abierta en otra ventana. Ciérrala primero.')
            try:
                yield
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def config(self):
        self.safe(self.config_path)
        if not self.config_path.exists():
            atomic(self.config_path, json_bytes({'version': 1, 'format_policy': None, 'picard_timeout': 600}))
        config = json.loads(self.config_path.read_text())
        if config.get('version') != 1 or config.get('format_policy') not in (None, 'flac', 'mp3', 'both'):
            raise ValueError('config.json no es válido. Restaura su copia antes de continuar.')
        return config

    def save_config(self, config):
        atomic(self.config_path, json_bytes(config))

    def catalog(self):
        self.safe(self.catalog_path)
        if not self.catalog_path.exists():
            return {'version': 1, 'files': [], 'aliases': {}}
        data = json.loads(self.catalog_path.read_text())
        if data.get('version') != 1:
            raise ValueError('Versión del catálogo no compatible.')
        for entry in data['files']:
            self.safe(entry['path'])
        return data

    def recover(self):
        recovered = []
        for manifest in sorted(self.recovery.glob('*/transaction.json')):
            tx = Transaction.open(self, manifest.parent)
            if tx.data['state'] in ('applying', 'rolling_back'):
                tx.rollback()
                recovered.append(tx.directory.name)
        return recovered


class Transaction:
    """Preimages + write-ahead manifest, never overwrite on ambiguous recovery.

    All payloads and preimages are fsynced before 'applying'. Each operation is
    idempotent by old/new hash. Rollback checks every path before changing any.
    Committed preimages remain available for explicit recovery of originals.
    """
    def __init__(self, library):
        self.lib = library
        self.directory = library.recovery / uuid.uuid4().hex
        self.directory.mkdir()
        self.data = {'version': 1, 'state': 'preparing', 'operations': []}
        self.manifest = self.directory / 'transaction.json'
        self._write()

    @classmethod
    def open(cls, library, directory):
        obj = cls.__new__(cls)
        obj.lib, obj.directory = library, directory
        obj.manifest = directory / 'transaction.json'
        obj.data = json.loads(obj.manifest.read_text())
        return obj

    def _write(self):
        atomic(self.manifest, json_bytes(self.data))

    def add(self, path, source=None, data=None, expected=None):
        path = self.lib.safe(path)
        relative = self.lib.rel(path)
        if any(o['path'] == relative for o in self.data['operations']):
            raise ValueError('Operación duplicada: ' + relative)
        index = str(len(self.data['operations']))
        old = digest(path) if path.exists() else None
        if expected is not None and old != expected:
            raise RuntimeError('El archivo cambió durante la importación: ' + relative)
        backup = self.directory / 'before' / index
        if old is not None:
            copy_durable(path, backup)
            if digest(backup) != old:
                raise IOError('No se pudo verificar la copia de seguridad: ' + relative)
        new = None
        if source is not None or data is not None:
            payload = self.directory / 'after' / index
            if source is not None:
                copy_durable(source, payload)
            else:
                atomic(payload, data)
            new = digest(payload)
        self.data['operations'].append({'path': relative, 'old': old, 'new': new, 'index': index})
        self._write()

    def _check(self, rollback=False):
        for op in self.data['operations']:
            path = self.lib.safe(op['path'])
            actual = digest(path) if path.exists() else None
            allowed = (op['old'], op['new']) if rollback else (op['old'],)
            if actual not in allowed:
                raise RuntimeError('Archivo modificado externamente; recuperación detenida: ' + op['path'])
            key = 'old' if rollback else 'new'
            if op[key] is not None:
                folder = 'before' if rollback else 'after'
                payload = self.directory / folder / op['index']
                if not payload.exists() or digest(payload) != op[key]:
                    raise IOError('Copia de recuperación dañada: ' + op['path'])

    def _install(self, op, rollback=False):
        path = self.lib.safe(op['path'])
        key = 'old' if rollback else 'new'
        if op[key] is None:
            if path.exists():
                path.unlink()
                sync_dir(path.parent)
        else:
            folder = 'before' if rollback else 'after'
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.parent / ('.musiclib-' + self.directory.name)
            self.lib.safe(temp)
            copy_durable(self.directory / folder / op['index'], temp)
            os.replace(temp, path)
            sync_dir(path.parent)

    def commit(self, fault=None):
        self._check()
        self.data['state'] = 'applying'
        self._write()
        try:
            for index, op in enumerate(self.data['operations']):
                self._install(op)
                if fault:
                    fault(index)
            self.data['state'] = 'committed'
            self._write()
        except Exception:
            self.rollback()
            raise
        # Payloads are dispensable only after the durable commit marker.
        shutil.rmtree(self.directory / 'after', ignore_errors=True)
        logging.info('Transaction committed %s', self.directory.name)

    def rollback(self):
        self._check(rollback=True)
        self.data['state'] = 'rolling_back'
        self._write()
        for op in reversed(self.data['operations']):
            self._install(op, rollback=True)
        self.data['state'] = 'rolled_back'
        self._write()
        logging.warning('Transaction rolled back %s', self.directory.name)
