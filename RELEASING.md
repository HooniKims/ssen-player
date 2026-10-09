# 배포와 업데이트

소스 저장소는 `HooniKims/ssen-player` 비공개입니다. 설치 파일 공개 범위는 소스 공개 범위와 별개로 결정합니다. 현재 앱에는 배포 주소가 없으므로 업데이트 UI가 그 상태를 명시합니다.

## Windows 빌드

1. `app/__init__.py`와 `build/installer.iss`의 버전을 함께 변경합니다.
2. `requirements-dev.txt` 설치 후 단위/재생/필기 테스트를 실행합니다.
3. `PyInstaller` onedir 패키징 후 Inno Setup으로 설치 파일을 만듭니다. 실행 시 임시 폴더에 풀지 않으므로 반복 시작 비용을 줄입니다.
4. 실제 패키징 앱의 `--smoke-test-output` 검사와 설치/업데이트 검사를 수행합니다.
5. 앱 코드와 설치 파일은 배포용 Authenticode 인증서가 준비되면 서명합니다. 업데이트 매니페스트의 Ed25519 서명과 Windows 코드 서명은 서로 다릅니다.

## HTTPS 업데이트 피드

앱에는 GitHub 개인 액세스 토큰을 넣지 않습니다. 일반 사용자 자동 업데이트에는 접근 가능한 HTTPS 피드 및 설치 파일 주소가 필요합니다. 비공개 설치 파일까지 요구된다면 별도의 사용자 인증 배포 서비스가 필요합니다.

1. 외부 보관 위치에서 Ed25519 키 쌍을 생성합니다. 개인키는 저장소 및 앱 번들에 넣지 않습니다.
2. `build/update.json`에 `feed_url`과 원시 32바이트 공개키의 Base64 값 `public_key`를 설정한 뒤 빌드합니다.
3. 설치 파일을 배포 서버에 올린 뒤 다음 스크립트로 매니페스트를 서명합니다.

```powershell
.venv/Scripts/python.exe scripts/sign_release.py `
  --key '<저장소 밖 개인키.pem>' `
  --installer artifacts/SsenPlayer-Setup-0.1.0.exe `
  --url 'https://배포호스트/SsenPlayer-Setup-0.1.0.exe' `
  --version 0.1.0 --output artifacts/update.json
```

4. 생성된 매니페스트를 `feed_url` 주소에 배포합니다. 버전, URL, 파일 크기, SHA-256 모두 서명에 포함됩니다.
5. 앱은 새 버전만 안내하고, 사용자가 다운로드와 설치를 각각 선택합니다. 재생 위치·음량·캡처 폴더는 `HKCU/Software/HooniKim/SsenPlayer`에 보관되어 설치 디렉터리 교체와 분리됩니다.

## 배포 전 확인

- 새로운 PC에서 별도 Python/코덱 설치 없이 실행되는지 확인.
- 수업 모드에서 실제 전자칠판 펜/손가락 입력, DPI 배율, 모니터 전환 확인.
- 재생 중 / 정지 중 캡처와 폴더 권한 오류 확인.
- 실제 iPhone MOV, HDR 원본, 고해상도/고프레임률 샘플 확인.
- 업데이트 변조 거부와 이전 버전 → 새 버전 설치, 설정 유지 확인.
- LGPL 구성요소의 라이선스 원문과 정확한 대응 소스 제공 경로를 배포물과 함께 유지.
