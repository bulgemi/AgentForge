# Issue: [Bugfix] af sandbox up ImagePullBackOff 결함 및 af build 이미지 태그 불일치 수정

- **Status**: Completed
- **Labels**: `type:bugfix`, `stage:done`, `status:completed`
- **Date**: 2026-09-16

## 1. 결함 요약
1. `af sandbox up` 실행 시 쿠버네티스 워크로드(`k8s/dev/*.yaml`)를 배포하지만, 노드(Minikube) 및 로컬 환경에 컨테이너 이미지가 없거나 빌드/로드가 수행되지 않아 파드가 `ImagePullBackOff`로 멈추는 현상 발생.
2. `af build` CLI 명령어에서 이미지 태그가 `agent-backend:{tag}`, `agent-frontend:{tag}`로 하드코딩되어 있어, 프로젝트명 기반 매니페스트(`af_test002-backend:latest`)와 불일치하는 결함.
3. 로컬 Minikube 클러스터 환경에서 호스트 Docker와 Minikube 내부 데몬이 분리되어 있어, 빌드된 이미지를 `minikube image load`로 로드하지 않으면 인식할 수 없는 문제.
4. 프론트엔드 Nginx의 `proxy_pass http://backend:8000;` 설정과 쿠버네티스 서비스 명명(`af-test002-backend`) 간의 불일치로 인한 Nginx 기동 실패(`host not found in upstream "backend"`).

## 2. 해결 내용
1. `agentforge/cli/commands/build.py`: 현재 프로젝트명(`current_dir.name`)을 반영하여 `{project_name}-backend:{tag}`, `{clean_name}-backend:{tag}`, `agent-backend:{tag}` 다중 태깅 지원.
2. `agentforge/cli/commands/sandbox.py`: `sandbox_up`에 `--build / --no-build` 플래그 추가 및 Minikube 클러스터 감지 시 자동 빌드 & `minikube image load` 파이프라인 연계.
3. `agentforge/sandbox/manager.py`:
   - `is_minikube_cluster()` 및 `load_images_to_minikube()` 메서드 구현.
   - `deploy_k8s_workloads`에서 프론트엔드 Nginx 프록시 호환을 위한 `backend` Service alias 자동 생성.
4. `tests/test_sandbox_image_build.py`: 단위 및 통합 재현 테스트 작성 및 219개 전체 테스트 스위트 회귀 검증 통과.
5. `af_test002` 실전 검증: Backend 및 Frontend 파드 모두 `1/1 Running` 상태 달성.
