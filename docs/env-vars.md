# 🌱 환경 변수 & 거버넌스 가이드 (Environment Variables Guide)

> [🏠 README](../README.md) &nbsp;|&nbsp; [⚡ Quickstart](quickstart.md) &nbsp;|&nbsp; [⚙️ CLI & Scaffolding](cli.md) &nbsp;|&nbsp; [🏗️ Architecture](architecture.md) &nbsp;|&nbsp; [🛠️ AI Skills](skills.md) &nbsp;|&nbsp; [🐳 Infrastructure](infrastructure.md) &nbsp;|&nbsp; **[🌱 Env Variables](env-vars.md)**

---

AgentForge로 생성된 프로젝트는 **12-Factor App 원칙**에 따라 코드와 설정을 엄격히 분리하며, 백엔드와 프론트엔드 각각 활성 환경 변수(`.env`)와 공개 참조 템플릿(`.env.sample`)을 이원화하여 관리합니다.

---

## 1. 백엔드 환경 변수 (`backend/.env` & `backend/.env.sample`)

스캐폴딩 엔진에 의해 프로젝트 생성 시 프로젝트명과 난수 시크릿 키가 자동으로 치환되어 채워집니다.

| 환경 변수명 | 기본값 (스캐폴딩 초기값) | 필수 여부 | 설명 |
| :--- | :--- | :---: | :--- |
| **`PROJECT_NAME`** | `<project_name>` | **필수** | 서비스 애플리케이션 명칭 및 로깅 태그 |
| **`ENVIRONMENT`** | `development` | 선택 | 실행 환경 (`development`, `staging`, `production`) |
| **`PORT`** | `8000` | 선택 | FastAPI 백엔드 HTTP 리스닝 포트 |
| **`LOG_LEVEL`** | `INFO` | 선택 | 구조화 JSON 로깅 레벨 (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| **`DATABASE_URL`** | `postgresql+asyncpg://...` | **필수** | PostgreSQL 비동기 접속 URI |
| **`DATABASE_HOST`** | `localhost` | 선택 | 데이터베이스 호스트 주소 |
| **`DATABASE_PORT`** | `5432` | 선택 | PostgreSQL 기본 포트 |
| **`DATABASE_USER`** | `postgres` | 선택 | 데이터베이스 사용자 계정 |
| **`DATABASE_PASSWORD`**| `postgres` | 선택 | 데이터베이스 비밀번호 |
| **`DATABASE_DBNAME`**  | `<project_name_snake>` | **필수** | 타겟 데이터베이스 이름 |
| **`REDIS_URL`** | `redis://localhost:6379/0` | **필수** | Redis 7+ 분산 세션 스토어 접속 URI |
| **`REDIS_HOST`** | `localhost` | 선택 | Redis 호스트 |
| **`REDIS_PORT`** | `6379` | 선택 | Redis 포트 |
| **`JWT_SECRET_KEY`** | `<project_name>-secret-key` | **필수** | Native JWT Access/Refresh 토큰 서명용 비밀키 |
| **`JWT_ALGORITHM`** | `HS256` | 선택 | 토큰 암호화 서명 알고리즘 |
| **`ACCESS_TOKEN_EXPIRE_MINUTES`** | `30` | 선택 | 단기 엑세스 토큰 만료 시간 (분) |
| **`REFRESH_TOKEN_EXPIRE_DAYS`** | `7` | 선택 | 장기 리프레시 토큰 만료 시간 (일) |
| **`DEFAULT_ADMIN_PASSWORD`** | `admin1234!` | 선택 | 최초 DB 마이그레이션 시 자동 생성될 `admin` 계정 비밀번호 |
| **`LANGFUSE_ENABLED`** | `true` | 선택 | Langfuse LLM 관측성 추적 활성화 여부 (`true`/`false`) |
| **`LANGFUSE_HOST`** | `http://localhost:3000` | 선택 | Langfuse 웹 대시보드 API 주소 |
| **`LANGFUSE_PUBLIC_KEY`** | `pk-lf-...` | 선택 | Langfuse 프로젝트 공개 키 |
| **`LANGFUSE_SECRET_KEY`** | `sk-lf-...` | 선택 | Langfuse 프로젝트 비밀 키 |
| **`OPENSEARCH_URL`** | `http://localhost:9200` | 선택 | OpenSearch 2.19+ REST API 엔드포인트 |
| **`OPENSEARCH_USER`**| `admin` | 선택 | OpenSearch 관리자 사용자명 |
| **`OPENSEARCH_PASSWORD`** | `admin` | 선택 | OpenSearch 관리자 비밀번호 |
| **`LDAP_SERVER_URI`**| `ldap://localhost:389` | 선택 | 사내 Active Directory / LDAP 서버 URI |
| **`SAML_IDP_METADATA_URL`** | `""` | 선택 | 기업 IdP(Okta, Keycloak 등) SAML 메타데이터 URL |

---

## 2. 프론트엔드 환경 변수 (`frontend/.env` & `frontend/.env.sample`)

프론트엔드 빌드 시 클라이언트에 주입되는 Vite 환경 변수입니다.

| 환경 변수명 | 기본값 | 설명 |
| :--- | :--- | :--- |
| **`VITE_API_BASE_URL`** | `http://localhost:8000` | 백엔드 FastAPI REST API 서버의 기본 엔드포인트 URL |
| **`VITE_DEV_PROXY_TARGET`** | `http://127.0.0.1:8000` | 로컬 개발 시 CORS 우회를 위한 Vite 개발 프록시 대상 주소 |
| **`VITE_APP_TITLE`** | `<project_name>` | 브라우저 탭 및 상단 네비게이션 바에 표시되는 서비스 타이틀 |

---

## 3. 보안 거버넌스 및 자동화 연동 규칙

1. **Git 버전 관리 격리**:
   - `.env` 파일은 실제 패스워드 및 시크릿 키를 포함하므로 **`.gitignore`에 등록되어 원격 저장소 커밋이 원천 차단**됩니다.
   - `.env.sample` 파일만 저장소에 커밋하여 팀원 간 최신 환경 변수 사양을 공유합니다.
2. **원클릭 자동 초기화 (`run.sh` / `setup.sh`)**:
   - 저장소를 새로 클론한 팀원이 로컬 실행 시 `.env` 파일이 없으면 스크립트가 자동으로 `.env.sample`을 복사하여 `.env`를 생성하므로 즉시 구동할 수 있습니다.
3. **운영 환경(Kubernetes) 주입**:
   - 운영 클러스터 배포 시에는 `.env` 파일 대신 Kubernetes `ConfigMap` 및 `Secret` 오브젝트를 통해 파드(Pod)에 안전하게 환경 변수가 주입됩니다.

---

> [🏠 README](../README.md) &nbsp;|&nbsp; [⚡ Quickstart](quickstart.md) &nbsp;|&nbsp; [⚙️ CLI & Scaffolding](cli.md) &nbsp;|&nbsp; [🏗️ Architecture](architecture.md) &nbsp;|&nbsp; [🛠️ AI Skills](skills.md) &nbsp;|&nbsp; [🐳 Infrastructure](infrastructure.md) &nbsp;|&nbsp; **[🌱 Env Variables](env-vars.md)**
