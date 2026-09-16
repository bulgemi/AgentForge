# 🐳 로컬 인프라 & 배포 가이드 (Infrastructure & Deployment Guide)

> [🏠 README](../README.md) &nbsp;|&nbsp; [⚡ Quickstart](quickstart.md) &nbsp;|&nbsp; [⚙️ CLI & Scaffolding](cli.md) &nbsp;|&nbsp; [🏗️ Architecture](architecture.md) &nbsp;|&nbsp; [🛠️ AI Skills](skills.md) &nbsp;|&nbsp; **[🐳 Infrastructure](infrastructure.md)** &nbsp;|&nbsp; [🏖️ Sandbox](sandbox.md) &nbsp;|&nbsp; [🌱 Env Variables](env-vars.md)

---

AgentForge로 생성된 프로젝트는 개발자의 로컬 환경과 프로덕션 클러스터 배포를 위해 **Docker Compose 멀티 프로파일**과 **환경 분리형 Kubernetes 매니페스트**를 기본 제공합니다.

---

## 1. Docker Compose 서비스 스택 & 프로파일 (Compose Profiles)

`docker-compose.yml`은 모든 컨테이너를 한 번에 띄워 리소스를 낭비하지 않도록, 개발 목적에 따라 선택적으로 구동 가능한 **6개의 프로파일**로 구성되어 있습니다:

| 서비스 컨테이너명 | 이미지 및 버전 | 소속 프로파일 (`--profile`) | 주요 역할 및 용도 |
| :--- | :--- | :--- | :--- |
| **`postgres`** | `postgres:16-alpine` | `infra`, `all` | 메인 관계형 데이터베이스 (사용자, 세션, 대화 이력) |
| **`redis`** | `redis:7.4-alpine` | `infra`, `all` | 고속 인메모리 분산 세션 스토어 & 토큰 블랙리스트 |
| **`clickhouse`** | `clickhouse/clickhouse-server:24.3-alpine` | `infra`, `observability`, `all` | Langfuse v3 시계열 트레이스/원격 메트릭 저장소 |
| **`minio`** | `minio/minio:RELEASE.2024-05-10...` | `infra`, `observability`, `all` | S3 호환 객체 스토리지 (Langfuse 대용량 페이로드 보관) |
| **`minio-setup`** | `minio/mc:latest` | `infra`, `observability`, `all` | MinIO 초기 버킷(`langfuse`) 자동 생성 일회성 배치 |
| **`langfuse`** | `langfuse/langfuse:3` | `infra`, `observability`, `all` | LLM Observability 모니터링 웹 대시보드 |
| **`langfuse-worker`** | `langfuse/langfuse-worker:3` | `infra`, `observability`, `all` | Langfuse 비동기 이벤트 수집 & 인덱싱 백그라운드 워커 |
| **`opensearch`** | `opensearchproject/opensearch:2.19.3` | `infra`, `search`, `audit`, `all` | 분산 검색 엔진, k-NN 벡터 인덱스 & 감사 로그 저장 |
| **`opensearch-init`** | `curlimages/curl:latest` | `infra`, `search`, `audit`, `all` | OpenSearch 인덱스 템플릿 자동 프로비저닝 배치 |
| **`opensearch-dashboards`** | `opensearch-dashboards:2.19.3` | `infra`, `search`, `audit`, `all` | OpenSearch 관리 대시보드 & 시각화 웹 콘솔 |
| **`backend`** | 로컬 빌드 (`Dockerfile`) | `app`, `all` | FastAPI 백엔드 API 서버 |
| **`frontend`** | 로컬 빌드 (`Dockerfile`) | `app`, `all` | Nginx 기반 Vite React 웹 애플리케이션 |

---

## 2. 프로파일별 실행 및 관리 명령어

> ⚠️ **중요 (Profile 필수)**: 모든 컨테이너 서비스에 프로파일이 지정되어 있으므로, `--profile` 옵션 없이 `docker compose up -d`를 실행하면 `no service selected` 안내와 함께 어떤 컨테이너도 실행되지 않습니다. 반드시 아래와 같이 프로파일을 지정해야 합니다.

```bash
# 1. 로컬 개발 표준 (권장): 백엔드/프론트엔드를 제외한 모든 인프라 동시 실행
docker compose --profile infra up -d

# 2. LLM 관측성 스택만 실행 (Langfuse Web, Worker, ClickHouse, MinIO)
docker compose --profile observability up -d

# 3. 검색 및 벡터 스택만 실행 (OpenSearch, Dashboards, Init)
docker compose --profile search up -d

# 4. 풀스택 모든 컨테이너 실행 (백엔드 및 프론트엔드 컨테이너 포함)
docker compose --profile all up -d

# 5. 실행 중인 컨테이너 상태 확인
docker compose --profile infra ps

# 6. 인프라 전체 종료
docker compose --profile infra down
```

