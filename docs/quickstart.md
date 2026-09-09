# ⚡ AgentForge 3분 사용자 가이드 (Quickstart Guide)

> **AgentForge로 3분 만에 독립형 AI 에이전트 풀스택 서비스를 구축하고 실행하는 가이드입니다.**  
> 프로젝트 생성부터 환경 변수 설정, 원클릭 서버 기동, 그리고 생성된 웹 포털 및 관리자 콘솔 화면 활용법까지 단계별로 안내합니다.

---

## 📑 목차 (Table of Contents)

1. [1단계: 프로젝트 생성 (`af new`)](#1단계-프로젝트-생성-af-new)
2. [2단계: 환경 설정 (`.env`)](#2단계-환경-설정-env)
3. [3단계: 원클릭 프로젝트 기동 (`run.sh` / `af dev`)](#3단계-원클릭-프로젝트-기동-runsh--af-dev)
4. [4단계: 생성 프로젝트 화면 및 주요 기능 둘러보기 (UI Walkthrough)](#4단계-생성-프로젝트-화면-및-주요-기능-둘러보기-ui-walkthrough)
   - [4-1. 엔터프라이즈 통합 로그인 포털](#4-1-엔터프라이즈-통합-로그인-포털-enterprise-multi-auth-login)
   - [4-2. AI 에이전트 채팅 포털 & 실시간 실행 콘솔](#4-2-ai-에이전트-채팅-포털--실시간-실행-콘솔-agent-chat--live-execution-console)
   - [4-3. 관리자 콘솔 - 사용자 및 권한 관리](#4-3-관리자-콘솔---사용자-및-권한-관리-admin-console-security--account-governance)
   - [4-4. 관리자 콘솔 - 신규 사용자 등록 모달](#4-4-관리자-콘솔---신규-사용자-등록-모달-new-user-registration-modal)

---

## 1단계: 프로젝트 생성 (`af new`)

터미널에서 `af new` (또는 `agentforge new`) 명령어를 실행하여 원하는 프레임워크와 프론트엔드 조합의 독립형(Standalone) 프로젝트를 즉시 생성합니다.

```bash
# 가장 권장되는 기본 조합 (LangGraph + React + Clean Architecture)
af new my-awesome-agent --framework langgraph --frontend react

# 또는 다른 에이전트 프레임워크 선택 (langchain, deepagent, adk, bedrock)
af new finance-bot -f bedrock -ui react
```

### 💡 주요 옵션 플래그
- `-f, --framework`: 지원 에이전트 프레임워크 (`langgraph` [기본값], `langchain`, `deepagent`, `adk`, `bedrock`)
- `-ui, --frontend`: 프론트엔드 UI 스택 (`react` [기본값, Vite SPA], `streamlit`, `none` [Headless API])
- `-p, --path`: 프로젝트 생성 대상 디렉토리 (기본값: 현재 폴더 `.`)

생성이 완료되면 외부 의존성이 전혀 없는 독립된 풀스택 모노레포(`my-awesome-agent/`)가 완성됩니다.

---

## 2단계: 환경 설정 (`.env`)

생성된 프로젝트 디렉토리로 이동합니다.

```bash
cd my-awesome-agent
```

AgentForge 프로젝트는 **Backend**와 **Frontend** 각각에 `.env`와 `.env.sample`을 기본 제공하며, 스캐폴딩 시 로컬 `.env`가 기본값으로 자동 생성됩니다.

### 1) 백엔드 환경 변수 (`backend/.env`)

사용할 LLM 공급자의 API 키를 `backend/.env`에 입력합니다:

```ini
# backend/.env

PROJECT_NAME=my-awesome-agent
ENVIRONMENT=dev

# 1. LLM 공급자 및 모델 설정 (선택 프레임워크에 맞춤 설정)
LLM_PROVIDER=openai                       # openai | gemini | anthropic | bedrock
OPENAI_API_KEY=sk-...                     # OpenAI API 키
OPENAI_MODEL_NAME=gpt-4o

# (선택) 다른 공급자 사용 시
# GOOGLE_API_KEY=AIzaSy...
# ANTHROPIC_API_KEY=sk-ant-...

# 2. 인프라 연결 설정 (기본 로컬 인프라 기준 자동 세팅됨)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/my_awesome_agent
REDIS_URL=redis://localhost:6379/0

# 3. 보안 및 초기 관리자 설정
DEFAULT_ADMIN_PASSWORD=admin1234!         # 최초 기동 시 자동 시딩될 admin 계정 비밀번호
JWT_SECRET_KEY=your-custom-secret-key-min-32-chars
```

### 2) 프론트엔드 환경 변수 (`frontend/.env`)

프론트엔드는 로컬 개발 프록시가 기본 구성되어 있어 추가 수정 없이 즉시 실행할 수 있습니다:

```ini
# frontend/.env
VITE_APP_TITLE=my-awesome-agent
VITE_API_BASE_URL=/api/v1
VITE_DEV_PROXY_TARGET=http://localhost:8000
VITE_ADMIN_URL=/admin.html
```

---

## 3단계: 원클릭 프로젝트 기동 (`run.sh` / `af dev`)

AgentForge 프로젝트는 로컬 인프라 컨테이너부터 백엔드, 프론트엔드 개발 서버까지 한 번에 띄울 수 있는 원클릭 스크립트를 제공합니다.

### 실행 방법

```bash
# macOS / Linux
./run.sh

# Windows
run.bat

# 또는 CLI 명령어 사용 시
af dev
```

> 🐳 **Docker Compose 자동 연동**:  
> 로컬에 Docker가 실행 중인 경우, `./run.sh`가 필수 인프라(PostgreSQL, Redis, Langfuse, OpenSearch)를 `docker compose --profile infra up -d`로 백그라운드 구동한 뒤 백엔드와 프론트엔드를 동시 기동합니다.

### 접속 엔드포인트 URL 안내

| 서비스 | 접속 URL | 설명 |
| :--- | :--- | :--- |
| **사용자 AI 채팅 포털** | [http://localhost:5173/](http://localhost:5173/) | 일반 사용자 및 관리자 AI 대화 인터페이스 |
| **관리자 콘솔 포털** | [http://localhost:5173/admin.html](http://localhost:5173/admin.html) | 계정 및 권한 거버넌스 대시보드 |
| **백엔드 API Swagger** | [http://localhost:8000/docs](http://localhost:8000/docs) | FastAPI 대화형 REST API 문서 |
| **Langfuse LLM 관측성** | [http://localhost:3000](http://localhost:3000) | LLM 호출 단계별 트레이싱 대시보드 |

#### 🔑 기본 관리자 로그인 계정 (초기 시딩)
- **아이디 (Username)**: `admin`
- **비밀번호 (Password)**: `admin1234!` (또는 `backend/.env`의 `DEFAULT_ADMIN_PASSWORD`)
- **역할 (Role)**: `admin` (사용자 포털 및 관리자 콘솔 전체 접근 가능)

---

## 4단계: 생성 프로젝트 화면 및 주요 기능 둘러보기 (UI Walkthrough)

AgentForge로 생성된 프로젝트의 실제 UI 화면과 핵심 기능을 둘러봅니다.

---

### 4-1. 엔터프라이즈 통합 로그인 포털 (Enterprise Multi-Auth Login)

브라우저에서 `http://localhost:5173/`에 접속하면 모던한 통합 인증 화면이 나타납니다.

<div align="center">
  <img src="images/screenshot_login.png" alt="Enterprise Multi-Auth Login Screen" width="850" />
</div>

- **다중 인증(Multi-Auth) 탭 전환**:
  - **ID / Password**: 일반 로컬 DB 계정 로그인 탭. 최초 생성된 `admin` / `admin1234!`로 바로 로그인할 수 있습니다.
  - **사내 LDAP**: 사내 Active Directory 또는 OpenLDAP 계정 연동 탭을 기본 탑재하여 기업 사번/계정으로 인증할 수 있습니다.
- **SAML 2.0 Single Sign-On (SSO)**:
  - 하단의 `SAML 2.0 Single Sign-On` 버튼을 통해 Okta, Keycloak, Azure AD 등 기업 엔터프라이즈 IdP와 연동된 원클릭 SSO 로그인을 지원합니다.
- **프로젝트 아이덴티티 자동 반영**:
  - 스캐폴딩 시 지정한 프로젝트 이름(예: `af_test001`)과 플랫폼 로고가 자동으로 바인딩되어 통일된 브랜딩을 제공합니다.

---

### 4-2. AI 에이전트 채팅 포털 & 실시간 실행 콘솔 (Agent Chat & Live Execution Console)

로그인 후 진입하는 메인 대화 화면입니다. 사용자는 실시간으로 AI 에이전트와 소통하고, 우측 실행 콘솔을 통해 내부 동작을 실시간 모니터링할 수 있습니다.

<div align="center">
  <img src="images/screenshot_chat.png" alt="Agent Chat and Live Console Screen" width="850" />
</div>

- **실시간 SSE 토큰 스트리밍**:
  - Server-Sent Events(`POST /api/v1/chat/stream`) 연결을 통해 에이전트의 답변 토큰이 지연 없이 실시간으로 스트리밍 렌더링됩니다.
  - 상단 헤더의 녹색 `Connected (SSE Stream)` 상태 표시등을 통해 실시간 통신 상태를 상시 점검합니다.
  - 마크다운 서식(제목, 불릿, 이모지, 코드 블록 등)을 완벽하게 지원합니다.
- **실시간 에이전트 실행 콘솔 (`>_ Console` / Terminal Console)**:
  - 우측의 **`AGENT EXECUTION CONSOLE`** 창은 에이전트의 실시간 실행 상태(`Idle`, `Thinking`, `Streaming`)를 배지로 보여줍니다.
  - 사용자가 전송한 프롬프트의 타임스탬프(`[오전 10:14:40] Prompt sent: "..."`), 단계별 심층 추론(Thinking Process), Tool/Function Calling 단계 로그를 터미널 스타일로 실시간 출력합니다.
  - 헤더의 `>_ Console` 버튼을 클릭하여 작업 공간에 맞게 언제든지 콘솔 창을 열거나 접을 수 있습니다.
- **상단 헤더 세션 관리**:
  - 현재 로그인 계정 및 역할 표시(`admin (admin)`)
  - `비밀번호 변경` 다이얼로그
  - 관리자 권한(`admin`) 보유 시 나타나는 `관리자 콘솔` 원클릭 이동 버튼
  - 안전한 세션 종료를 위한 `로그아웃` 버튼

---

### 4-3. 관리자 콘솔 - 사용자 및 권한 관리 (Admin Console: Security & Account Governance)

헤더의 `관리자 콘솔` 버튼을 누르거나 `http://localhost:5173/admin.html`로 접속하면 나타나는 관리자 전용 거버넌스 대시보드입니다.

<div align="center">
  <img src="images/screenshot_admin_users.png" alt="Admin Console User Management" width="850" />
</div>

- **중앙 집중형 계정 거버넌스 (`/admin.html`)**:
  - 1개의 Vite 프로젝트에서 번들링되는 독립된 관리자 전용 SPA 진입점입니다.
  - 관리자(`ADMIN`) 권한을 가진 계정만 접근할 수 있도록 보안 라우트 가드가 적용되어 있습니다.
- **사용자 조회, 검색 및 필터링**:
  - 아이디 또는 이메일 키워드 검색 인풋
  - 권한별(`전체 권한`, `ADMIN`, `USER`) 드롭다운 필터 및 `조회` 버튼
- **사용자 상태 시각화**:
  - 사용자 아이디, 등록 이메일, 배정 권한(`ADMIN`, `USER` 컬러 배지), 계정 상태(`active`, `locked` 배지) 표시
- **보안 관리 액션**:
  - 개별 사용자의 **`비밀번호 초기화`** 원클릭 실행 (임시 비밀번호 발급)
  - 계정 잠금 해제 등 계정 라이프사이클 통제
- **포털 즉시 복귀**:
  - 우측 상단의 `← 사용자 채팅 포털` 버튼을 통해 언제든지 에이전트 대화 화면으로 돌아갈 수 있습니다.

---

### 4-4. 관리자 콘솔 - 신규 사용자 등록 모달 (New User Registration Modal)

관리자 콘솔에서 `+ 신규 사용자 등록` 버튼을 클릭하면 새로운 사용자를 안전하게 프로비저닝할 수 있는 모달 팝업이 노출됩니다.

<div align="center">
  <img src="images/screenshot_admin_modal.png" alt="New User Registration Modal" width="850" />
</div>

- **직관적인 모달 입력 폼**:
  - **아이디**: 새 사용자의 고유 로그인 ID
  - **이메일**: 계정 안내 및 인증용 이메일
  - **권한 (ROLE)**: 드롭다운을 통해 `User (일반 에이전트 사용자)` 또는 `Admin (시스템 관리자)` 권한 지정
- **비동기 DB 즉각 저장**:
  - `생성` 버튼 클릭 시 백엔드 `SQLModel` ORM을 통해 PostgreSQL 16 비동기 데이터베이스에 즉시 생성되며, 관리자 콘솔 테이블에 새로고침 없이 즉각 반영됩니다.

---

## 🚀 다음 단계 (Next Steps)

- **도구(Tool) 및 지식 베이스 연동**: `backend/src/infrastructure/`에 고유 비즈니스 로직 및 외부 API Tool을 추가해보세요.
- **LLM 관측성 분석**: [http://localhost:3000](http://localhost:3000) (Langfuse)에 접속하여 사용자 대화 및 에이전트의 세부 실행 트레이스를 모니터링해보세요.
- **프로덕션 컨테이너 빌드 & 배포**: `af build` 및 `af deploy`를 통해 Kubernetes 클러스터에 원클릭 배포할 수 있습니다.
- **전체 프레임워크 아키텍처 상세**: [메인 README.md](../README.md)를 참조하세요.
