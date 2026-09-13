"""Explicit opt-in live integration, reading only copies of user-selected music."""
import sys
from pathlib import Path
APP = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(APP), str(APP / 'vendor')]
import json
import logging
import shutil
import uuid
from musiclib.storage import Library, digest
from musiclib.engine import Engine
from musiclib.metadata import files

source = Path(sys.argv[1])
originals = files(source)
before = {str(p): digest(p) for p in originals}
root = APP.parent / ('Live Test ' + uuid.uuid4().hex[:8])
lib = Library(root)
logging.basicConfig(filename=lib.app / 'import.log', level=logging.INFO)
config = lib.config(); config['format_policy'] = 'both'; lib.save_config(config)
playlist = lib.paths['playlists'] / 'Amotik Test'
playlist.mkdir()
shutil.copy2(originals[0], playlist / originals[0].name)
reports = [Engine(lib).run()]
album = lib.paths['releases_incoming'] / source.name
shutil.copytree(source, album)
reports.append(Engine(lib).run())
reports.append(Engine(lib).rebuild())
assert not files(lib.paths['tracks']), 'Promotion did not finish'
assert len(files(lib.paths['releases'])) == len(originals), 'Release count differs'
for m3u in lib.paths['m3u'].glob('*.m3u'):
    for line in m3u.read_text().splitlines():
        if line and not line.startswith('#'):
            assert (m3u.parent / line).is_file(), line
assert before == {str(p): digest(p) for p in originals}, 'Source changed'
result = {'root': str(root), 'reports': reports, 'originals_unchanged': True}
(APP / 'tests/live-results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps(result, ensure_ascii=False, indent=2))
