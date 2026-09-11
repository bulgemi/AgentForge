---
name: feature-development
description: End-to-end 개발 하네스 스킬 - 신규 기능 개발 요구사항을 분석하고, 파일 단위 구체적 설계, 오버엔지니어링 검토, 사용자 승인 게이트, GitHub Issue 및 태그 등록, 구현, 코드 리뷰, 기능 점검(테스트 작성/통과), 결과 보고 파이프라인을 엄격히 준수하여 수행합니다.
---

# 신규 기능 개발 하네스 (Feature Development Harness)

AgentForge 프로젝트에서 새로운 비즈니스 기능, API 엔드포인트, UI 화면, 또는 백엔드 서비스를 구축할 때 사용하는 표준 개발 하네스입니다.
본 스킬은 임의 코딩을 금지하며 아래 8단계 파이프라인과 [공통 워크플로우 명세](../shared/workflow-spec.md)를 엄격히 준수합니다.

---

## 실행 절차 및 지침

### 1단계: 신규 요구사항 분석 (Analysis)
1. 사용자 요구사항의 핵심 목적과 수용 조건(Acceptance Criteria)을 파악합니다.
2. 시스템 아키텍처(클린 아키텍처: 도메인, 유스케이스, 어댑터, 외부 인터페이스)와의 경계를 정의합니다.
3. 데이터 모델(DB 엔티티, Pydantic/DTO 스키마) 및 외부 시스템(Redis, OpenSearch, Langfuse 등) 연동 요구사항을 확인합니다.

### 2단계: 파일 단위 상세 설계 (Design)
1. 변경 영향도가 명확히 파악되도록 **반드시 파일 단위 목록**으로 상세 설계를 작성합니다:
   - `[NEW] path/to/file`: 파일의 책임, 생성할 클래스/함수 시그니처 및 타입 어노테이션
   - `[MODIFY] path/to/file`: 수정할 함수명, 구체적인 변경 로직 및 영향받는 의존성
   - `[DELETE] path/to/file`: 삭제 대상 및 대체 방안
2. API 요청/응답 스펙, DB 테이블 스키마 DDL 또는 마이그레이션 전략을 구체적으로 포함합니다.

### 3단계: 설계 리뷰 및 오버엔지니어링 검토 (Over-Engineering Review)
1. 아래 질문에 대해 설계를 비판적으로 검토합니다:
   - **YAGNI**: 현재 요구사항에 포함되지 않은 추상화 레이어나 미래 대비용 파라미터가 포함되어 있는가?
   - **과도한 패턴 남용**: 단순 로직에 불필요한 전략 패턴, 팩토리, 데코레이터 등을 복잡하게 엮지 않았는가?
   - **불필요한 파일 생성**: 하나의 모듈로 충분한 코드를 수많은 잘게 쪼갠 파일로 분산시키지 않았는가?
2. 오버엔지니어링 요소를 정제하고 설계를 가장 단순하고 명료한 형태로 최적화합니다.

### ★ 사용자 승인 게이트 (Human-in-the-loop Gate)
> [!IMPORTANT]
> 설계를 자의적으로 확정하고 구현에 진입해서는 안 됩니다.
> 정제된 상세 설계서와 오버엔지니어링 검토 요약을 사용자에게 명확히 보고하고, **사용자의 명시적 승인(`Proceed` 또는 확인)**을 획득하십시오.

### 4단계: GitHub Issue 및 태그 등록 (Issue Registration)
1. GitHub CLI(`gh`)를 통해 공식 Issue를 생성합니다:
   ```bash
   gh issue create --title "[Feature] <기능명>" \
     --label "type:feature,stage:implementation,status:in-progress" \
     --body "<승인된 설계서 본문>"
   ```
2. 만약 `gh`가 미설치 또는 미인증 상태라면:
   - `.github/issues/ISSUE-<YYYYMMDD>-<feature-slug>.md` 경로에 생성하고 사용자에게 알립니다.

### 5단계: Issue 기반 구현 (Implementation)
1. 승인된 설계서에 명시된 파일 단위 계획에 따라 순차적으로 코드를 작성합니다.
2. 기존 코딩 컨벤션(타입 힌트, docstring, 비동기 패턴, 에러 핸들링)을 완벽히 유지합니다.
3. 설계 범위를 벗어난 과도한 리팩토링이나 임의의 부가 기능 구현은 금지됩니다.

### 6단계: 코드 리뷰 (Code Review)
1. `git diff`를 확인하여 의도하지 않은 변경이나 디버깅용 잔재 코드가 없는지 점검합니다.
2. 보안 취약점(입력값 검증, 인증/인가 누락, 민감정보 노출)을 체크합니다.
3. 점검 내용을 GitHub Issue 댓글(또는 로컬 이슈 파일)에 기록합니다.

### 7단계: 기능 점검 및 테스트 작성 (QA & Verification)
1. **신규 테스트 케이스 작성**:
   - 신규 기능의 정상 흐름(Happy Path) 및 예외 흐름(Edge Case)에 대한 단위/통합 테스트를 `backend/tests/` 및 프론트엔드에 추가합니다.
2. **자동화 테스트 실행**:
   - Backend: `uv run pytest tests/`
   - Frontend: `npm run build` 및 `npm test`
3. **수동 점검 체크리스트 제공**:
   - cURL 명령어나 브라우저 URL을 포함한 실제 동작 검증 체크리스트를 도출하여 점검합니다.

### 8단계: 결과 보고 및 Issue 완료 (Close)
1. GitHub Issue의 상태 태그를 전환하고 이슈를 종료합니다:
   ```bash
   gh issue edit <ISSUE_NUM> --remove-label "stage:implementation" --add-label "stage:done,status:completed"
   gh issue close <ISSUE_NUM> --comment "신규 기능 구현, 코드 리뷰 및 기능 검증 테스트 통과로 완료되었습니다."
   ```
2. 사용자에게 최종 변경 사항, 생성/수정된 파일 목록, 테스트 결과 요약을 보고합니다.
