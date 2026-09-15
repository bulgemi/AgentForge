# Issue: [Bugfix] backend/Dockerfile 프로세스 치환 문법 오류로 인한 빌드 실패 수정

- **Status**: Completed
- **Labels**: `type:bugfix`, `stage:done`, `status:completed`
- **Date**: 2026-09-16

## 1. 결함 요약
- `backend/Dockerfile` 내 `RUN uv pip install --no-cache --system -r <(uv pip compile pyproject.toml)` 실행 시, 기본 셸인 `/bin/sh`(`dash`)에서 Bash 전용 문법인 프로세스 치환(`<(...)`)을 인식하지 못하고 `/bin/sh: 1: Syntax error: "(" unexpected` 에러를 발생시키며 이미지 빌드가 실패하는 결함.
- AgentForge 템플릿(`agentforge/templates/backend/Dockerfile`) 및 이미 생성된 프로젝트(`af_test002/backend/Dockerfile`)에 모두 존재하는 결함.

## 2. 해결 내용
- `backend/Dockerfile`에서 POSIX 표준 `/bin/sh` 호환 구문으로 변경:
  ```dockerfile
  COPY pyproject.toml .
  RUN uv pip compile pyproject.toml -o requirements.txt && \
      uv pip install --no-cache --system -r requirements.txt
  ```
- 대상 파일:
  - `agentforge/templates/backend/Dockerfile` (AgentForge 원본 템플릿)
  - `af_test002/backend/Dockerfile` (생성된 프로젝트)

## 3. 검증 결과
- `af_test002` 프로젝트 루트에서 `./af build` 실행 결과:
  - `agent-backend:latest`: 93개 의존성 패키지 정상 컴파일 및 이미지 빌드 완료 (`exit code: 0`)
  - `agent-frontend:latest`: Vite 프로덕션 빌드 및 Nginx 이미지 빌드 완료 (`exit code: 0`)
  - 전체 빌드 최종 성공: `✓ Docker build completed successfully!`
- AgentForge 단위/통합 회귀 테스트 통과:
  - `pytest tests/test_generator.py tests/test_cli.py` (23 passed in 23.47s)
