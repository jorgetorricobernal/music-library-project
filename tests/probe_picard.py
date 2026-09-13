"""Real Picard probe on three fresh copies; never writes the source recording."""
import sys
from pathlib import Path
APP = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(APP), str(APP / 'vendor')]
import hashlib
import json
import logging
import shutil
from mutagen.id3 import ID3
from musiclib.storage import Library
from musiclib.picard import Picard

source = Path(sys.argv[1])
lib = Library(APP.parent / 'Integration Test')
logging.basicConfig(filename=lib.app / 'import.log', level=logging.INFO)
results = []
for strategy, kind in [('lookup', 'releases'), ('lookup', 'playlists'), ('scan', 'playlists')]:
    stage = lib.app / ('probe-' + strategy + '-' + kind)
    stage.mkdir(exist_ok=True)
    audio = stage / 'sample.mp3'
    shutil.copy2(source, audio)
    tags = ID3(audio)
    for key in list(tags):
        if 'musicbrainz' in key.casefold() or 'acoustid' in key.casefold():
            del tags[key]
    if strategy == 'scan':
        for key in ('TPE1', 'TPE2', 'TALB', 'TIT2', 'TRCK'):
            tags.delall(key)
    tags.save(audio)
    found = Picard(lib, timeout=180).run_pass([audio], kind, strategy, stage / 'commands')
    results.append({'strategy': strategy, 'kind': kind, 'resolved': [t.dict() for t in found.values()]})
    print(json.dumps(results[-1]), flush=True)
(APP / 'tests/picard-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
