---
name: bugfix
description: End-to-end 개발 하네스 스킬 - 결함 및 장애 요구사항을 분석하고, 근본 원인(RCA) 분석, 재현 실패 테스트(Reproducing Test) 필수 선작성, 최소 수정(Minimal Diff) 상세 설계, 과도한 변경 방지 리뷰, 사용자 승인 게이트, GitHub Issue/태그 등록, 수정 구현, 코드 리뷰, 회귀 검증, 결과 보고를 엄격히 수행합니다.
---

# 버그 수정 하네스 (Bugfix Harness)

AgentForge 프로젝트에서 런타임 에러, 비즈니스 로직 오류, 회귀 결함 등을 추적하고 안전하게 수정할 때 사용하는 표준 개발 하네스입니다.
본 스킬은 결함 재현 테스트를 통한 과학적 검증과 최소 변경 원칙(Minimal Diff)을 최우선으로 삼으며 [공통 워크플로우 명세](../shared/workflow-spec.md)를 준수합니다.

---

## 실행 절차 및 지침

### 1단계: 결함 분석 및 근본 원인 분석 (RCA: Root Cause Analysis)
1. 발생 증상, 에러 로그, 스택 트레이스, 재현 시나리오를 정밀 분석합니다.
2. 표면적인 증상 치료가 아닌 결함이 발생하는 근본 메커니즘(RCA)을 규명합니다.
3. 동일한 패턴으로 발생할 수 있는 잠재적 결함 포인트가 있는지 조사합니다.

### 2단계: 파일 단위 상세 설계 및 재현 테스트 계획 (Design)
1. **재현 실패 테스트(Reproducing Test) 작성 계획**:
   - 결함을 정확히 트리거하여 실패(RED)를 증명할 테스트 파일과 테스트 케이스를 설계합니다.
2. **최소 수정(Minimal Diff) 파일 목록**:
   - `[NEW] tests/.../test_bug_reproduce.py`: 버그 재현 테스트 파일
   - `[MODIFY] path/to/file`: 버그를 유발하는 구체적 라인과 수정할 안전한 로직
   - 버그 수정과 무관한 코드 정리나 리팩토링은 절대 포함하지 않습니다.

### 3단계: 설계 리뷰 및 과도한 수정 방지 검토 (Over-engineering Check)
1. 아래 질문으로 설계의 안전성을 검증합니다:
   - **과도한 수정(Over-fixing) 여부**: 버그 수정 범위를 넘어 주변 모듈까지 임의로 재설계하고 있지 않은가?
   - **새로운 버그 유발 위험**: 수정 로직이 다른 정상 시나리오에 부작용(Side-effect)을 유발할 가능성은 없는가?
   - **최소 변경 여부**: 가장 간결하고 명확한 방식으로 버그를 해소하는가?
2. 안전한 최소 수정안으로 설계를 확정합니다.

### ★ 사용자 승인 게이트 (Human-in-the-loop Gate)
> [!IMPORTANT]
> 근본 원인 분석, 재현 테스트 방안, 최소 수정 계획을 사용자에게 보고하고, **사용자의 명시적 승인(`Proceed` 또는 확인)**을 획득한 후 진행합니다.

### 4단계: GitHub Issue 및 태그 등록 (Issue Registration)
1. GitHub CLI(`gh`)를 통해 공식 Issue를 생성합니다:
   ```bash
   gh issue create --title "[Bugfix] <결함 증상 요약>" \
     --label "type:bugfix,stage:implementation,status:in-progress" \
     --body "<승인된 원인 분석 및 수정 계획>"
   ```
2. `gh` 미설치/미인증 시 `.github/issues/ISSUE-<YYYYMMDD>-<bugfix-slug>.md`로 로컬 폴백합니다.

### 5단계: Issue 기반 테스트 선작성 및 코드 수정 (Implementation)
1. **1차: 재현 테스트 코드 작성 및 실행**:
   - 설계된 테스트 케이스를 작성하고 실행하여 실패(Fail / Red)를 먼저 확인합니다.
2. **2차: 버그 수정 코드 반영**:
   - 문제를 일으킨 최소 라인을 정밀 수정합니다.
3. **3차: 재현 테스트 통과 확인**:
   - 실패했던 테스트가 성공(Pass / Green)으로 바뀌는지 확인합니다.

### 6단계: 코드 리뷰 (Code Review)
1. `git diff`를 통해 오직 버그 수정과 테스트 코드만 변경되었는지 엄격히 확인합니다.
2. 엣지 케이스(None/Null 포인터, 빈 문자열, 비동기 레이스 컨디션 등)에 대한 방어 로직이 적절한지 리뷰합니다.
3. 리뷰 요약을 GitHub Issue 댓글로 남깁니다.

### 7단계: 기능 점검 및 전체 회귀 테스트 (QA & Regression Testing)
1. **전체 테스트 스위트 실행**:
   - `uv run pytest tests/`를 실행하여 기존의 모든 정상 기능이 깨지지 않았음을 증명합니다.
2. **프론트엔드/서비스 빌드 확인**:
   - 필요 시 프론트엔드 빌드 및 관련 서비스 정상 가동 상태를 검증합니다.

### 8단계: 결과 보고 및 Issue 완료 (Close)
1. GitHub Issue의 상태 태그를 전환하고 이슈를 종료합니다:
   ```bash
   gh issue edit <ISSUE_NUM> --remove-label "stage:implementation" --add-label "stage:done,status:completed"
   gh issue close <ISSUE_NUM> --comment "근본 원인 해소, 재현 테스트 작성 및 전체 회귀 테스트 통과로 버그 수정 완료."
   ```
2. 사용자에게 원인, 해결 방법, 추가된 테스트 케이스, 변경 내역을 최종 보고합니다.
