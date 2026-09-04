# AgentForge ⚡

> **Fast, Standalone & Production-Ready AI Agent Framework**  
> 빠른 AI 에이전트 개발을 위해 프론트엔드, 백엔드, Kubernetes 배포까지 풀스택 독립형 아키텍처를 자동 생성하는 오픈소스 프레임워크입니다.

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Architecture](https://img.shields.io/badge/Architecture-Fullstack%20Monorepo-green.svg)](#-생성되는-프로젝트-구조)
[![Frameworks](https://img.shields.io/badge/Supported%20Frameworks-LangChain%20%7C%20LangGraph%20%7C%20DeepAgent%20%7C%20ADK%20%7C%20Bedrock-orange.svg)](#-지원-에이전트-프레임워크-5종)

---

## 🌟 개요 (Overview)

**AgentForge**는 기존 [FastLangFrame](https://github.com/bulgemi/FastLangFrame)의 설계 철학을 계승하고, 실제 현업 및 프로덕션 환경에서의 한계점을 혁신적으로 개선한 차세대 AI 에이전트 스캐폴딩 & 런타임 프레임워크입니다.

### 💡 FastLangFrame 대비 무엇이 달라졌나요?

| 구분 | 기존 FastLangFrame | ✨ **AgentForge** |
| :--- | :--- | :--- |
| **프로젝트 생성 위치** | 프레임워크 내부 `projects/` 고정 | **사용자가 원하는 로컬 임의 경로(`--path`) 자유 지정** |
| **코어 코드 의존성** | 중앙 코어 모듈을 참조(`import`)하는 종속형 구조 | **Core 엔진을 생성 프로젝트에 복사하여 100% 독립 실행(Standalone)** |
| **에이전트 프레임워크** | LangChain / LangGraph 중심 | **LangChain, LangGraph, DeepAgent, ADK, AWS Bedrock 5종 전폭 지원** |
| **인프라 의존성 (Bloat)** | Authelia, Nginx, Redis, DB 등 기본 탑재 (무거움) | **초경량 최소화 (Zero Bloat): 불필요한 외부 의존성 제거, 즉시 실행** |
| **스택 범위** | 백엔드 API + 일부 테스트 UI 위주 | **Frontend (React+Vite / Streamlit) + Backend (FastAPI) + K8s 매니페스트 풀스택 생성** |
| **템플릿 시스템** | 레거시 복잡 템플릿 | **현대적 코드베이스 기반 신규 클린 템플릿 전면 재작성** |
| **CLI 생태계** | 저장소 스크립트(`bin/lapm`) 실행 방식 | **독립 설치형 글로벌 CLI (`agentforge`, `af`) 풀 라이프사이클 지원** |

---

## 🏗️ 아키텍처 (Architecture)

AgentForge로 생성된 프로젝트는 [pay](https://github.com/Seorin25F/pay) 저장소의 검증된 실전 아키텍처를 계승하여 **풀스택 모노레포(Clean Architecture)** 형태로 구성되며, 각 티어가 느슨하게 결합되어 독립적으로 실행·배포될 수 있습니다.

```mermaid
graph TB
    %% Client Layer
    subgraph Client["Frontend Layer (선택형 웹 클라이언트)"]
        subgraph ReactApp["Vite + React SPA"]
            UI_Comp["React Components<br/>(Chat Box, Streaming Bubble, Tools Status)"]
            UI_API["API Client (src/api)<br/>(fetch /invoke & EventSource /stream)"]
            UI_Docker["Nginx Reverse Proxy & Security<br/>(docker/default.conf)"]
            UI_Comp --> UI_API
            UI_API -.-> UI_Docker
        end
        UI_Streamlit["Streamlit Dashboard<br/>(Rapid Prototype UI)"]
    end

    %% Backend Layer
    subgraph BackendGateway["Backend Layer (FastAPI Clean Architecture)"]
        direction TB
        MainAPI["FastAPI Entrypoint (src/main.py & src/bootstrap.py)<br/>- POST /invoke (Blocking)<br/>- POST /stream (SSE Streaming)<br/>- GET /health (Healthcheck)"]

        subgraph CoreEngine["Standalone Core Engine (src/core/) - 복사형 독립 런타임"]
            Streaming["SSE Token Streamer<br/>(Async Chunk Generator)"]
            RuntimeCtx["Runtime Context<br/>(Concurrency & Semaphore)"]
            AdapterBase["BaseAgentAdapter<br/>(표준 에이전트 추상화 인터페이스)"]
        end

        subgraph CleanArch["Clean Architecture Layers (src/)"]
            direction TB
            AppLayer["Application Layer (src/application/)<br/>- Agent Orchestration Services<br/>- DTOs & Use Cases"]
            DomainLayer["Domain Layer (src/domain/)<br/>- Business Entities & States<br/>- Agent / Repository Interfaces"]
            InfraLayer["Infrastructure Layer (src/infrastructure/)<br/>- LLM Provider Connectors<br/>- Framework Adapters Implementation<br/>- External APIs & DB Storage"]
            
            AppLayer --> DomainLayer
            AppLayer --> InfraLayer
            InfraLayer -.-> DomainLayer
        end

        MainAPI --> CoreEngine
        MainAPI --> AppLayer
        InfraLayer --> AdapterBase
    end

    %% Frameworks
    subgraph Frameworks["선택된 에이전트 프레임워크 (5종 지원)"]
        FW_LC["1. LangChain (LCEL / Chains)"]
        FW_LG["2. LangGraph (StateGraph / Multi-Turn)"]
        FW_DA["3. DeepAgent (Deep Reasoning / Planning)"]
        FW_ADK["4. ADK (Agent Development Kit)"]
        FW_BR["5. AWS Bedrock (Bedrock Agent / Knowledge Base)"]
    end

    %% Deployment Layer
    subgraph Deployment["Deployment & DevOps Layer (pay k8s 구조 계승)"]
        Compose["Local Dev (docker-compose.yml)"]
        DeployScript["k8s-deploy.sh (통합 배포 자동화)"]
        
        subgraph K8sEnvs["Kubernetes Environments"]
            K8sDev["k8s/dev/ (개발 환경)<br/>- backend / frontend Deployments<br/>- ConfigMap & Secret-External"]
            K8sPrd["k8s/prd/ (운영 환경)<br/>- HA Deployment & Resource Limit<br/>- Ingress & Security Context"]
        end
        
        DeployScript --> K8sDev
        DeployScript --> K8sPrd
    end

    %% Connections
    UI_API -->|HTTP REST /invoke| MainAPI
    UI_API -->|SSE /stream (Token Streaming)| MainAPI
    UI_Streamlit -->|HTTP / SSE| MainAPI

    AdapterBase ===> FW_LC
    AdapterBase ===> FW_LG
    AdapterBase ===> FW_DA
    AdapterBase ===> FW_ADK
    AdapterBase ===> FW_BR

    BackendGateway -.-> Compose
    ReactApp -.-> Compose
    BackendGateway -.-> Deployment
    ReactApp -.-> Deployment
```

---

## 🤖 지원 에이전트 프레임워크 5종

AgentForge는 백엔드 표준 어댑터(`BaseAgentAdapter`) 패턴을 내장하여, 어떤 프레임워크를 선택하더라도 클라이언트와 표준화된 규격으로 통신합니다.

| 프레임워크 | 설명 | 특징 및 추천 활용처 | 공식 링크 |
| :--- | :--- | :--- | :--- |
| **1. LangChain** | 엔드투엔드 LLM 체인 구성의 표준 | 전통적인 프롬프트 체이닝, 간단한 Tool Calling 에이전트 | [공식 문서](https://www.langchain.com/) |
| **2. LangGraph** | 순환형(Cyclic) 그래프 및 분기 상태 제어 | 정교한 Multi-Turn 대화, Human-in-the-loop, 다중 에이전트 제어 | [공식 문서](https://www.langchain.com/langgraph) |
| **3. DeepAgent** | 심층 추론(Deep Reasoning) 및 계획 수립 에이전트 | 단계별 사고 과정(Thinking), 연구 및 복합 문제 분석 특화 | [공식 문서](https://docs.langchain.com/oss/python/deepagents/overview) |
| **4. ADK (Agent Development Kit)** | 모듈식 경량 에이전트 개발 키트 | 표준 도구 및 컴포넌트 조합형 엔지니어링 에이전트 | [공식 문서](https://adk.dev/) |
| **5. AWS Bedrock** | AWS 네이티브 완전관리형 AI 에이전트 | 엔터프라이즈 AWS 보안/규정 준수, Bedrock Agents 및 Knowledge Base 연동 | [공식 문서](https://aws.amazon.com/ko/bedrock/) |

> 📌 **표준 API 보장**: 모든 프레임워크 어댑터는 동일한 엔드포인트를 제공합니다.
> - `POST /invoke` : 단일 프롬프트 동기 블로킹 호출
> - `POST /stream` : 실시간 토큰 및 이벤트 스트리밍 (Server-Sent Events, SSE)
> - `GET /health` : 서비스 상태 및 에이전트 로딩 헬스체크

---

## 📁 생성되는 프로젝트 구조

`agentforge new` 명령으로 생성된 프로젝트는 [pay](https://github.com/Seorin25F/pay) 저장소의 실전 Clean Architecture 모노레포 구조를 기반으로 하며, 외부 프레임워크 저장소에 전혀 의존하지 않는 완전한 독립형(Standalone) 프로젝트입니다.

```text
my-awesome-agent/
├── backend/                       # FastAPI 기반 백엔드 (Clean Architecture 계층 구조)
│   ├── src/                       # 백엔드 핵심 소스
│   │   ├── core/                  # 복사된 독립형 Standalone Core 엔진
│   │   │   ├── adapter.py         # 표준 BaseAgentAdapter 인터페이스
│   │   │   ├── config.py          # Pydantic Settings 환경 설정
│   │   │   ├── logging.py         # 구조화 로깅
│   │   │   └── streaming.py       # 실시간 SSE 스트리머 & 동시성 세마포어
│   │   ├── domain/                # 비즈니스 도메인 모델, Entity, 인터페이스 규격
│   │   ├── application/           # 에이전트 서비스, 유스케이스 오케스트레이션, DTO
│   │   ├── infrastructure/        # 선택된 에이전트 프레임워크(LangGraph/Bedrock 등) 연동, 외부 API
│   │   ├── common/                # 공통 에러 핸들링, 미들웨어, 유틸 상수
│   │   ├── utils/                 # 도구 커넥터 및 헬퍼 유틸리티
│   │   ├── main.py                # FastAPI 웹 애플리케이션 진입점
│   │   └── bootstrap.py           # 서비스 컨테이너 초기화 및 런타임 바인딩
│   ├── alembic/                   # 데이터베이스 마이그레이션 버전 관리
│   ├── alembic.ini
│   ├── tests/                     # 백엔드 단위/통합 테스트 스위트
│   ├── Dockerfile                 # 백엔드 프로덕션 멀티스테이지 Dockerfile
│   ├── pyproject.toml             # uv / pyproject 기반 의존성 정의
│   └── uv.lock                    # 초고속 uv 패키지 락파일
│
├── frontend/                      # Vite + React 기반 모던 웹 프론트엔드 (Streamlit 선택 가능)
│   ├── src/                       # 프론트엔드 React 소스
│   │   ├── api/                   # 백엔드 (/invoke, /stream SSE) 통신 API 클라이언트
│   │   ├── components/            # 채팅 인터페이스, 메시지 카드, 상태 뱃지 등 UI 컴포넌트
│   │   ├── pages/                 # 메인 화면 및 에이전트 대시보드 뷰
│   │   ├── hooks/                 # 실시간 스트리밍 훅 및 상태 관리 훅
│   │   ├── store/                 # 전역 상태 관리 (Zustand 등)
│   │   ├── utils/                 # 공통 도우미 함수
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── docker/                    # 프론트엔드 컨테이너 빌드 & Nginx 웹서버 설정
│   │   ├── Dockerfile             # Vite 빌드 결과물 서빙 경량 Nginx 컨테이너
│   │   ├── default.conf           # SPA 라우팅 대응 Nginx 설정
│   │   └── nginx-security.conf    # 보안 헤더 설정
│   ├── package.json
│   ├── vite.config.js             # Vite 번들러 설정
│   └── tailwind.config.js         # Tailwind CSS 스타일링 설정
│
├── k8s/                           # 환경 분리형 Kubernetes 실전 배포 매니페스트
│   ├── dev/                       # 개발(Dev) 환경 매니페스트
│   │   ├── backend/               # 백엔드 Deployment & Service
│   │   ├── frontend/              # 프론트엔드 Deployment & Service
│   │   ├── configmap.yaml         # 개발 환경 변수 ConfigMap
│   │   ├── secret-external.yaml   # API Key 등 시크릿 템플릿
│   │   ├── namespace.yaml
│   │   └── serviceaccount.yaml
│   ├── prd/                       # 운영(Prod) 환경 매니페스트 (고가용성 & 리소스 튜닝)
│   │   ├── backend/
│   │   ├── frontend/
│   │   ├── configmap.yaml
│   │   ├── secret-external.yaml
│   │   ├── namespace.yaml
│   │   └── serviceaccount.yaml
│   └── k8s-deploy.sh              # 환경별 원클릭 클러스터 배포 쉘 스크립트
│
├── docs/                          # 프로젝트 아키텍처, API 스펙, 개발 가이드 문서
├── docker-compose.yml             # 로컬 통합 개발 환경 원클릭 실행 (Frontend + Backend)
├── .env.sample                    # 환경 변수 샘플 파일
└── README.md                      # 프로젝트 전용 안내 문서

---

## 🚀 빠른 시작 (Quick Start)

### 1. AgentForge CLI 설치

```bash
# pip를 통한 설치
pip install agentforge

# 또는 uv / pipx를 통한 초고속 설치
uv tool install agentforge
```

### 2. 새 프로젝트 생성 (`agentforge new`)

원하는 위치에 프로젝트 이름, 사용할 에이전트 프레임워크, 프론트엔드 유형을 지정하여 생성합니다.

```bash
# 기본 사용법
agentforge new <프로젝트명> --framework <프레임워크> --frontend <프론트엔드> --path <경로>

# 예시 1: LangGraph + React(Vite) 조합으로 현재 디렉토리에 생성
agentforge new customer-agent --framework langgraph --frontend react --path .

# 예시 2: AWS Bedrock + Streamlit 조합으로 특정 디렉토리에 생성
agentforge new enterprise-bot --framework bedrock --frontend streamlit --path /data/projects

# 대화형 모드 (옵션을 지정하지 않으면 인터랙티브 마법사 실행)
agentforge init
```

#### 옵션 플래그 상세

| 옵션 | 단축형 | 설명 | 선택값 |
| :--- | :--- | :--- | :--- |
| `--framework` | `-f` | 에이전트 개발 프레임워크 | `langchain`, `langgraph`, `deepagent`, `adk`, `bedrock` |
| `--frontend` | `-ui` | 프론트엔드 인터페이스 | `react` (Vite + Tailwind), `streamlit`, `none` (headless 백엔드) |
| `--path` | `-p` | 프로젝트가 생성될 디렉토리 경로 | 기본값: 현재 작업 디렉토리 (`.`) |

---

## 💻 CLI 도구 명령어 (`agentforge` / `af`)

AgentForge CLI는 프로젝트 스캐폴딩부터 로컬 테스트, 빌드, 배포까지 전 주기(Full Lifecycle)를 지원합니다.

### 1) 로컬 개발 서버 실행 (`dev`)
백엔드(FastAPI)와 프론트엔드(Vite React / Streamlit)를 한 번에 실행합니다.
```bash
cd <프로젝트디렉토리>
agentforge dev
# Backend: http://localhost:8000 (API Docs: http://localhost:8000/docs)
# Frontend: http://localhost:5173 (React/Vite) 또는 http://localhost:8501 (Streamlit)
```

### 2) Docker 이미지 빌드 (`build`)
배포를 위한 프로덕션 컨테이너 이미지를 빌드합니다.
```bash
agentforge build --tag v1.0.0
# backend:v1.0.0 및 frontend:v1.0.0 이미지 생성
```

### 3) Kubernetes 클러스터 배포 (`deploy`)
`k8s/` 매니페스트를 타겟 클러스터에 배포합니다.
```bash
agentforge deploy --namespace ai-agents
```

---

## 🛠️ 개발 및 기여 가이드 (Contributing)

AgentForge는 오픈소스 프로젝트로서 커뮤니티의 기여를 적극 환영합니다.

```bash
# 1. 저장소 클론
git clone https://github.com/bulgemi/AgentForge.git
cd AgentForge

# 2. 개발 환경 설정
poetry install  # 또는 pip install -e ".[dev]"

# 3. 테스트 실행
pytest
```

새로운 에이전트 프레임워크 어댑터 추가, 프론트엔드 템플릿 개선, K8s 매니페스트 최적화 등 다양한 기여를 기다립니다. 이슈와 PR을 편하게 남겨주세요!

---

## 📄 라이선스 (License)

이 프로젝트는 [MIT License](LICENSE)에 따라 배포됩니다.
