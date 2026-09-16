"""Scaffolding and template synthesis engine for AgentForge projects."""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Mapping

from .copier import copy_core_engine
from .validator import (
    validate_framework,
    validate_frontend,
    validate_generated_project,
    validate_project_name,
    validate_target_directory,
)

PACKAGE_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
PACKAGE_ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"


def to_snake_case(name: str) -> str:
    """Convert PascalCase, camelCase, or kebab-case string into lowercase snake_case."""
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
    s = s.replace("-", "_")
    s = re.sub(r'_+', '_', s)
    result = s.strip("_").lower()
    return result or "agentforge_app"


class ScaffoldingEngine:
    """Orchestrates creation of fullstack standalone agent projects."""

    def __init__(self, templates_dir: str | Path | None = None) -> None:
        self.templates_dir = Path(templates_dir or PACKAGE_TEMPLATES_DIR).resolve()

    def render_content(self, text: str, context: Mapping[str, Any]) -> str:
        """Simple, fast token replacement without requiring heavy template runtime."""
        rendered = text
        for key, value in context.items():
            # Support {{ key }}, {{key}}, {{  key  }} with arbitrary internal whitespace
            pattern = re.compile(r"\{\{\s*" + re.escape(key) + r"\s*\}\}")
            rendered = pattern.sub(str(value), rendered)
        return rendered

    def copy_template_tree(
        self,
        source_dir: Path,
        dest_dir: Path,
        context: Mapping[str, Any],
        exclude_exts: tuple[str, ...] = (".pyc", ".pyo"),
    ) -> None:
        """Recursively copy template directory tree, substituting variables in text files."""
        if not source_dir.exists():
            return

        dest_dir.mkdir(parents=True, exist_ok=True)
        text_extensions = (
            ".py",
            ".json",
            ".yaml",
            ".yml",
            ".md",
            ".toml",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".html",
            ".css",
            ".sh",
            ".bat",
            ".cmd",
            ".env",
            ".sample",
            ".ini",
            ".conf",
            ".txt",
            ".sql",
        )

        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if not d.startswith("__pycache__") and d != "node_modules"]
            rel_dir = Path(root).relative_to(source_dir)
            target_current_dir = dest_dir / rel_dir
            target_current_dir.mkdir(parents=True, exist_ok=True)

            for file_name in files:
                if any(file_name.endswith(ext) for ext in exclude_exts):
                    continue
                src_file = Path(root) / file_name
                dest_file = target_current_dir / file_name

                # Check if it is a text template that can be substituted
                is_text = any(file_name.endswith(ext) for ext in text_extensions) or file_name.startswith(".env")
                if is_text:
                    try:
                        content = src_file.read_text(encoding="utf-8")
                        rendered = self.render_content(content, context)
                        dest_file.write_text(rendered, encoding="utf-8")
                        # Preserve executable permissions for scripts
                        if (src_file.stat().st_mode & 0o111) or file_name.endswith(".sh"):
                            dest_file.chmod(dest_file.stat().st_mode | 0o755)
                        continue
                    except UnicodeDecodeError:
                        pass

                # Binary or non-text file copy
                shutil.copy2(src_file, dest_file)

    def generate(
        self,
        project_name: str,
        target_dir: str | Path,
        framework: str = "langgraph",
        frontend: str = "react-vite",
        force: bool = False,
    ) -> Path:
        """Generate a complete standalone project with backend, frontend, infra, and core.

        Args:
            project_name: Name of the project.
            target_dir: Directory where the project should be created.
            framework: Agent framework (e.g. langgraph, langchain, bedrock, etc.).
            frontend: Frontend framework (react-vite, streamlit, or none).
            force: Overwrite if directory exists.

        Returns:
            Path to the created project.
        """
        clean_name = validate_project_name(project_name)
        clean_framework = validate_framework(framework)
        clean_frontend = validate_frontend(frontend)
        dest_root = validate_target_directory(Path(target_dir) / clean_name, force=force)
        dest_root.mkdir(parents=True, exist_ok=True)

        context = {
            "project_name": clean_name,
            "project_name_snake": to_snake_case(clean_name),
            "framework": clean_framework,
            "frontend": clean_frontend,
            "python_version": "3.12",
        }

        # 1. Copy Backend Template
        backend_tpl = self.templates_dir / "backend"
        if backend_tpl.exists():
            self.copy_template_tree(backend_tpl, dest_root / "backend", context)

        # 2. Inject Selected Framework Adapter Template
        framework_tpl = self.templates_dir / "backend" / "src" / "frameworks" / clean_framework
        if framework_tpl.exists():
            dest_fw = dest_root / "backend" / "src" / "infrastructure" / "adapters" / "agent"
            dest_fw.mkdir(parents=True, exist_ok=True)
            self.copy_template_tree(framework_tpl, dest_fw, context)

        # 3. Copy Frontend Template
        if clean_frontend in ("react", "react-vite"):
            frontend_tpl = self.templates_dir / "frontend" / "react-vite"
            if frontend_tpl.exists():
                self.copy_template_tree(frontend_tpl, dest_root / "frontend", context)

            # Ensure branding assets (favicon, logos) from assets/ are synced to frontend/public
            if PACKAGE_ASSETS_DIR.exists():
                dest_public = dest_root / "frontend" / "public"
                dest_public.mkdir(parents=True, exist_ok=True)
                for asset_file in PACKAGE_ASSETS_DIR.iterdir():
                    if asset_file.is_file() and not asset_file.name.startswith("."):
                        shutil.copy2(asset_file, dest_public / asset_file.name)
        elif clean_frontend == "streamlit":
            streamlit_tpl = self.templates_dir / "frontend" / "streamlit"
            if streamlit_tpl.exists():
                self.copy_template_tree(streamlit_tpl, dest_root / "frontend", context)

        # 4. Copy Infrastructure & Kubernetes Templates
        infra_tpl = self.templates_dir / "infra"
        if infra_tpl.exists():
            # docker-compose.yml and postgres-init
            for item in infra_tpl.iterdir():
                if item.is_file():
                    content = item.read_text(encoding="utf-8")
                    (dest_root / item.name).write_text(self.render_content(content, context), encoding="utf-8")
                elif item.is_dir():
                    self.copy_template_tree(item, dest_root / item.name, context)

        k8s_tpl = self.templates_dir / "k8s"
        if k8s_tpl.exists():
            self.copy_template_tree(k8s_tpl, dest_root / "k8s", context)

        # 4.1 Copy Convenience Scripts (run.sh, run.bat, setup.sh, setup.bat)
        scripts_tpl = self.templates_dir / "scripts"
        if scripts_tpl.exists():
            for item in scripts_tpl.iterdir():
                if item.is_file():
                    content = item.read_text(encoding="utf-8")
                    dest_file = dest_root / item.name
                    dest_file.write_text(self.render_content(content, context), encoding="utf-8")
                    if item.name.endswith(".sh") or item.name == "af":
                        dest_file.chmod(dest_file.stat().st_mode | 0o755)

        # 5. Standalone Core Engine Copy
        dest_backend_src = dest_root / "backend" / "src"
        copy_core_engine(dest_backend_src, overwrite=True)

        # 6. Copy Root configuration files (.gitignore, AGENTS.md, CLAUDE.md, .cursorrules) and .agents
        root_tpl = self.templates_dir / "root"
        if root_tpl.exists():
            for item in root_tpl.iterdir():
                if item.is_file():
                    dest_file = dest_root / item.name
                    if not dest_file.exists():
                        content = item.read_text(encoding="utf-8")
                        dest_file.write_text(self.render_content(content, context), encoding="utf-8")
                elif item.is_dir() and item.name == ".agents":
                    self.copy_template_tree(item, dest_root / ".agents", context)

        # 6.1 Generate VS Code Launch and Settings configurations (.vscode/launch.json, settings.json)
        self._generate_vscode_configs(dest_root, clean_frontend)

        readme_path = dest_root / "README.md"
        if not readme_path.exists():
            readme_content = f"""# {clean_name} ⚡

[AgentForge](https://github.com/bulgemi/AgentForge) 기반으로 구축된 엔터프라이즈 풀스택 독립형 AI 에이전트 프로젝트입니다.

- **에이전트 프레임워크**: {clean_framework}
- **프론트엔드**: {clean_frontend}
- **아키텍처**: 풀스택 클린 아키텍처 (Clean Architecture Monorepo)
- **인증 및 보안**: ID/PW, LDAP, SAML 2.0 및 JWT 세션 관리
- **데이터베이스 & 캐시**: PostgreSQL 16 + Redis 7.4
- **LLM 관측성 (Observability)**: Langfuse v3 (ClickHouse + MinIO + Web + Worker)
- **검색 & 벡터 스토어**: OpenSearch 2.19.3 + OpenSearch Dashboards

---

## ⚡ 빠른 시작 (Quick Start)

### 1. 원클릭 로컬 실행 (One-Click Local Run, 권장)
가상환경 구성, Docker 인프라(Postgres, Redis, Langfuse, OpenSearch) 기동, 백엔드 및 프론트엔드 개발 서버를 단 한 번에 실행합니다:

```bash
# macOS / Linux
./run.sh

# Windows
run.bat
```

> **팁 (Tip)**: 서버를 띄우지 않고 의존성 패키지만 설치하려면 `./setup.sh` 또는 `setup.bat`를 실행하세요.

---

### 2. VS Code 원클릭 실행 및 디버깅 (F5 Launch & Debug)
VS Code에서 **F5** 키를 누르거나 **실행 및 디버그 (Run and Debug)** 뷰(`Ctrl+Shift+D` / `Cmd+Shift+D`)를 열면 바로 디버깅을 시작할 수 있습니다 (`.vscode/launch.json` 내장):
- **Fullstack: Backend + Frontend**: 백엔드(FastAPI uvicorn)와 프론트엔드 개발 서버를 동시에 기동합니다.
- **Backend: FastAPI (uvicorn)**: 중단점(Breakpoint)을 설정하고 백엔드 로직을 정밀 디버깅합니다.
- **Frontend: Vite Dev Server**: 프론트엔드 개발 서버를 기동하고 브라우저를 자동 실행합니다.

---

### 3. Docker Compose 프로파일 인프라 관리 (Infrastructure Management)

> **중요 (Important)**: 본 프로젝트의 모든 인프라 서비스는 Docker Compose 프로파일(`profiles`)로 격리되어 있습니다. `--profile` 없이 `docker compose up -d`를 실행하면 `no service selected`가 발생합니다. 로컬 개발 시에는 반드시 `--profile infra` 또는 `--profile all`을 지정하세요.

```bash
# 1. 필수 인프라 전체 실행 (권장: PostgreSQL 16, Redis 7.4, Langfuse v3, OpenSearch)
docker compose --profile infra up -d

# 2. LLM 관측성 스택만 단독 실행 (Langfuse Web, Worker, ClickHouse, MinIO)
docker compose --profile observability up -d

# 3. 검색 및 벡터 스택만 단독 실행 (OpenSearch, OpenSearch Dashboards)
docker compose --profile search up -d

# 4. 백엔드 및 프론트엔드 컨테이너를 포함한 모든 서비스 실행
docker compose --profile all up -d

# 인프라 중지 및 정리
docker compose --profile infra down
```

---

### 4. 주요 서비스 대시보드 및 접속 URL (Dashboard & URLs)
- **사용자 채팅 포털 (Frontend Chat)**: http://localhost:5173
- **관리자 콘솔 (Frontend Admin)**: http://localhost:5173/admin.html
- **백엔드 대화형 API 문서 (Swagger)**: http://localhost:8000/docs
- **Langfuse LLM 관측성 대시보드**: http://localhost:3000
- **OpenSearch Dashboards 콘솔**: http://localhost:5601
- **OpenSearch REST API**: http://localhost:9200

---

### 5. 초기 관리자 로그인 계정 (Initial Admin Credentials)
백엔드 최초 기동 시 데이터베이스 테이블이 자동 생성되며 기본 관리자 계정이 시딩됩니다:
- **아이디 (Username)**: `admin`
- **비밀번호 (Password)**: `admin1234!` (`backend/.env`의 `DEFAULT_ADMIN_PASSWORD`로 변경 가능)
- **역할 (Role)**: `admin` (사용자 대화 포털 및 관리자 콘솔 모두 접근 가능)

---

### 6. 수동 로컬 실행 (Manual Run)
```bash
# 백엔드 실행 (Backend)
cd backend
uv run uvicorn src.main:app --reload --port 8000

# 프론트엔드 실행 (Frontend)
cd ../frontend
npm install
npm run dev
```

---

### 7. 온디맨드 개발자 샌드박스 도구 (`af sandbox` / `./af sandbox`)
AWS EKS, GCP GKE, Azure AKS 및 Rancher 클라우드 쿠버네티스 환경에서 개발자 전용 격리 샌드박스 네임스페이스와 함께 Backend, Frontend, Ingress 워크로드를 원클릭 자동 배포하고, 로컬 코드를 실시간 스트리밍 동기화할 수 있습니다. (RFC 1123 규격 자동 변환 지원)

> 💡 **전역 CLI 미설치 시 무설치 실행 지원 (`./af` 래퍼)**:
> AgentForge CLI가 컴퓨터에 전역으로 설치되어 있지 않더라도, 프로젝트 루트의 `./af` (macOS/Linux) 또는 `af.bat` (Windows) 래퍼 스크립트를 사용하면 `uvx`를 통해 설치 없이 즉시 실행됩니다:
> ```bash
> ./af sandbox up     # Windows: af.bat sandbox up
> ./af sandbox watch
> ```

```bash
# 1. 샌드박스 프로비저닝 (Minikube 환경 감지 시 컨테이너 이미지 자동 빌드 & 적재)
./af sandbox up --csp aws --name $USER --ttl 8h

# Rancher Project 연동 (중앙 거버넌스 및 대시보드 자동 바인딩)
./af sandbox up --rancher-project c-m-xxxx:p-yyyy

# (선택) 이미지 자동 빌드를 건너뛰고 매니페스트만 적용
./af sandbox up --no-build

# 2. 실시간 소스코드 핫리로드 (backend/src 수정 시 원격 Pod로 0.5초 내 동기화)
./af sandbox watch

# 3. 로컬 포트포워딩 터널링 (원격 파드를 localhost:5173, 8000으로 연결)
./af sandbox open --port-forward

# 4. 유휴 시 절전 (Replicas=0 축소로 클라우드 비용 0원화)
./af sandbox pause
./af sandbox resume

# 5. 상태 점검 및 샌드박스 완전 삭제
./af sandbox status
./af sandbox down --force
```

---

### 8. 실전형 대화 부하테스트 도구 (`backend/load_test/`)
Locust 기반 실전 부하테스트 환경이 프로젝트 내에 자동 생성되어 있습니다:
- **실전형 시나리오**: 로그인(`POST /auth/login`) ➔ 대화방 생성(`POST /chats`) ➔ 순차 기술 질문 스트리밍 문답 ➔ 로그아웃
- **LLM 특화 지표 분리 측정**: 첫 토큰 도달 시간(**TTFT**)과 전체 스트리밍 완료 소요 시간(**Total Latency**)을 분리 집계
- **실행 방법**:
  ```bash
  cd backend/load_test
  ./run.sh                    # 웹 UI 대시보드 (http://localhost:8089)
  ./run.sh --headless -u 50   # 헤드리스 자동 부하 테스트 및 HTML 리포트 생성
  ```
- **질문 커스터마이징**: `questions.json`을 수정하여 도메인 특화 질의로 확장할 수 있습니다.

---

### 9. 프론트엔드 UI/UX 디자인 시스템 및 AI 코딩 협업 (Frontend UI/UX Design System & AI Coding Agent Guidelines)
AgentForge는 **스펙 기반 UI 개발 (Spec-Driven UI Development)** 방법론을 적용합니다:
- [`frontend/DESIGN.md`](frontend/DESIGN.md)를 수정하여 프로젝트 고유의 도메인 요구사항, 브랜드 색상, 타이포그래피, 8pt 그리드 여백 및 Do's & Don'ts 규칙을 정의하세요.
- AI 코딩 어시스턴트(Cursor, Claude Code, GitHub Copilot, Windsurf, Antigravity)와 협업할 때 [`frontend/DESIGN.md`](frontend/DESIGN.md)를 **단일 진실 공급원 (Single Source of Truth, SSOT)**으로 지정하면 일관된 고품질 UI 컴포넌트를 생성하고 유지할 수 있습니다.
- 프론트엔드 아키텍처 및 프롬프트 가이드는 [`frontend/README.md`](frontend/README.md)를 참조하세요.

---

### 10. AI 개발 하네스 및 워크플로우 스킬 (AI Developer Harness & Workflow Skills)
본 프로젝트에는 기능 개발, 리팩토링, 결함 수정을 표준화하는 AI 개발 하네스 스킬(`.agents/skills`)이 내장되어 있습니다:
- **`feature-development`** (`.agents/skills/feature-development/SKILL.md`): Clean Architecture 계층 분리 신규 기능 개발 하네스
- **`feature-enhancement`** (`.agents/skills/feature-enhancement/SKILL.md`): 파급 영향도 분석 및 안전한 리팩토링 하네스
- **`bugfix`** (`.agents/skills/bugfix/SKILL.md`): RCA 근본 원인 규명 및 재현 실패 테스트(RED) 선작성 결함 수정 하네스
- **`code-tutor`** (`.agents/skills/code-tutor/SKILL.md`): 2단계 하이브리드 Mermaid 도식화 및 ELI15 Q&A 스토리텔링 코드/아키텍처 튜터 (2-stage Mermaid diagrams and ELI15 Q&A)
- **8단계 표준 엔지니어링 파이프라인**:
  `분석` → `파일 단위 상세 설계` → `설계 리뷰(오버엔지니어링 검토)` → `★사용자 승인 게이트` → `GitHub Issue 등록(단계/상태 태그)` → `Issue 기반 구현` → `코드 리뷰` → `기능 점검(신규/회귀 테스트)` → `결과 보고 및 Issue 종료`
- 세부적인 GitHub CLI(`gh`) 연동 및 라벨 체계는 [`.agents/skills/shared/workflow-spec.md`](.agents/skills/shared/workflow-spec.md)에 기술되어 있습니다.
"""
            readme_path.write_text(readme_content, encoding="utf-8")

        # 7. Post-scaffold syntax verification
        validate_generated_project(dest_root)

        return dest_root

    def _generate_vscode_configs(self, dest_root: Path, frontend: str) -> None:
        """Generate .vscode/launch.json and .vscode/settings.json configurations."""
        vscode_dir = dest_root / ".vscode"
        vscode_dir.mkdir(parents=True, exist_ok=True)

        backend_config: dict[str, Any] = {
            "name": "Backend: FastAPI (uvicorn)",
            "type": "debugpy",
            "request": "launch",
            "python": "${workspaceFolder}/backend/.venv/bin/python",
            "windows": {
                "python": "${workspaceFolder}/backend/.venv/Scripts/python.exe"
            },
            "module": "uvicorn",
            "args": [
                "src.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
                "--reload"
            ],
            "cwd": "${workspaceFolder}/backend",
            "envFile": "${workspaceFolder}/backend/.env",
            "env": {
                "PYTHONPATH": "${workspaceFolder}/backend/src:${workspaceFolder}/backend"
            },
            "jinja": True,
            "justMyCode": False,
            "console": "integratedTerminal"
        }

        configurations: list[dict[str, Any]] = [backend_config]
        compounds: list[dict[str, Any]] = []

        if frontend in ("react", "react-vite"):
            frontend_config: dict[str, Any] = {
                "name": "Frontend: Vite Dev Server",
                "type": "node-terminal",
                "request": "launch",
                "command": "npm run dev",
                "cwd": "${workspaceFolder}/frontend",
                "envFile": "${workspaceFolder}/frontend/.env",
                "serverReadyAction": {
                    "pattern": "Local:\\s+(https?://\\S+)",
                    "uriFormat": "%s",
                    "action": "openExternally"
                }
            }
            configurations.append(frontend_config)
            compounds.append({
                "name": "Fullstack: Backend + Frontend",
                "configurations": [
                    "Backend: FastAPI (uvicorn)",
                    "Frontend: Vite Dev Server"
                ],
                "stopAll": True
            })
        elif frontend == "streamlit":
            frontend_config = {
                "name": "Frontend: Streamlit UI",
                "type": "debugpy",
                "request": "launch",
                "python": "${workspaceFolder}/backend/.venv/bin/python",
                "windows": {
                    "python": "${workspaceFolder}/backend/.venv/Scripts/python.exe"
                },
                "module": "streamlit",
                "args": [
                    "run",
                    "app.py"
                ],
                "cwd": "${workspaceFolder}/frontend",
                "envFile": "${workspaceFolder}/backend/.env",
                "console": "integratedTerminal"
            }
            configurations.append(frontend_config)
            compounds.append({
                "name": "Fullstack: Backend + Frontend",
                "configurations": [
                    "Backend: FastAPI (uvicorn)",
                    "Frontend: Streamlit UI"
                ],
                "stopAll": True
            })

        launch_data: dict[str, Any] = {
            "version": "0.2.0",
            "configurations": configurations
        }
        if compounds:
            launch_data["compounds"] = compounds

        launch_file = vscode_dir / "launch.json"
        if not launch_file.exists():
            launch_file.write_text(json.dumps(launch_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        settings_data: dict[str, Any] = {
            "python.defaultInterpreterPath": "${workspaceFolder}/backend/.venv/bin/python",
            "python.analysis.extraPaths": [
                "${workspaceFolder}/backend",
                "${workspaceFolder}/backend/src"
            ],
            "python.autoComplete.extraPaths": [
                "${workspaceFolder}/backend",
                "${workspaceFolder}/backend/src"
            ]
        }
        settings_file = vscode_dir / "settings.json"
        if not settings_file.exists():
            settings_file.write_text(json.dumps(settings_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
