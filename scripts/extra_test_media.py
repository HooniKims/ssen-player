"""Generate short, reproducible codec fixtures using the developer FFmpeg CLI."""
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent.parent
folder = root/'artifacts/test-media'
folder.mkdir(parents=True, exist_ok=True)
cases = [
    ('vp9.webm', 'libvpx-vp9', 'libopus', ['-deadline','realtime','-cpu-used','8']),
    ('av1.mp4', 'libaom-av1', 'aac', ['-cpu-used','8','-crf','45']),
    ('mpeg4.avi', 'mpeg4', 'libmp3lame', ['-q:v','5']),
    ('mjpeg.mov', 'mjpeg', 'pcm_s16le', ['-q:v','5']),
    ('h264-ac3.mkv', 'libx264', 'ac3', ['-preset','ultrafast']),
    ('h264-flac.mkv', 'libx264', 'flac', ['-preset','ultrafast']),
    ('4k-hevc.mp4', 'libx265', 'aac', ['-preset','ultrafast','-x265-params','log-level=error','-pix_fmt','yuv420p10le']),
    ('60fps.mp4', 'libx264', 'aac', ['-preset','ultrafast']),
]
for name, video, audio, extra in cases:
    size = '3840x2160' if name.startswith('4k') else '640x360'
    rate = 60 if name.startswith('60') else 24
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',
        '-f','lavfi','-i',f'testsrc2=size={size}:rate={rate}',
        '-f','lavfi','-i','sine=frequency=660:sample_rate=48000',
        '-t','3','-c:v',video,*extra,'-c:a',audio,str(folder/name)], check=True)
    print(name, flush=True)
