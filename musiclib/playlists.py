"""M3U paths with stable identity hints, preserving order and unresolved entries."""
import json
import logging
import os
from pathlib import Path
from .metadata import rank

PREFIX = '#MUSICLIB-ID:'


def hint(entry):
    return {'id': entry['id'], 'path': entry['path']}


def relative(path, m3u):
    return os.path.relpath(path, m3u.parent).replace(os.sep, '/')


def render(entries, m3u, library):
    lines = ['#EXTM3U']
    for entry in entries:
        lines.append(PREFIX + json.dumps(hint(entry), ensure_ascii=False))
        tags = entry.get('tags', {})
        title = (str(tags.get('artist', '')) + ' - ' + str(tags.get('title', ''))).replace('\n', ' ').replace('\r', ' ')
        lines.append(f'#EXTINF:{int(tags.get("seconds", -1))},{title}')
        lines.append(relative(library.safe(entry['path']), m3u))
    return '\n'.join(lines) + '\n'


def repair(text, m3u, library, catalog, policy):
    by_path = {e['path']: e for e in catalog['files']}
    by_id, by_name = {}, {}
    for entry in catalog['files']:
        by_id.setdefault(entry['id'], []).append(entry)
        by_name.setdefault(Path(entry['path']).name.casefold(), []).append(entry)
    aliases = catalog.get('aliases', {})
    result, reference = [], None
    changed = missing = checked = 0
    for line in text.lstrip('\ufeff').splitlines():
        if line.startswith(PREFIX):
            try:
                reference = json.loads(line[len(PREFIX):])
            except (ValueError, TypeError):
                reference = None
            result.append(line)
            continue
        if not line or line.startswith('#'):
            result.append(line)
            continue
        checked += 1
        entry = None
        path = (m3u.parent / line).resolve()
        if path.is_relative_to(library.root):
            rel = path.relative_to(library.root).as_posix()
            entry = by_path.get(rel)
            old_id = aliases.get(rel)
            if entry is None and old_id:
                candidates = by_id.get(old_id, [])
                if candidates:
                    entry = max(candidates, key=lambda x: (x['kind'] == 'releases', rank(x, policy)))
        if entry is None and isinstance(reference, dict):
            reference_id = reference.get('id')
            candidates = by_id.get(reference_id, []) or by_id.get(aliases.get(reference_id), [])
            if candidates:
                entry = max(candidates, key=lambda x: (x['kind'] == 'releases', rank(x, policy)))
        if entry is None and path.is_relative_to(library.paths['pending']) and path.is_file():
            library.safe(path)
            entry = {'path': library.rel(path)}
        if entry is None:
            candidates = by_name.get(Path(line).name.casefold(), [])
            # Never guess between different recordings with the same filename.
            if candidates and len({c['id'] for c in candidates}) == 1:
                entry = max(candidates, key=lambda x: rank(x, policy))
        if entry:
            new = relative(library.safe(entry['path']), m3u)
            changed += new != line
            if reference is None:
                result.append(PREFIX + json.dumps(hint(entry), ensure_ascii=False))
            result.append(new)
        else:
            result.append(line)
            missing += 1
            logging.warning('Unresolved M3U entry %s: %s', m3u, line)
        reference = None
    if not result or result[0] != '#EXTM3U':
        result.insert(0, '#EXTM3U')
    return '\n'.join(result) + '\n', {'checked': checked, 'changed': changed, 'missing': missing}


def discover(library):
    return sorted(p for p in library.paths['m3u'].iterdir() if not p.name.startswith('.') and p.suffix.lower() in ('.m3u', '.m3u8') and p.is_file())
