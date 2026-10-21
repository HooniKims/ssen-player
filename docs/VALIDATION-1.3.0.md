# 1.3.0 검증 · 2026-10-21

## 구현과 환경

- 대상은 이 저장소의 쎈Player, Python 3.12 / PySide6 6.10.2 / PyInstaller / Inno Setup 7.1이다. 공식 배포 저장소는 `HooniKims/ssen-player`다.
- 사용자 설정은 `HKCU/Software/HooniKim/SsenPlayer`에 저장한다. 업데이트의 `updates/auto_check`, `updates/skipped_version`, `updates/last_checked`는 이용권과 독립적으로 저장하고 실패를 표시한다.
- 메인 시작 경로, 기존 HTTPS·크기·SHA-256 검증, 설치형 등록 정보, 설정·약관 UI를 연결했다. 포터블/개발 실행은 공식 ZIP 배포 페이지로 안내한다.
- 실행 중인 쎈img의 실제 우측 하단 카드와 상세 안내창을 Computer Use로 확인하고 `artifacts/qa/update-reference`에 각각 캡처했다. 다른 앱의 이름·버전·배포 주소는 사용하지 않았다.

## 자동 테스트

- Python 회귀 테스트 **64개 통과**: 기존 41개에 업데이트 상태/Qt UI 23개를 추가했다. 업데이트 UI 23개는 실제 앱 스타일을 적용한 상태로도 통과했다.
- 공통 인증 키트 **17개 통과**, 브라우저 암호 벡터 **61개 통과**. 합계 **142개**이며 별도 재실행을 중복 합산하지 않았다.
- 최신/새 버전, 같은 세션의 나중에·X 재노출 방지, 설치 준비 시 1회 추가 알림, 건너뛴 버전 재생성 후 유지 및 다음 버전 알림, 건너뛴 버전의 수동 다운로드를 검사했다.
- 15초/4시간 설정값, 중복 시작 방지, 예약 해제·재생성·설정 유지, 자동 확인을 끈 수동 확인을 검사했다. 타이머 콜백은 간격을 단축해 실제 이벤트 루프로 실행했다. 4시간을 실제로 기다린 시험은 아니다.
- `scripts/startup_update_smoke.py`에서 실제 `main.main()` 정상 경로를 실행했다. 단일 실행은 임시 폴더, 인증·설정은 격리 fixture를 사용했다. 시작 타이머 활성화와 자동 다운로드가 없는 상태를 확인했다.
- 네트워크 오류 시 기존 새 버전 유지, 다운로드 오류와 재시도, 설정 저장 실패의 롤백/오류 표시, 다운로드·확인 중복 방지, 작업 스레드 결과의 UI 스레드 전달을 검사했다.
- 다운로드 완료만으로 설치·종료가 호출되지 않음, 명시적 확인, 바쁜 작업 차단, 설치 직전 변조 파일 거부, 포터블·개발 실행의 설치 차단과 공식 URL 제한을 검사했다.
- HTML/긴 릴리스 노트는 일반 텍스트로 6,000자까지 표시한다. 버전 버튼의 키보드 접근, 재생 Space 단축키와 충돌 방지, 상세창 Escape 닫기를 검사했다.

## 실제 화면과 미디어

`scripts/update_smoke.py`는 실제 Player/Qt UI를 사용하지만 **9.9.9 모의 릴리스와 가짜 다운로드 파일**로 상태를 만든다. 테스트용 버전·설명·용량은 제품 코드에 포함하지 않았다. 실제 설치는 호출하지 않았다.

스크린샷은 `artifacts/qa/updates`에 남겼다.

- `card-normal.png`, `version-dot.png`, `details-normal.png`
- `card-minimum.png`, `details-minimum.png`, `details-minimum-bottom.png`
- `card-downloading.png`, `details-downloading.png`, `card-ready.png`
- `card-portable.png`, `details-error.png`, `details-untrusted-notes.png`, `latest-no-notice.png`

1280×800 및 최소 1024×700에서 카드가 창 안에 있고 상세창의 긴 내용·약관은 세로 스크롤로 접근할 수 있음을 확인했다. 상세창의 가로 스크롤은 없고 닫기 버튼은 항상 보인다. 수업/완전 화면에서 돌아와도 닫은 카드를 다시 띄우지 않는다.

`scripts/subtitle_smoke.py`는 실제 MOV를 재생하며 한글 자막을 QDragEnterEvent/QDropEvent로 적용했다. 일시 정지 위치 유지, 재생 중 계속 재생, 자막이 재생 목록에 들어가지 않음, 일반/최소/수업/완전 화면의 자막 표시를 확인했다. `artifacts/qa/subtitles`에 화면과 보고서를 남겼다.

기존 `scripts/smoke_test.py`의 실제 MOV, 재생 중 필기, 재생·일시 정지 캡처, 합성 터치, 전체 화면 회귀 검사도 통과했다.

## 배포 EXE와 설치 조건

- 완성된 EXE에서 MOV와 AV1을 각각 `--auth-test-output`으로 실행했다. 실제 디코딩/재생, 인증 전 보호, 가짜 서버의 잘못된 서명 거부를 포함한 모든 검사가 통과했다. 실제 계정은 사용하지 않았다.
- PyInstaller 내부의 앱 버전·Player·업데이트 엔진/UI·자막·단일 실행·진단 코드가 현재 소스와 일치하는지 코드 객체를 비교했다. 시험용 권한 모듈은 포함되지 않았다.
- 번들 재생 DLL 5개의 SHA-256이 고정 vendor 원본과 일치했다. 약관·EXE 저작권·비공개 문서 제외와 사용자 출력 69개의 표식 미포함을 확인했다.
- `scripts/test_installer_restart.py`는 제품의 `[Run]` 조건과 `[Code]`를 복사한 소형 Inno 설치 fixture에서 실행했다. 실제 Player 대신 무해한 `whoami.exe`를 사용했다. 일반 무인 설치에서는 실행 0회, `/RESTARTPLAYER=1`에서는 1회였다. 사용자 앱 설치·바로가기·제거 등록을 변경하지 않았다.

## 검증 범위

모의 업데이트 UI 검사를 실제 공개 설치 파일 다운로드 성공 또는 사용자 앱 설치 성공으로 표현하지 않는다. 기존 사용자 설치를 덮어쓰거나 실제 앱 재시작 설치를 수행하지 않았다. 실제 이메일 인증·학교망·타 앱 계정 공유, 전자칠판 실기기, HDR 색 정확도는 이번 수정에서 별도로 검증하지 않았다.
