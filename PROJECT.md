# Project: AgentForge Framework

## Architecture
AgentForge is an enterprise-grade agent framework and scaffolding engine delivering standalone, zero-bloat, fullstack agent projects.
- **Decoupled Standalone Runtime**: The Core Runtime Engine (`agentforge/core/`) is 100% copied into generated projects (`backend/src/core/`) and executes with zero external runtime dependencies on the generator repository.
- **Clean Architecture Backend**: Decoupled 5-layer domain-driven architecture (`domain/`, `application/`, `infrastructure/`, `rest/`, `core/`) with enterprise multi-protocol authentication (ID/PW, LDAP, SAML 2.0), Redis token blacklist & sliding-window rate limiting, async SQLModel persistence, and normalized framework adapters.
- **Multi-Portal Frontend**: Unified Vite multi-page application with separate entrypoints for User Chat Portal (`index.html` / `App.jsx`) and Admin Management Portal (`admin.html` / `AdminApp.jsx`), real-time SSE streaming, HITL interrupt approval, offline `lucide-react` icons, and dual-routing Nginx container.
- **Zero-Bloat Infra**: Lightweight 4-service `docker-compose.yml` (Postgres 16, Redis 7, Backend, Frontend) and environment-separated Kubernetes manifests (`dev`, `prd`) with automated rollout verification (`k8s-deploy.sh`).
- **Unified CLI & Scaffolding Engine**: Global Typer CLI (`agentforge`, `af`) supporting lifecycle commands (`new`, `dev`, `build`, `deploy`), template parameter injection, and post-scaffold syntax validation.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | `BaseAgentAdapter` Interface | Protocol defining standard methods: `ainvoke`, `astream`, `ahandle_interrupt` | M1 | Survey 1, R1 |
| 2 | Concrete Framework Adapters | Implementations for 5+ frameworks: LangChain, LlamaIndex, Google GenAI, CrewAI, AutoGen, LangGraph, DeepAgent, Bedrock | M1 | Survey 1, R1 |
| 3 | Normalized Chunk Events | `AgentChunk`, `AgentEventType` (`token`, `meta`, `evidence`, `interrupt`, `error`, `done`) | M1 | Survey 1, R1 |
| 4 | `SSETokenStreamer` | Fast async generator to SSE chunk serializer with anti-buffering headers | M1 | Survey 1, R1 |
| 5 | `RuntimeContext` & Semaphores | Concurrency governance, request cancellation detection, correlation IDs | M1 | Survey 1, R1 |
| 6 | `Database` Singleton | Double-checked locking thread-safe connection pool manager | M1 | Survey 1, R1 |
| 7 | Sync/Async Session Makers | `get_sync_session`, `get_async_session` with automatic rollback & cleanup | M1 | Survey 1, R1 |
| 8 | Pagination Helper | `Page`, `PageableParams`, `PageMetadata` (limit/offset, page/size) | M1 | Survey 1, R1 |
| 9 | Structured JSON Logger | `setup_logger`, `JsonFormatter` with correlation ID and ISO timestamp | M1 | Survey 1, R1 |
| 10 | Pydantic Configuration | `BaseAppSettings` via `pydantic-settings` with env loading and defaults | M1 | Survey 1, R1 |
| 11 | Scaffolding Copier | Standalone copier copying core engine into `backend/src/core/` | M2 | Survey 1, R3 |
| 12 | CLI Main Dispatcher | Typer app in `agentforge/cli/main.py` with global options and subcommands | M2 | Survey 1, R3 |
| 13 | CLI `agentforge new` | Scaffolding command with interactive prompt + non-interactive CLI flags | M2 | Survey 1, R3 |
| 14 | CLI `agentforge dev` | Concurrent backend + frontend development server runner | M2 | Survey 1, R3 |
| 15 | CLI `agentforge build` | Multi-stage Docker container build runner for backend & frontend | M2 | Survey 1, R3 |
| 16 | CLI `agentforge deploy` | Kubernetes deployment runner invoking `k8s-deploy.sh` | M2 | Survey 1, R3 |
| 17 | Scaffolding Engine | Template parameter substitution engine (project name, framework, auth, db) | M2 | Survey 1, R3 |
| 18 | Scaffolding Validator | Directory integrity and `compileall` syntax validation post-scaffold | M2 | Survey 1, R3 |
| 19 | Dual CLI Entrypoints | `agentforge` and `af` entrypoints declared in `pyproject.toml` | M2 | Survey 1, R3 |
| 20 | Packaging & README Update | Root `pyproject.toml` dependencies and user documentation | M2 | Survey 1, R3 |
| 21 | Clean Architecture Layout | 5-layer hierarchy (`domain`, `application`, `infrastructure`, `rest`, `core`) | M3 | Survey 2, R2 |
| 22 | Domain Models & Ports | User, AuthSession, ChatRoom, ChatMessage, ChatInterrupt entities & ports | M3 | Survey 2, R2 |
| 23 | ID/PW Authentication | Bcrypt password hashing + JWT access/refresh token rotation | M3 | Survey 2, R2 |
| 24 | LDAP Authentication | `ldap3` Active Directory bind, user search, and group-to-role mapping | M3 | Survey 2, R2 |
| 25 | SAML 2.0 Authentication | `pysaml2` SP metadata generation and ACS XML assertion verification | M3 | Survey 2, R2 |
| 26 | Redis Session Blacklist | Token revocation blacklist (`blacklist:{jti}`) and session store | M3 | Survey 2, R2 |
| 27 | Redis Sliding-Window Rate Limiter | Atomic Redis Lua script rate limiter protecting endpoints | M3 | Survey 2, R2 |
| 28 | Async SQLModel Persistence | Asyncpg engine, connection pooling, SQLModel tables | M3 | Survey 2, R2 |
| 29 | Alembic Async Migrations | Async Alembic migrations setup (`env.py`, initial migration script) | M3 | Survey 2, R2 |
| 30 | Backend Framework Adapters | Adapt core framework adapters into `ChatService` and `/api/v1/chats` | M3 | Survey 2, R2 |
| 31 | Lifespan Bootstrap | Application lifespan manager, DB init, Redis pool, shutdown cleanup | M3 | Survey 2, R2 |
| 32 | Backend Packaging & Docker | uv `pyproject.toml` and production multi-stage non-root `Dockerfile` | M3 | Survey 2, R2 |
| 33 | Multi-Entrypoint Vite Config | Single `vite.config.js` building `index.html` (chat) and `admin.html` (admin) | M4 | Survey 3, R2 |
| 34 | User Chat Portal (`App.jsx`) | Real-time SSE streaming chat UI with markdown rendering and history | M4 | Survey 3, R2 |
| 35 | Markdown & Code Rendering | `react-markdown` + `remark-gfm` with syntax highlighted code blocks | M4 | Survey 3, R2 |
| 36 | HITL `InterruptApprovalCard` | Interactive approval card for human-in-the-loop agent pauses | M4 | Survey 3, R2 |
| 37 | Admin Portal (`AdminApp.jsx`) | Dedicated management application entrypoint and routing | M4 | Survey 3, R2 |
| 38 | `AccountManagementPanel` | User CRUD, role filtering, search debounce, audit reason modal | M4 | Survey 3, R2 |
| 39 | `TerminalConsole` | Real-time agent execution terminal with log streaming and command feed | M4 | Survey 3, R2 |
| 40 | Unified Auth UI | `AuthProvider`, `LoginForm` (ID/PW, LDAP tabs, SAML button), password reset | M4 | Survey 3, R2 |
| 41 | Offline UI Stack | Tailwind CSS + `lucide-react` self-contained vector icons (zero CDN) | M4 | Survey 3, R2 |
| 42 | Frontend Multi-Stage Dockerfile | Production Nginx container with dual SPA routing (`/` and `/admin`) | M4 | Survey 3, R2 |
| 43 | Zero-Bloat `docker-compose.yml` | 4-service stack: Postgres 16, Redis 7, Backend, Frontend with health checks | M5 | Survey 3, R2 |
| 44 | Kubernetes Manifests (`dev`/`prd`) | Deployments, Services, ConfigMaps, Secrets, Ingress, securityContext | M5 | Survey 3, R2 |
| 45 | `k8s-deploy.sh` Script | Rollout script with preflight validation, checksum annotations, rollout wait | M5 | Survey 3, R2 |
| 46 | Scaffolding Integration Test | Full execution test: `agentforge new test-agent` with compile validation | M6 | Survey 1-3, R4 |
| 47 | Core & CLI Unit Tests | Comprehensive pytest test suite in `tests/test_core.py`, `test_cli.py`, `test_generator.py` | M6 | Survey 1-3, R4 |
| 48 | Full E2E Test Suite & Adversarial Hardening | Verification against 100% of Tiers 1-4 E2E tests + Tier 5 coverage audit | M6 | Survey 1-3, R4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Core Runtime Engine | `agentforge/core/`: adapter.py, streaming.py, database.py, logging.py, config.py, __init__.py | none | PLANNED |
| M2 | CLI & Generator Engine | `agentforge/cli/`, `agentforge/generator/`, root `pyproject.toml`, `README.md` | M1 | PLANNED |
| M3 | Clean Architecture Backend Template | `agentforge/templates/backend/`: domain, application, infrastructure, rest, bootstrap, alembic, Dockerfile, pyproject.toml | M1 | PLANNED |
| M4 | Frontend React-Vite Multi-Portal Template | `agentforge/templates/frontend/react-vite/`: multi-entrypoint Vite, user portal, admin portal, auth, chat, Dockerfile | none | PLANNED |
| M5 | Infra & Kubernetes Templates | `agentforge/templates/infra/`, `agentforge/templates/k8s/`: docker-compose.yml, k8s dev/prd manifests, k8s-deploy.sh | M3, M4 | PLANNED |
| M6 | Integration Verification & E2E Acceptance | Full scaffolding execution test, unit test suite (`tests/`), 100% E2E test suite pass & Tier 5 adversarial hardening | M1, M2, M3, M4, M5, E2E Track | PLANNED |

