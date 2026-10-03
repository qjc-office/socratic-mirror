# socratic-mirror

Claude Code 사용자의 과거 대화 기록에서 반복되는 근거 없는 전제를 찾아, 답 없이 질문만으로 무너뜨리는 공개 플러그인.

## 프로젝트 정보
- 고객: 없음 (QJC 공개 오픈소스, MIT)
- GitHub: qjc-office/socratic-mirror (public)
- PRD: v1 → `docs/prds/PRD-socratic-mirror.md`
- 설계 문서(spec SSOT): `docs/superpowers/specs/2026-10-02-socratic-mirror-design.md`
- 사내 원장 식별자는 공개 저장소에 두지 않는다 (사내 os_projects에서 조회)

## 기술 스택
- Claude Code 플러그인 (commands / skills / agents), 저장소 하나가 마켓플레이스 겸용
- 기록 추출: Python 3 표준 라이브러리만 (외부 의존성 금지)
- 테스트: pytest(단위) + `claude plugin eval`(행동, 반드시 이 플러그인을 대상으로 지정)

## 개발 규칙
- 커밋 포맷: `<type>: <description>`
- 테스트: RED → GREEN → IMPROVE
- 파일 한계: 800줄 / 함수 50줄 / 중첩 4단계
- 공개 저장소다. 실제 대화 기록, 고객명, 내부 경로, 시크릿을 픽스처·예시·README에 넣지 않는다
- 사용자 대면 문구는 한국어·영어 둘 다 유지 (README.md / README.en.md)
- 원본 프롬프트 출처는 "SNS에서 공유된 프롬프트를 각색"으로만 표기한다

## 문서 동기화
- 동작이 바뀌면 같은 PR에서 설계 문서와 README를 함께 고친다
- 머지 전 `/sync-docs`