---

## 3. 주요 서비스 웹 대시보드 & 기본 계정

| 서비스 | 접속 URL | 기본 로그인 계정 | 설명 |
| :--- | :--- | :--- | :--- |
| **사용자 포털 (Chat)** | [http://localhost:5173](http://localhost:5173) | `admin` / `admin1234!` | 실시간 토큰 스트리밍 AI 채팅 포털 |
| **관리자 콘솔 (Admin)** | [http://localhost:5173/admin.html](http://localhost:5173/admin.html) | `admin` / `admin1234!` | 사용자 계정 관리, 잠금 해제 거버넌스 콘솔 |
| **백엔드 Swagger API** | [http://localhost:8000/docs](http://localhost:8000/docs) | 없음 (공개 API 문서) | OpenAPI 사양 기반 백엔드 엔드포인트 테스트 |
| **Langfuse 관측성** | [http://localhost:3000](http://localhost:3000) | 최초 접속 시 가입 | LLM 트레이스, 토큰 비용, 레이턴시 모니터링 |
| **OpenSearch Dashboards**| [http://localhost:5601](http://localhost:5601) | `admin` / `admin` | 인덱스 관리, 벡터 검색 및 감사 로그 시각화 |

---

## 4. 로컬 원클릭 런처 연동 (`run.sh` / `run.bat`)

생성된 프로젝트 루트에는 로컬 개발 환경을 단 1초 만에 준비하는 원클릭 스크립트가 내장되어 있습니다:

```bash
# macOS / Linux
./run.sh

# Windows
run.bat
```

### 스크립트 내부 자동화 흐름:
1. 로컬 환경 변수(`.env`)가 없으면 `.env.sample`을 참조하여 자동 생성
2. Docker 데몬 실행 상태 감지 후 `docker compose --profile infra up -d` 자동 기동
3. 백엔드 가상환경(`.venv`) 및 의존성(`uv sync` 또는 `pip install`) 자동 구성
4. 프론트엔드 의존성(`npm install`) 확인
5. 백엔드(포트 8000)와 프론트엔드(포트 5173) 개발 서버 동시 실행 및 브라우저 오픈

> 💡 **의존성만 사전 설치하려는 경우**: `./setup.sh` (Windows: `setup.bat`)를 실행하면 서버를 띄우지 않고 가상환경과 패키지만 설치합니다.

---

## 5. Kubernetes 클러스터 실전 배포 (`k8s/`)

AgentForge로 생성된 프로젝트의 `k8s/` 디렉토리에는 개발(Dev) 및 운영(Prod) 환경으로 엄격히 분리된 실전 배포 매니페스트가 포함되어 있습니다.

```text
k8s/
├── dev/                           # 개발 환경 (경량 리소스)
│   ├── backend.yaml
│   ├── frontend.yaml
│   └── configmap.yaml
├── prd/                           # 운영 환경 (고가용성 다중 Replica, HPA, 리소스 제한)
│   ├── backend.yaml
│   ├── frontend.yaml
│   └── ingress.yaml
└── k8s-deploy.sh                  # 원클릭 배포 쉘 스크립트
```

### 배포 명령어

```bash
# CLI 명령어 이용
af deploy --env dev                # 개발 환경 배포
af deploy --env prd                # 운영 환경 배포

# 또는 직접 쉘 스크립트 실행
./k8s/k8s-deploy.sh dev
./k8s/k8s-deploy.sh prd
```

---

## 6. Rancher Apps & Marketplace를 통한 Helm 카탈로그 배포 (`charts/`)

AgentForge는 **Rancher**(https://github.com/rancher/rancher)의 대규모 쿠버네티스 관리 환경 및 클라우드 프로덕션 배포를 위해 전용 **Helm Chart 및 Rancher Apps & Marketplace 카탈로그 규격**을 기본 생성합니다.

```text
charts/my-agent/
├── Chart.yaml                     # Helm v2 차트 메타데이터
├── values.yaml                    # 기본 파라미터 (ALB/NGINX Ingress, RDS, ElastiCache, IRSA)
├── questions.yaml                 # Rancher 대시보드 시각적 웹 폼 명세
├── app-readme.md                  # Rancher UI 카탈로그 카드 안내문
├── README.md                      # 파라미터 상세 기술 문서
└── templates/                     # 쿠버네티스 템플릿
```

### Helm 차트 패키징 (`af package`)
```bash
af package --target rancher        # dist/charts/에 .tgz 및 index.yaml 생성
```

---

## 7. 다중 CSP (AWS EKS, GCP GKE, Azure AKS) 개발자 샌드박스 (`af sandbox`)

개발자가 클라우드 K8s 환경에서 자신만의 독립된 환경을 즉시 생성하고 로컬 코드와 실시간 연동하며 개발할 수 있는 **온디맨드 개발자 샌드박스** 기능을 제공합니다.

### 1) 다중 CSP 지원 매트릭스
- **AWS EKS**: AWS ALB Controller Ingress & IRSA (`eks.amazonaws.com/role-arn`)
- **GCP GKE**: GKE Ingress & Workload Identity (`iam.gke.io/gcp-service-account`)
- **Azure AKS**: Application Gateway Ingress & Workload Identity (`azure.workload.identity/client-id`)

### 2) 샌드박스 CLI 사용법

```bash
# 1. 샌드박스 프로비저닝 (AWS EKS, 8시간 TTL 기본)
af sandbox up --csp aws --name alice --ttl 8h

# 2. GCP GKE 또는 Azure AKS에 생성
af sandbox up --csp gcp --name alice
af sandbox up --csp azure --name alice

# 3. 로컬 코드 실시간 동기화 (Hot-Reload)
af sandbox watch                   # backend/src 소스 수정 시 원격 Pod로 0.5초 내 동기화

# 4. 웹 포털 브라우저 오픈 또는 로컬 포트포워딩
af sandbox open                    # https://alice.sandbox.myagent.io 접속
af sandbox open --port-forward     # localhost:5173 -> pod:80 터널링

# 5. 유휴 시 절전 (Replica=0 축소로 클라우드 비용 절감)
af sandbox pause
af sandbox resume

# 6. 상태 점검 및 완전 삭제
af sandbox status
af sandbox down --force
```

### 3) 로컬 환경에서의 Rancher 기반 샌드박스 테스트 (Local Testing)

클라우드 비용 없이 로컬 머신(`Docker` + `Minikube`)에서 Rancher 컨테이너와 샌드박스 라이프사이클을 100% 동일하게 검증할 수 있습니다:

1. **로컬 Minikube 및 Rancher Server 기동**:
   ```bash
   minikube start
   docker run -d --restart=unless-stopped -p 8080:80 -p 8443:443 --privileged rancher/rancher:latest
   ```
2. **Rancher 접속 및 Minikube Import**:
   - 브라우저로 `https://localhost:8443` 접속
     > 💡 **접속 트러블슈팅**:
     > - **초기 부팅 대기**: K3s/etcd 초기화로 인해 컨테이너 기동 후 약 1~2분 정도 소요될 수 있습니다.
     > - **SSL 인증서 경고**: 브라우저에서 [고급] ➔ [이동] 클릭 (Chrome에서 차단 시 빈 화면에서 `thisisunsafe` 입력).
     > - **초기 비밀번호 확인**: `docker logs rancher-local 2>&1 | grep "Bootstrap Password:"` 실행
     > - **포트/프로토콜**: `https://localhost:8443` 또는 `http://localhost:8080` (자동 리다이렉트) 사용
   - 초기 부트스트랩 비밀번호 입력 후 새 비밀번호를 `admin1234!@#$`로 설정하고 로그인
   - **Cluster Management** ➔ **Import Existing** 선택 후 클러스터 이름(`local-minikube`) 입력
   - 발급된 `curl ... | kubectl apply -f -` 명령어를 터미널에서 실행하여 Minikube를 Rancher에 연동
3. **로컬 와일드카드 도메인(`nip.io`)으로 샌드박스 생성**:
   ```bash
   af sandbox up --name dev-local --domain 127.0.0.1.nip.io
   af sandbox watch                    # 로컬 코드 핫리로드
   af sandbox open --port-forward      # 로컬호스트 포트포워딩
   ```

---

> [🏠 README](../README.md) &nbsp;|&nbsp; [⚡ Quickstart](quickstart.md) &nbsp;|&nbsp; [⚙️ CLI & Scaffolding](cli.md) &nbsp;|&nbsp; [🏗️ Architecture](architecture.md) &nbsp;|&nbsp; [🛠️ AI Skills](skills.md) &nbsp;|&nbsp; **[🐳 Infrastructure](infrastructure.md)** &nbsp;|&nbsp; [🏖️ Sandbox](sandbox.md) &nbsp;|&nbsp; [🌱 Env Variables](env-vars.md)
