"""Tag reading and conservative identity. Mutagen is bundled, no pip at launch."""
from dataclasses import dataclass, asdict
import re
import unicodedata
import uuid
from pathlib import Path
import mutagen
from mutagen.id3 import ID3
from mutagen.mp4 import MP4
from .storage import digest

AUDIO = {'.flac', '.mp3', '.m4a', '.mp4', '.wav', '.aiff', '.aif', '.ogg', '.opus', '.alac'}


def clean(value, limit=100):
    s = unicodedata.normalize('NFKC', str(value or ''))
    s = s.replace('/', '-').replace('\\', '-').replace(':', ' -')
    s = re.sub(r'[\x00-\x1f\x7f<>"|?*]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip(' .')
    while len(s.encode('utf-8')) > limit:
        s = s[:-1]
    return s or 'Unknown'


def mbid(s):
    try:
        return str(uuid.UUID(str(s)))
    except (ValueError, TypeError, AttributeError):
        return ''


def number(s, default=0):
    match = re.match(r'\s*(\d+)', str(s))
    return int(match.group(1)) if match else default


@dataclass
class Tags:
    artist: str = ''
    albumartist: str = ''
    album: str = ''
    title: str = ''
    year: str = ''
    track: int = 0
    disc: int = 1
    discs: int = 1
    total: int = 0
    recording: str = ''
    release: str = ''
    group: str = ''
    release_track: str = ''
    seconds: float = 0
    bitrate: int = 0

    @property
    def identified(self):
        return bool(self.recording and self.release and self.title and self.artist and self.album)

    @property
    def release_key(self):
        return self.group or self.release

    def identity(self, path):
        return 'mb:' + self.recording if self.recording else 'sha:' + digest(path)

    def filename(self, extension):
        position = f'{self.disc:02d}-{self.track:02d}' if self.discs > 1 or self.disc > 1 else f'{self.track:02d}'
        return clean(f'{self.artist} - {self.album} - {position}. {self.title}', 220) + extension.lower()

    def folder(self):
        return clean(f'{self.albumartist or self.artist} [{self.year}] {self.album}', 210)

    def dict(self):
        return asdict(self)


def read(path):
    audio = mutagen.File(path)
    if audio is None:
        raise ValueError('Formato de audio no reconocido: ' + str(path))
    tags = audio.tags or {}
    def first(value):
        if hasattr(value, 'text'):
            value = value.text
        if isinstance(value, (list, tuple)):
            value = value[0] if value else ''
        if isinstance(value, bytes):
            value = value.decode('utf-8', 'replace')
        return str(value or '')
    if isinstance(tags, ID3):
        keys = {'artist':'TPE1', 'albumartist':'TPE2', 'album':'TALB', 'title':'TIT2',
                'tracknumber':'TRCK', 'discnumber':'TPOS', 'date':'TDRC', 'originaldate':'TDOR',
                'originalyear':'TXXX:originalyear', 'musicbrainz_albumid':'TXXX:MusicBrainz Album Id',
                'musicbrainz_releasegroupid':'TXXX:MusicBrainz Release Group Id',
                'musicbrainz_releasetrackid':'TXXX:MusicBrainz Release Track Id'}
        def get(key):
            if key == 'musicbrainz_trackid':
                frame = tags.get('UFID:http://musicbrainz.org')
                return first(frame.data) if frame else first(tags.get('TXXX:MusicBrainz Track Id'))
            return first(tags.get(keys.get(key, 'TXXX:' + key)))
    elif isinstance(audio, MP4):
        keys = {'artist':'\xa9ART', 'albumartist':'aART', 'album':'\xa9alb', 'title':'\xa9nam', 'date':'\xa9day'}
        def get(key):
            if key in ('tracknumber', 'discnumber'):
                pair = tags.get('trkn' if key == 'tracknumber' else 'disk', [(0, 0)])[0]
                return f'{pair[0]}/{pair[1]}'
            names = {'musicbrainz_trackid':'MusicBrainz Track Id', 'musicbrainz_albumid':'MusicBrainz Album Id',
                     'musicbrainz_releasegroupid':'MusicBrainz Release Group Id',
                     'musicbrainz_releasetrackid':'MusicBrainz Release Track Id'}
            return first(tags.get(keys.get(key, '----:com.apple.iTunes:' + names.get(key, key))))
    else:
        lower = {k.lower(): v for k, v in tags.items()}
        def get(key):
            return first(lower.get(key))
    track, disc = get('tracknumber'), get('discnumber')
    year = ''
    for key in ('originaldate', 'originalyear', 'date'):
        match = re.match(r'(\d{4})', get(key))
        if match:
            year = match.group(1)
            break
    return Tags(artist=get('artist'), albumartist=get('albumartist'), album=get('album'), title=get('title'),
                year=year, track=number(track), disc=number(disc, 1) or 1,
                discs=number(get('disctotal') or (disc.split('/')[1] if '/' in disc else ''), 1) or 1,
                total=number(get('tracktotal') or (track.split('/')[1] if '/' in track else '')),
                recording=mbid(get('musicbrainz_trackid')), release=mbid(get('musicbrainz_albumid')),
                group=mbid(get('musicbrainz_releasegroupid')), release_track=mbid(get('musicbrainz_releasetrackid')),
                seconds=float(getattr(audio.info, 'length', 0)), bitrate=int(getattr(audio.info, 'bitrate', 0)))


def files(folder):
    result = []
    for p in Path(folder).rglob('*'):
        if p.is_symlink():
            raise ValueError('Retira el enlace simbólico antes de importar: ' + str(p))
        if p.is_file() and p.suffix.lower() in AUDIO and not p.name.startswith('._'):
            result.append(p)
    return sorted(result, key=lambda p: [int(x) if x.isdigit() else x.casefold() for x in re.split(r'(\d+)', str(p))])


def rank(entry, policy):
    ext = Path(entry['path']).suffix.lower()
    preference = {'.flac': 50, '.wav': 40, '.aiff': 40, '.aif': 40, '.alac': 35, '.m4a': 30, '.mp3': 20}
    if policy in ('flac', 'mp3'):
        preference['.' + policy] = 100
    return (preference.get(ext, 10), entry['tags'].get('bitrate', 0), entry.get('existing', False))


def write_release(path, canonical):
    """Retag a staging copy when promoting a better loose format into a release."""
    from mutagen.id3 import TPE1, TPE2, TALB, TIT2, TRCK, TPOS, TDRC, TDOR, TXXX, UFID
    audio = mutagen.File(path)
    if audio.tags is None:
        audio.add_tags()
    values = {'artist': canonical.artist, 'albumartist': canonical.albumartist, 'album': canonical.album,
              'title': canonical.title, 'tracknumber': str(canonical.track) + ('/' + str(canonical.total) if canonical.total else ''),
              'discnumber': f'{canonical.disc}/{canonical.discs}', 'originaldate': canonical.year,
              'musicbrainz_trackid': canonical.recording, 'musicbrainz_albumid': canonical.release,
              'musicbrainz_releasegroupid': canonical.group, 'musicbrainz_releasetrackid': canonical.release_track}
    if isinstance(audio.tags, ID3):
        frames = {'artist': TPE1, 'albumartist': TPE2, 'album': TALB, 'title': TIT2,
                  'tracknumber': TRCK, 'discnumber': TPOS, 'originaldate': TDOR}
        descriptions = {'musicbrainz_albumid': 'MusicBrainz Album Id', 'musicbrainz_releasegroupid': 'MusicBrainz Release Group Id',
                        'musicbrainz_releasetrackid': 'MusicBrainz Release Track Id'}
        for key, value in values.items():
            if key in frames:
                audio.tags.add(frames[key](encoding=3, text=[value]))
            elif key == 'musicbrainz_trackid':
                audio.tags.add(UFID(owner='http://musicbrainz.org', data=value.encode('ascii')))
            else:
                audio.tags.add(TXXX(encoding=3, desc=descriptions[key], text=[value]))
    elif isinstance(audio, MP4):
        fields = {'artist': '\xa9ART', 'albumartist': 'aART', 'album': '\xa9alb', 'title': '\xa9nam'}
        descriptions = {'musicbrainz_trackid': 'MusicBrainz Track Id', 'musicbrainz_albumid': 'MusicBrainz Album Id',
                        'musicbrainz_releasegroupid': 'MusicBrainz Release Group Id', 'musicbrainz_releasetrackid': 'MusicBrainz Release Track Id'}
        for key, value in values.items():
            if key in fields:
                audio[fields[key]] = [value]
            elif key == 'tracknumber':
                audio['trkn'] = [(canonical.track, canonical.total)]
            elif key == 'discnumber':
                audio['disk'] = [(canonical.disc, canonical.discs)]
            else:
                audio['----:com.apple.iTunes:' + descriptions.get(key, key)] = [value.encode('utf-8')]
    else:
        for key, value in values.items():
            audio[key] = [value]
    audio.save()
