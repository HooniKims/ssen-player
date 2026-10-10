# 배포와 업데이트

소스 저장소와 GitHub 릴리즈는 `HooniKims/ssen-player`에서 공개합니다. 0.2.3부터 앱은 GitHub 릴리즈에서 새 버전을 확인합니다.

## Windows 빌드

빌드 전 `python scripts/fetch_codecs.py`로 `build/codecs.json`에 고정한 LGPL 재생 DLL을 내려받습니다. SHA-256 검증 후 `vendor/ffmpeg`에만 저장하며 시스템에는 설치하지 않습니다. PyInstaller는 Qt 기본 DLL 대신 이 파일들을 포함합니다. 완성된 `_internal/PySide6`의 5개 DLL 해시가 vendor 원본과 일치하는지 확인하고 AV1을 포함한 설치본 검사를 실행합니다.

1. `app/__init__.py`와 `build/installer.iss`의 버전을 함께 변경합니다.
2. `requirements-dev.txt` 설치 후 단위/재생/필기 테스트를 실행합니다.
3. `PyInstaller` onedir 패키징 후 Inno Setup으로 설치 파일을 만듭니다. 실행 시 임시 폴더에 풀지 않으므로 반복 시작 비용을 줄입니다.
4. 실제 패키징 앱의 `--smoke-test-output` 검사와 설치/업데이트 검사를 수행합니다.
5. 앱 코드와 설치 파일은 배포용 Authenticode 인증서가 준비되면 서명합니다. 업데이트 매니페스트의 Ed25519 서명과 Windows 코드 서명은 서로 다릅니다.

## GitHub 릴리즈 업데이트

앱은 실행 3초 뒤 `build/update.json`의 `feed_url`, 곧 `https://github.com/HooniKims/ssen-player/releases/latest/download/update.json`을 확인합니다. 새 버전이 있으면 "지금 업데이트 / 다음에"를 묻고, "다음에"를 고르면 다음 실행 때 다시 묻습니다. 수업 전체 화면이나 녹화 중에는 창을 띄우지 않고 상태 줄에만 알립니다. 인터넷이 없거나 확인에 실패하면 아무것도 표시하지 않습니다.

`update.json`은 Ed25519로 서명합니다. 앱에는 공개키만 들어 있고, 개인키는 저장소 밖 `%USERPROFILE%\.ssen-player\update-signing-key.pem`에 둡니다. **개인키를 잃으면 이미 설치된 앱에 업데이트를 보낼 수 없으므로 따로 백업합니다.** 앱에는 GitHub 토큰을 넣지 않습니다.

1. 설치 파일을 빌드한 뒤 매니페스트에 서명합니다. `--url`은 해당 릴리즈 태그의 설치 파일 주소입니다.

```powershell
.venv/Scripts/python.exe scripts/sign_release.py `
  --key "$env:USERPROFILE/.ssen-player/update-signing-key.pem" `
  --installer artifacts/SsenPlayer-Setup-0.2.3.exe `
  --url 'https://github.com/HooniKims/ssen-player/releases/download/v0.2.3/SsenPlayer-Setup-0.2.3.exe' `
  --version 0.2.3 --output artifacts/update.json
```

2. GitHub 릴리즈 `v0.2.3`에 설치 파일, 포터블 ZIP, `artifacts/update.json`을 함께 올립니다. 파일 이름은 반드시 `update.json`이어야 합니다.
3. 초안이나 시험판이 아닌 정식 릴리즈로 게시합니다. `latest` 주소는 정식 릴리즈만 가리킵니다.
4. 앱은 서명, 버전, URL, 파일 크기, SHA-256을 모두 확인한 뒤 설치합니다. 재생 위치·음량·캡처 폴더는 `HKCU/Software/HooniKim/SsenPlayer`에 저장되므로 설치 폴더가 바뀌어도 유지됩니다.

0.2.2 이하에는 업데이트 주소가 없어서 0.2.3은 한 번 직접 내려받아 설치해야 합니다.

## 배포 전 확인

- 새로운 PC에서 별도 Python/코덱 설치 없이 실행되는지 확인.
- 수업 모드에서 실제 전자칠판 펜/손가락 입력, DPI 배율, 모니터 전환 확인.
- 재생 중 / 정지 중 캡처와 폴더 권한 오류 확인.
- 실제 iPhone MOV, HDR 원본, 고해상도/고프레임률 샘플 확인.
- 업데이트 변조 거부와 이전 버전 → 새 버전 설치, 설정 유지 확인.
- LGPL 구성요소의 라이선스 원문과 정확한 대응 소스 제공 경로를 배포물과 함께 유지.
