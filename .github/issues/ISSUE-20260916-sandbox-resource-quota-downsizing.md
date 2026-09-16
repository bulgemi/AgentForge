# Issue: 샌드박스(Sandbox) 기본 리소스 쿼터 최소 자원 축소

## 메타데이터
- **ID**: ISSUE-20260916-sandbox-resource-quota-downsizing
- **타입**: Enhancement / Optimization
- **상태**: Completed / Closed
- **담당**: AgentForge AI Developer Harness

## 배경 및 목적
현재 샌드박스 생성 시 `ResourceQuota` 상한이 `limits.cpu=4000m`(4Core), `limits.memory=8Gi`로 높게 설정되어 있어 로컬 Minikube 또는 소형 온디맨드 노드에서 과도한 리소스 예약을 유발할 수 있습니다.
이를 안정적으로 기동 가능한 최소 자원인 `limits.cpu=2000m`(2Core), `limits.memory=2Gi`로 하향 조정하고, 이에 맞춰 `requests` 및 `LimitRange` 기본값을 최적화합니다.

## 세부 작업 내역
1. `agentforge/templates/sandbox/resourcequota.yaml` 리소스 조정:
   - ResourceQuota:
     - `requests.cpu`: 1000m -> 500m
     - `requests.memory`: 2Gi -> 1Gi
     - `limits.cpu`: 4000m -> 2000m
     - `limits.memory`: 8Gi -> 2Gi
   - LimitRange:
     - Container default: cpu 1000m -> 500m, memory 1Gi -> 512Mi
     - Container defaultRequest: cpu 100m, memory 128Mi 유지
2. `docs/sandbox.md` 설명 수정:
   - ResourceQuota 관련 수치(4Core/8Gi -> 2Core/2Gi) 갱신
3. `tests/test_sandbox_manager.py` 테스트 케이스 강화:
   - 생성된 `resourcequota.yaml` 매니페스트 내 리소스 수치 검증 assertion 추가
