$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force artifacts/test-media | Out-Null
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'testsrc2=size=960x540:rate=30' -f lavfi -i 'sine=frequency=440:sample_rate=48000' -t 12 -c:v libx264 -preset ultrafast -pix_fmt yuv420p -c:a aac artifacts/test-media/classroom.mov
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'testsrc2=size=640x360:rate=24' -t 3 -c:v libx265 -preset ultrafast -tag:v hvc1 -pix_fmt yuv420p10le artifacts/test-media/hevc.mov
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'testsrc2=size=640x360:rate=24' -t 3 -c:v prores_ks -profile:v 2 -pix_fmt yuv422p10le artifacts/test-media/prores.mov
ffmpeg -hide_banner -loglevel error -y -display_rotation 90 -i artifacts/test-media/classroom.mov -t 3 -c copy artifacts/test-media/rotated.mov
ffmpeg -hide_banner -loglevel error -y -i artifacts/test-media/classroom.mov -t 3 -c copy artifacts/test-media/h264.mkv
ffmpeg -hide_banner -loglevel error -y -i artifacts/test-media/classroom.mov -t 3 -c copy artifacts/test-media/h264.mp4
if ($LASTEXITCODE -ne 0) { throw 'Test media generation failed' }
