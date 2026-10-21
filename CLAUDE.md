# 쎈player 개발 주의 사항

- 빌드·검증·배포 절차는 README.md와 RELEASING.md를 따른다. 앱은 PySide6/Qt, 설치본은 Inno Setup이다.
- 1.0.0부터 자체 이용약관 LICENSE가 적용된다. 제3조는 쎈 시리즈 공통 문안이며, 오픈소스 구성 요소의 라이선스 권리는 그대로 유지한다.
- 저작권: © 2026 상명초 김승현, 등촌중 김형훈. 설치 ID·게시자·설치 경로·EXE 이름·업데이트 검증 방식은 약관 작업 때문에 바꾸지 않는다.
- 표식 6곳의 값 목록은 비공개 docs/provenance.md에만 기록한다. 해당 기록과 작업 지시서 MD는 공개 Git 및 배포물에서 제외한다.
- 난독화하지 않는다. 이용자 파일, 캡처 PNG, 녹화 MP4, 구간 MP4, 자막, 파일별 설정·필기·메타데이터에 표식을 넣지 않는다.
- LICENSE 수정 후 scripts/prepare_legal.py로 설치 약관과 EXE 버전 정보를 만든다. SsenPlayer.spec도 빌드 시 이를 실행한다.

## 공통 인증 1.1.0
- 공통 인증 키트 1.0, app id `player` / 서버 요청 `ssen-player`. `assets/auth/kit-sha256.json`에 기록한 서비스·throttle·저장소·기본 UI 원본은 수정하지 않는다.
- Qt 앱이므로 제공받은 ssencut AuthBridge 안내 5-B 방식으로 연결했다. 기존 Qt WebEngine의 비공개 엔진 페이지에서 원본 JS를 실행한다. Electron을 추가하지 않는다.
- TCP 루프백 대신 QWebChannel을 쓴다. 이용권 UI와 엔진은 별도 페이지/채널이며, UI에는 저장소·네트워크 API가 없다. 외부 페이지 이동과 새 창은 차단한다.
- `%LOCALAPPDATA%/SsenSeries/Auth/v4.bin`, DPAPI CurrentUser, entropy `SsenSeries.Auth.v4`, mutex `Local\SsenSeriesAuthV4`, revision CAS를 그대로 유지한다. 실제 계정으로 QA를 실행하지 않는다.
- 네트워크는 Windows 시스템 프록시·루트 인증서를 사용하는 Qt Network. TLS 검증을 끄지 않는다. 고정 서버/경로/헤더만 허용하며, 리디렉션 금지·20초 제한·1MiB 제한을 적용한다.
- UI 버튼뿐 아니라 Canvas.stroke_begin, SaveCapture.run, ClipJob.run, Recorder.start, ProtectedSettings.setValue, register_player 실행부에서 차단한다. 내보내기 작업은 인증 후 발급한 30초·1회 한정 작업별 허가를 소비한다. 허가 없는 직접 호출은 실패한다.
- 재생·탐색·자막 보기·일시적 속도/음량·구간 반복은 인증 없이 허용. 필기/지우기/편집·캡처·녹화 시작·구간 내보내기·구간 목록 저장/삭제·설정 저장·기본 앱 등록은 인증 후 허용한다. 시작된 녹화는 인증이 끊겨도 종료·저장해 자료 손실을 막는다.
- 1.3.0 사용자 요청에 따라 업데이트 자동 확인·버전 건너뛰기·마지막 확인 시각만 별도 `updates/` 설정으로 인증 없이 저장한다. 저장 실패는 표시하고 성공으로 처리하지 않는다. 기존 미디어·편집 설정의 보호는 유지한다.
- 원본 throttle의 미리 읽기, 표시용 캐시, 10분 자동 확인/유휴 지연, 60초 권한 캐시를 유지한다. 이메일·토큰은 캐시·로그·진단에 추가하지 않는다. 반복 입력마다 PowerShell을 실행하지 않는다.
- `scripts/qa_auth.py`는 소스 회귀시험 전용 가짜 권한이며 배포물에 포함하지 않는다. `--auth-test-output`은 격리 저장소/서명 없는 가짜 서버만 쓰므로 편집 권한을 부여할 수 없다.
- 게시 전 실제 서버의 `player` scope 지원, 다른 쎈 앱 계정 공유, 학교망/메일 인증을 확인한다. 2026-10-12 사용자가 서버 player 등록 여부 미확인 안내를 받은 뒤에도 정식 게시를 재차 명시적으로 지시했다. 이 지시에 따라 1.1.0을 게시한다. 서버 등록·실제 계정 연동이 검증됐다고 기록하지 않는다.
