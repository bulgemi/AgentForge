# AGENTS.md - AgentForge AI Developer Harness Instructions

This repository is powered by **AgentForge** and includes an autonomous **AI Developer Harness** in `.agents/skills/`.
All AI coding agents (OpenAI Codex, Google Antigravity, Anthropic Claude Code, Cursor, Windsurf, GitHub Copilot) **MUST automatically follow the instructions below without requiring the user to explicitly specify skill file paths**.

---

## 🎯 Universal Zero-Prompt Intent Routing

Whenever the user gives a natural language task, analyze their intent and **automatically activate the corresponding harness skill**:

| User Intent / Request Pattern | Automatically Adopted Skill | Key Mandatory Rules |
| :--- | :--- | :--- |
| **신규 기능 / 컴포넌트 / API 추가**<br/>(e.g., "대화 내보내기 추가해줘", "Add user export API") | [`.agents/skills/feature-development/SKILL.md`](.agents/skills/feature-development/SKILL.md) | • Clean Architecture 계층 분리<br/>• `[NEW]`, `[MODIFY]`, `[DELETE]` 파일 단위 설계<br/>• 신규 단위/E2E 테스트 케이스 필수 작성 |
| **기존 기능 개선 / 리팩토링 / 최적화**<br/>(e.g., "세션 TTL 갱신 로직 개선해줘", "Optimize query") | [`.agents/skills/feature-enhancement/SKILL.md`](.agents/skills/feature-enhancement/SKILL.md) | • 파급 영향도(Blast Radius) 분석<br/>• 하위 호환성(Breaking Changes) 보장<br/>• 과도한 재작성(Over-refactoring) 방지 |
| **버그 수정 / 결함 해결 / 에러 분석**<br/>(e.g., "스트리밍 500 에러 고쳐줘", "Fix connection reset") | [`.agents/skills/bugfix/SKILL.md`](.agents/skills/bugfix/SKILL.md) | • 근본 원인(RCA) 규명<br/>• **재현 실패 테스트(RED) 필수 선작성**<br/>• 최소 수정 원칙(Minimal Diff) 엄수 |

---

## 🚦 8단계 표준 엔지니어링 파이프라인 (Mandatory Workflow)

모든 작업은 [`.agents/skills/shared/workflow-spec.md`](.agents/skills/shared/workflow-spec.md)에 정의된 8단계를 반드시 순차적으로 준수해야 합니다:

1. **분석 (Analysis)**: 도메인 규칙 및 파급 영향도 분석
2. **파일 단위 상세 설계 (Design)**: `[NEW]`, `[MODIFY]`, `[DELETE]` 목록과 구체적 함수/클래스 시그니처 명시
3. **설계 리뷰 (Over-engineering Check)**: YAGNI, 불필요한 추상화/패턴 남용 배제
4. **★ 사용자 승인 게이트 (Human-in-the-loop Gate)**:
   > **CRITICAL**: 에이전트는 설계를 자의적으로 확정하고 구현을 시작할 수 없습니다. 설계서 및 오버엔지니어링 검토 내용을 보고하고 **사용자의 명시적 승인(`Proceed` 또는 확인 응답)**을 받은 후에만 5단계로 진행하십시오.
5. **GitHub Issue & 태그 등록**: `gh issue create` (또는 `.github/issues/` 로컬 마크다운 폴백)
6. **Issue 기반 정밀 구현**: 승인된 파일 단위 설계서 범위 내에서만 구현
7. **코드 리뷰**: `git diff` 점검, 보안 취약점 및 부작용 체크
8. **기능 점검 & 결과 보고**: 자동화 테스트(`pytest`, frontend build) 통과 증명 + 신규/회귀 테스트 통과 + 이슈 종료
