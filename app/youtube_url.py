"""URL parsing kept independent of the lazily-loaded browser engine."""
import re
from urllib.parse import urlparse, parse_qs


def video_id(value):
    value = value.strip()
    if re.fullmatch(r'[A-Za-z0-9_-]{11}', value): return value
    parsed = urlparse(value)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError('YouTube 영상 링크를 입력해 주세요.')
    host = (parsed.hostname or '').lower()
    if host == 'youtu.be': candidate = parsed.path.strip('/').split('/')[0]
    elif host in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'www.youtube-nocookie.com'):
        candidate = parse_qs(parsed.query).get('v', [''])[0]
        if not candidate and parsed.path.startswith(('/embed/', '/shorts/', '/live/')):
            candidate = parsed.path.split('/')[2]
    else: candidate = ''
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', candidate):
        raise ValueError('올바른 YouTube 영상 링크가 아닙니다.')
    return candidate