## Interface Contracts
### `agentforge.core.adapter` ↔ Backend Application Use Cases
- `BaseAgentAdapter`:
  - `async def ainvoke(input_data: AgentInput) -> AgentOutput`
  - `async def astream(input_data: AgentInput) -> AsyncGenerator[AgentChunk, None]`
  - `async def ahandle_interrupt(interrupt_id: str, decision: str, state_update: dict | None = None) -> AgentOutput | AsyncGenerator[AgentChunk, None]`
- `AgentChunk`: `event: AgentEventType` (`token`, `evidence`, `meta`, `interrupt`, `error`, `done`), `data: dict | str`, `timestamp: str`, `id: str | None`.

### `agentforge.core.streaming` ↔ Backend Presentation Routes
- `SSETokenStreamer`:
  - `async def sse_event_generator(source: AsyncGenerator[AgentChunk, None]) -> AsyncGenerator[str, None]`
  - Formats chunks as `event: {event_type}\ndata: {json_payload}\n\n`
  - Sets HTTP headers: `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`, `Connection: keep-alive`.
- `RuntimeContext`:
  - Context manager tracking `correlation_id`, `client_disconnected: asyncio.Event`, `concurrency_semaphore: asyncio.Semaphore`.

### `agentforge.core.database` ↔ Backend Infrastructure Repositories
- `Database`: Thread-safe singleton with `get_async_session() -> AsyncGenerator[AsyncSession, None]` and `get_sync_session() -> Generator[Session, None]`.
- `apply_pageable_params(query, params: PageableParams) -> query`
- `Page[T]`: `items: list[T]`, `metadata: PageMetadata(page, size, total_elements, total_pages)`.

