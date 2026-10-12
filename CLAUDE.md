# 쎈player 개발 주의 사항

- 빌드·검증·배포 절차는 README.md와 RELEASING.md를 따른다. 앱은 PySide6/Qt, 설치본은 Inno Setup이다.
- 1.0.0부터 자체 이용약관 LICENSE가 적용된다. 제3조는 쎈 시리즈 공통 문안이며, 오픈소스 구성 요소의 라이선스 권리는 그대로 유지한다.
- 저작권: © 2026 상명초 김승현, 등촌중 김형훈. 설치 ID·게시자·설치 경로·EXE 이름·업데이트 검증 방식은 약관 작업 때문에 바꾸지 않는다.
- 표식 6곳의 값 목록은 비공개 docs/provenance.md에만 기록한다. 해당 기록과 작업 지시서 MD는 공개 Git 및 배포물에서 제외한다.
- 난독화하지 않는다. 이용자 파일, 캡처 PNG, 녹화 MP4, 구간 MP4, 자막, 파일별 설정·필기·메타데이터에 표식을 넣지 않는다.
- LICENSE 수정 후 scripts/prepare_legal.py로 설치 약관과 EXE 버전 정보를 만든다. SsenPlayer.spec도 빌드 시 이를 실행한다.
