<div align="center">
  <img src="assets/agentforge_icon.png" alt="AgentForge Logo" width="160" />

  # AgentForge ⚡

  > **Fast, Standalone & Production-Ready AI Agent Framework**  
  > 프론트엔드, 백엔드, 로컬 인프라부터 Kubernetes 배포까지 단 한 줄로 완성하는 엔터프라이즈 풀스택 에이전트 프레임워크

  [![Python Version](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue.svg)](https://www.python.org/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
  [![Documentation Hub](https://img.shields.io/badge/Docs-Documentation%20Hub-blue.svg)#-공식-문서-가이드-허브-documentation-hub)
  [![AI Harness](https://img.shields.io/badge/AI%20Harness-.agents%2Fskills-orange.svg)](docs/skills.md)
  [![Spec-Driven UI](https://img.shields.io/badge/UI%2FUX-Spec--Driven%20(DESIGN.md)-blueviolet.svg)](docs/architecture.md#3-스펙-기반-ui-개발--ai-에이전트-협업-체계-frontenddesignmd)
  [![Quickstart](https://img.shields.io/badge/Quickstart-3--Min%20Guide-FF5722.svg)](docs/quickstart.md)
</div>

---

### ⚡ 10초 퀵 스타트 (Quick Start)

```bash
# 1. AgentForge CLI 도구 설치 (uv 또는 pip)
uv tool install agentforge     # 또는 pip install agentforge

# 2. 독립형 풀스택 에이전트 프로젝트 생성 (원하는 프레임워크 선택)
af new my-agent --framework langgraph --frontend react

# 3. 생성된 디렉토리로 이동 후 원클릭 실행 (인프라 & 앱 동시 기동)
cd my-agent && ./run.sh        # Windows: run.bat
```
> 🌐 **기동 후 브라우저 접속**: [http://localhost:5173](http://localhost:5173) (기본 관리자 로그인: `admin` / `admin1234!`)

---

## 🌟 왜 AgentForge인가요? (핵심 가치 제안)

기존 프레임워크의 한계를 극복하고 엔터프라이즈 현업의 요구사항을 반영하여 완전히 새로 설계되었습니다:

| 구분 | 기존 프레임워크 한계 | ✨ **AgentForge 핵심 혁신** | 사용자 이점 |
| :--- | :--- | :--- | :--- |
| **의존성 (Dependency)** | 중앙 코어를 import하는 종속형 | **Core 엔진 100% 독립 복사 (Standalone)** | 외부 패키지 설치 없이 독립 레포로 버전 관리 및 배포 가능 |
| **에이전트 유연성** | 특정 라이브러리 1종 고정 | **5대 프레임워크 표준 어댑터 패턴 내장** | LangChain, LangGraph, DeepAgent, ADK, Bedrock 자유 선택 |
| **AI 협업 통제** | AI의 임의 파일 수정 및 회귀 버그 | **`.agents/skills/` 8단계 표준 개발 하네스** | 분석 → 파일단위 설계 → 오버엔지니어링 검토 → 승인 게이트 → 구현 |
| **UI/UX 일관성** | 개발자마다 제각각인 스타일링 | **Spec-Driven UI (`frontend/DESIGN.md`)** | 디자인 토큰과 제약 규칙을 AI의 Single Source of Truth로 연동 |
| **인프라 부하** | 모든 무거운 컨테이너 강제 기동 | **Docker Compose 6개 프로파일 선택 구동** | 불필요한 리소스 낭비 없이 필요한 스택(`infra`, `search` 등)만 실행 |

---

## 📚 공식 문서 가이드 허브 (Documentation Hub)

AgentForge의 세부 아키텍처와 운영 매뉴얼은 목적별 전문 서브 문서에서 자세히 다룹니다:

| 가이드 문서 | 주요 내용 | 추천 대상 |
| :--- | :--- | :--- |
| [**⚡ 3분 사용자 퀵스타트**](docs/quickstart.md) | 프로젝트 생성부터 로그인, 대화 화면 및 관리자 콘솔 UI 둘러보기 | AgentForge를 처음 시작하는 모든 사용자 |
| [**⚙️ CLI & 스캐폴딩 완전 가이드**](docs/cli.md) | `af new`, `dev`, `build`, `deploy` 옵션, Python API, 5단계 합성 엔진 | CLI 파라미터 및 자동화 파이프라인 구축자 |
| [**🏗️ 아키텍처 & 프레임워크 가이드**](docs/architecture.md) | Clean Architecture 모노레포, 에이전트 5종 어댑터, Spec-Driven UI, 엔터프라이즈 기능 | 백엔드/프론트엔드 아키텍처를 깊이 이해하려는 개발자 |
| [**🛠️ AI 개발 하네스 (Skills) 가이드**](docs/skills.md) | `feature-development`, `feature-enhancement`, `bugfix`, 8단계 파이프라인, GitHub Issue/태그 | AI 코딩 도구(Cursor, Claude Code, Antigravity) 사용자 |
| [**🐳 로컬 인프라 & 배포 가이드**](docs/infrastructure.md) | Docker Compose 6개 프로파일, 서비스 스택, 대시보드 URL, K8s 클러스터 배포 | 로컬 인프라 제어 및 클라우드 배포 운영자 |
| [**🌱 환경 변수 & 거버넌스 가이드**](docs/env-vars.md) | 백엔드/프론트엔드 `.env` & `.env.sample` 전체 레퍼런스 및 보안 수칙 | 보안 설정 및 환경 변수 연동 엔지니어 |

---

## 🚀 핵심 기능 하이라이트 (Core Highlights)

### 1. 🤖 5대 에이전트 프레임워크 표준 연동 (`BaseAgentAdapter`)
- **지원 프레임워크**: LangGraph(기본), LangChain, DeepAgent, ADK, AWS Bedrock
- 어떤 프레임워크를 선택하더라도 동일한 REST API(`/invoke`, `/health`) 및 SSE 실시간 스트리밍(`/stream`) 표준 규격을 보장합니다.

### 2. 🎨 Spec-Driven UI Development (`frontend/DESIGN.md`)
- `frontend/DESIGN.md`에 브랜드 색상, 8pt 그리드 여백, 시맨틱 토큰, 품질 제약(Do's & Don'ts)을 명시합니다.
- AI 코딩 어시스턴트(Cursor, Claude Code, Windsurf)가 `DESIGN.md`를 단일 진실 공급원(SSOT)으로 삼아 완벽한 UI 일관성을 유지합니다.

### 3. 🛠️ `.agents/skills/` 8단계 표준 AI 개발 하네스
- **3개 특화 스킬**: `신규 기능(feature-development)`, `기능 개선(feature-enhancement)`, `버그 수정(bugfix)`
- **8단계 파이프라인**: `분석` → `파일 단위 설계([NEW]/[MODIFY])` → `오버엔지니어링 검토` → `★사용자 승인 게이트` → `GitHub Issue/태그 등록` → `구현` → `코드 리뷰` → `기능 점검(신규/회귀 테스트)` → `이슈 종료`

### 4. 🐳 멀티 프로파일 로컬 인프라 & K8s 배포
- **PostgreSQL 16** + **Redis 7.4** + **Langfuse v3** (ClickHouse + MinIO) + **OpenSearch 2.19.3**
- `--profile infra`, `--profile observability`, `--profile search`, `--profile all` 등 필요한 스택만 선택 가동할 수 있습니다.

---

## 📁 생성되는 프로젝트 기본 구조 (Project Layout)

`af new` 명령어로 생성되는 프로젝트는 의존성이 완벽히 격리된 독립형 모노레포 구조를 갖춥니다:

```text
my-awesome-agent/
├── .agents/skills/                # 🤖 기본 탑재 AI 개발 하네스 (feature, enhancement, bugfix)
├── run.sh / run.bat               # 원클릭 인프라 & 개발 서버 동시 실행 스크립트
├── backend/                       # FastAPI 백엔드 (Clean Architecture: domain, application, infra)
│   ├── src/core/                  # 100% 독립 복사된 Core 엔진 (adapter, streaming, database, config)
│   ├── .env & .env.sample         # 백엔드 활성 환경 변수 및 공개 템플릿
│   └── pyproject.toml             # uv / pyproject 기반 의존성 정의
├── frontend/                      # Vite + React 멀티 엔트리포인트 (사용자 채팅 포털 & 관리자 콘솔)
│   ├── DESIGN.md                  # 공식 UI/UX 디자인 시스템 & AI 코딩 에이전트 협업 규칙
│   └── .env & .env.sample         # 프론트엔드 환경 변수
├── docker-compose.yml             # 로컬 통합 인프라 (Postgres, Redis, Langfuse, OpenSearch)
├── k8s/                           # 환경 분리형 Kubernetes 실전 배포 매니페스트 (dev, prd, k8s-deploy.sh)
└── README.md                      # 프로젝트 전용 안내 문서
```

> 🏛️ 프레임워크 자체의 내부 엔진 저장소 구조는 [아키텍처 가이드](docs/architecture.md)에서 확인하실 수 있습니다.

---

## 🛠️ 개발 및 기여 가이드 (Contributing)

AgentForge는 오픈소스 프로젝트로서 커뮤니티의 기여를 적극 환영합니다.

```bash
# 1. 저장소 클론
git clone https://github.com/bulgemi/AgentForge.git
cd AgentForge

# 2. 개발 환경 설정
pip install -e ".[dev]"    # 또는 uv pip install -e ".[dev]"

# 3. 테스트 실행
pytest
```

새로운 에이전트 프레임워크 어댑터 추가, 프론트엔드 템플릿 개선, K8s 매니페스트 최적화 등 이슈와 PR을 자유롭게 남겨주세요!

---

## 📄 라이선스 (License)

이 프로젝트는 [MIT License](LICENSE)에 따라 배포됩니다.
