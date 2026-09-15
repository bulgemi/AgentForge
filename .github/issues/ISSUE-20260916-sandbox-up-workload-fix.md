# Issue: [Bugfix] af sandbox up 워크로드 미배포 및 CLI 충돌 결함 수정

- **Status**: Completed
- **Labels**: `type:bugfix`, `stage:done`, `status:completed`
- **Date**: 2026-09-16

## 1. 결함 요약
1. `af sandbox up` 실행 시 `charts/` 디렉토리(Helm)만 검사하여, AgentForge의 표준 구조인 `k8s/dev` 쿠버네티스 순수 매니페스트가 배포되지 않고 파드가 0개인 빈 네임스페이스만 생성되는 결함.
2. `SandboxManager.get_namespace("sandbox-a08126")` 호출 시 접두사가 중복되어 `sandbox-sandbox-a08126`이 되는 결함.
3. `./af` 래퍼 스크립트에서 전역 `af` 미설치 시 `uvx agentforge`를 호출하여 제3자 PyPI 패키지와 충돌하고 실패하는 결함.
4. `k8s/dev` 템플릿의 `metadata.namespace: ai-agents` 하드코딩 및 `app.kubernetes.io/component` 라벨 누락.

## 2. 해결 목표
- `SandboxManager.get_namespace`에서 `sandbox-` 중복 접두사 정규화.
- `af sandbox up`에서 `k8s/dev` 매니페스트를 감지하여 샌드박스 네임스페이스로 변환/배포하는 기능 추가.
- `k8s/dev` 템플릿의 하드코딩된 네임스페이스 제거 및 표준 컴포넌트 라벨 추가.
- `./af` 및 `af.bat` 래퍼 스크립트의 실행 안전성 확보.
