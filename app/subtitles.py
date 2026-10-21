import html
import re
from pathlib import Path

SUBTITLE_EXTENSIONS = ('.srt', '.smi', '.sami', '.vtt')


def find_subtitle(video):
    """Find a same-name sidecar, including uppercase Windows extensions."""
    video = Path(video)
    try:
        files = {p.name.casefold(): p for p in video.parent.iterdir() if p.is_file()}
    except OSError:
        return None
    return next((files[(video.stem + suffix).casefold()] for suffix in SUBTITLE_EXTENSIONS
                 if (video.stem + suffix).casefold() in files), None)


def read_subtitles(path):
    data = Path(path).read_bytes()
    text = None
    encodings = ('utf-16',) if data.startswith((b'\xff\xfe', b'\xfe\xff')) else ('utf-8-sig', 'cp949')
    for encoding in encodings:
        try:
            text = data.decode(encoding)
            break
        except UnicodeError:
            pass
    if text is None:
        raise ValueError('자막 인코딩을 읽을 수 없습니다.')
    def clean(value):
        value = re.sub(r'<br\s*/?>', '\n', value, flags=re.I)
        return html.unescape(re.sub(r'<[^>]+>', '', value)).strip()
    if Path(path).suffix.lower() in ('.smi', '.sami'):
        entries = list(re.finditer(r'<sync\s+start\s*=\s*["\']?(\d+)[^>]*>', text, re.I))
        if not entries:
            raise ValueError('자막 구간을 찾지 못했습니다. SMI 파일 내용을 확인해 주세요.')
        return [(int(m[1]), int(entries[i+1][1]) if i+1 < len(entries) else int(m[1])+5000,
                 clean(text[m.end():entries[i+1].start() if i+1 < len(entries) else len(text)]))
                for i, m in enumerate(entries)]
    def ms(s):
        parts = s.replace(',', '.').split(':')
        return round(sum(float(p) * 60**i for i, p in enumerate(reversed(parts))) * 1000)
    result = []
    for block in re.split(r'\n\s*\n', text.replace('\r', '')):
        match = re.search(r'(\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3})\s*-->\s*(\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3})[^\n]*\n(.*)', block, re.S)
        if match:
            result.append((ms(match[1]), ms(match[2]), clean(match[3])))
    if not result:
        raise ValueError('지원하는 자막 구간을 찾지 못했습니다. SRT, VTT, SMI를 선택해 주세요.')
    return sorted(result)