### Frontend ↔ Backend API Contracts
- `POST /api/v1/auth/login`: Accepts `LoginRequest(username, password, auth_type: id_pw | ldap | saml)`, returns `TokenResponse(access_token, refresh_token, token_type, expires_in)`.
- `POST /api/v1/chats/stream`: Accepts `ChatStreamRequest(chat_id, message, session_id)`, returns `text/event-stream`.
- `POST /api/v1/chats/interrupts/{interrupt_id}/resolve`: Accepts `InterruptResolveRequest(decision: approve | reject, comment: str | None)`.
- `GET /api/v1/admin/users`: Accepts `page`, `size`, `role`, `status`, `search`, returns `Page[UserResponse]`.
- `GET /healthz`: Returns `{"status": "ok", "version": str, "database": "up", "redis": "up"}`.

## Code Layout
```
AgentForge/
├── agentforge/
│   ├── __init__.py
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── new.py
│   │   ├── dev.py
│   │   ├── build.py
│   │   └── deploy.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── adapter.py
│   │   ├── streaming.py
│   │   ├── database.py
│   │   ├── logging.py
│   │   └── config.py
│   ├── generator/
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── copier.py
│   │   └── validator.py
│   └── templates/
│       ├── backend/
│       │   ├── alembic/
│       │   ├── src/
│       │   │   ├── core/           # Copied standalone core
│       │   │   ├── domain/
│       │   │   ├── application/
│       │   │   ├── infrastructure/
│       │   │   ├── rest/
│       │   │   ├── frameworks/
│       │   │   ├── bootstrap.py
│       │   │   └── main.py
│       │   ├── pyproject.toml
│       │   └── Dockerfile
│       ├── frontend/
│       │   └── react-vite/
│       │       ├── index.html
│       │       ├── admin.html
│       │       ├── vite.config.js
│       │       ├── tailwind.config.js
│       │       ├── package.json
│       │       ├── Dockerfile
│       │       └── src/
│       ├── infra/
│       │   └── docker-compose.yml
│       └── k8s/
│           ├── dev/
│           ├── prd/
│           └── k8s-deploy.sh
├── tests/
│   ├── __init__.py
│   ├── test_core.py
│   ├── test_cli.py
│   └── test_generator.py
├── pyproject.toml
└── README.md
```
