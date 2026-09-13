---
name: feature-enhancement
description: End-to-end 개발 하네스 스킬 - 기존 기능의 개선/고도화/리팩토링 요구사항을 분석하고, 영향도 분석, 하위 호환성 검토, 파일 단위 상세 설계, 과도한 재작성(Over-refactoring) 방지 리뷰, 사용자 승인 게이트, GitHub Issue/태그 등록, 구현, 코드 리뷰, 회귀 검증, 결과 보고를 엄격히 수행합니다.
---

# 기능 개선 및 고도화 하네스 (Feature Enhancement Harness)

AgentForge 프로젝트에서 이미 동작 중인 기능, 모듈, 성능, 아키텍처 구조를 개선하거나 리팩토링할 때 사용하는 표준 개발 하네스입니다.
본 스킬은 기존 시스템의 안정성과 하위 호환성을 최우선으로 보호하며 [공통 워크플로우 명세](../shared/workflow-spec.md)를 준수합니다.

---

## 실행 절차 및 지침

### 1단계: 기존 기능 및 영향도 분석 (Impact Analysis)
1. 개선 대상 기존 코드의 현재 구현 상태, 호출 흐름, 데이터 계약을 면밀히 분석합니다.
2. **파급 영향도(Blast Radius) 측정**:
   - 수정 대상 모듈을 의존하는 상위 모듈 및 클라이언트 식별
   - DB 스키마 변경 시 기존 저장 데이터의 마이그레이션 필요성
   - API 응답 형식 변경에 따른 프론트엔드/외부 연동 하위 호환성(Breaking Changes) 여부 확인

### 2단계: 파일 단위 상세 설계 (Design)
1. 변경 영향도가 명확히 파악되도록 **반드시 파일 단위 목록**으로 상세 설계를 작성합니다:
   - `[MODIFY] path/to/file`: 수정 대상 함수/클래스, 변경 전 로직 vs 변경 후 로직, 하위 호환성 유지 방안
   - `[NEW] path/to/file`: 신규 보조 모듈 또는 마이그레이션 스크립트
   - `[DELETE] path/to/file`: 더 이상 사용되지 않는 레거시 코드 및 삭제 안전성 근거
2. 변경 전후의 인터페이스 및 데이터 흐름 차이점을 명확히 기재합니다.

### 3단계: 설계 리뷰 및 과도한 재작성(Over-refactoring) 검토
1. 아래 질문을 통해 설계의 경제성과 안전성을 점검합니다:
   - **Over-refactoring 방지**: 개선 목적에 꼭 필요하지 않은 인접 모듈까지 광범위하게 재작성하려 하지는 않는가?
   - **하위 호환성 보장**: 기존 호출자(Caller)들의 시그니처나 동작을 불필요하게 깨뜨리지 않는가?
   - **점진적 전환**: 필요 시 Deprecation 경고를 두고 단계적으로 이관 가능한 설계인가?
2. 불필요한 범위 확장을 배제하고, 개선 목표 달성에 필요한 최소 변경(Minimal Diff)으로 설계를 조정합니다.

### ★ 사용자 승인 게이트 (Human-in-the-loop Gate)
> [!IMPORTANT]
> 영향도 분석 결과와 과도한 재작성 방지 검토 결과를 사용자에게 명확히 제시하고, **사용자의 명시적 승인(`Proceed` 또는 확인)**을 획득한 후에만 다음 단계로 진행합니다.

### 4단계: GitHub Issue 및 태그 등록 (Issue Registration)
1. GitHub CLI(`gh`)를 통해 공식 Issue를 생성합니다:
   ```bash
   gh issue create --title "[Enhancement] <개선 내용>" \
     --label "type:enhancement,stage:implementation,status:in-progress" \
     --body "<승인된 개선 설계서 본문>"
   ```
2. `gh` 미설치/미인증 시 `.github/issues/ISSUE-<YYYYMMDD>-<enhancement-slug>.md`로 로컬 폴백합니다.

### 5단계: Issue 기반 안전 구현 (Implementation)
1. 승인된 설계 범위 내에서만 정밀하게 코드를 수정합니다.
2. 기존 유닛 테스트들이 깨지지 않도록 하위 호환성을 유지하며 기능을 고도화합니다.

### 6단계: 코드 리뷰 (Code Review)
1. `git diff`를 실행하여 의도하지 않은 사이드 이펙트나 포맷팅 변경으로 인한 불필요한 노이즈가 없는지 검토합니다.
2. 기존 비즈니스 로직의 불변 규칙(Invariants)이 여전히 충족되는지 확인합니다.
3. 리뷰 결과를 GitHub Issue 댓글로 남깁니다.

### 7단계: 기능 점검 및 회귀 테스트 (QA & Regression Testing)
1. **기존 테스트 스위트 회귀 검증**:
   - 기존의 모든 테스트가 100% 통과하는지 확인 (`uv run pytest tests/`)
2. **개선 기능 신규 테스트 케이스 추가**:
   - 새롭게 고도화된 기능, 엣지 케이스, 경계 조건을 다루는 테스트 케이스를 작성하여 통과시킵니다.
3. **통합 동작 점검**:
   - 프론트엔드 빌드 및 백엔드 API와의 연동 정상성을 검증합니다.

### 8단계: 결과 보고 및 Issue 완료 (Close)
1. GitHub Issue의 상태 태그를 전환하고 이슈를 종료합니다:
   ```bash
   gh issue edit <ISSUE_NUM> --remove-label "stage:implementation" --add-label "stage:done,status:completed"
   gh issue close <ISSUE_NUM> --comment "기능 개선 및 회귀 테스트 검증이 완료되어 이슈를 종료합니다."
   ```
2. 사용자에게 전후 개선 지표(성능, 가독성, 신규 기능 등)와 변경 파일 목록을 최종 보고합니다.
