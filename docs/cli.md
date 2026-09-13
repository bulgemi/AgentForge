# ⚙️ CLI & 스캐폴딩 완전 가이드 (CLI & Scaffolding Guide)

> [🏠 README](../README.md) &nbsp;|&nbsp; [⚡ Quickstart](quickstart.md) &nbsp;|&nbsp; **[⚙️ CLI & Scaffolding](cli.md)** &nbsp;|&nbsp; [🏗️ Architecture](architecture.md) &nbsp;|&nbsp; [🛠️ AI Skills](skills.md) &nbsp;|&nbsp; [🐳 Infrastructure](infrastructure.md) &nbsp;|&nbsp; [🌱 Env Variables](env-vars.md)

---

AgentForge는 완전한 독립형(Standalone) 프로덕션 AI 에이전트 프로젝트를 수 초 만에 자동 합성하는 전용 CLI 도구(`agentforge`, `af`)와 Python 프로그래밍 API(`ScaffoldingEngine`)를 제공합니다.

---

## 1. 설치 방법 (Installation)

### 방법 A. PyPI / uv를 통한 전역 CLI 설치 (가장 권장)

```bash
# uv를 통한 초고속 격리 설치 (권장)
uv tool install agentforge

# 또는 pip / pipx를 통한 전역 설치
pip install agentforge
# pipx install agentforge
```

### 방법 B. 원클릭 자동 설치 스크립트 (저장소 소스 클론 시)

저장소를 클론한 후 운영체제에 맞는 원클릭 설치 스크립트를 실행하면 가상환경 구성, 패키지 설치, CLI 등록까지 전 과정을 자동으로 완료합니다.

```bash
git clone https://github.com/bulgemi/AgentForge.git
cd AgentForge

# macOS / Linux
./install.sh

# Windows
install.bat
```
- 시스템의 Python 3.12+ 및 `uv` 설치 여부를 자동 감지합니다.
- `uv`가 설치되어 있으면 초고속 설치를 진행하며, 없을 시 표준 `python venv/pip`로 안전하게 폴백합니다.

### 방법 C. 수동 소스 클론 및 개발자 모드 설치

```bash
git clone https://github.com/bulgemi/AgentForge.git
cd AgentForge

# 편집 가능(editable) 모드 설치
pip install -e .
# 또는 uv 환경에서 개발 의존성 포함 설치:
uv pip install -e ".[dev]"
```

> 💡 **단축 명령어 지원**: 설치가 완료되면 `agentforge`와 동일한 기능의 단축 명령어인 `af`를 자유롭게 사용할 수 있습니다.
> ```bash
> af --help
> ```

---

## 2. CLI 스캐폴딩 사용법 (`agentforge new` / `af new`)

터미널에서 명령어 한 줄로 원하는 에이전트 프레임워크와 프론트엔드 인터페이스 조합의 독립형 프로젝트를 생성합니다.

```bash
# 기본 구문
agentforge new <프로젝트명> [OPTIONS]

# 단축형
af new <프로젝트명> [OPTIONS]
```

### 📋 CLI 옵션 및 파라미터 상세

| 옵션명 | 단축형 | 기본값 | 선택 가능 값 | 설명 |
| :--- | :---: | :---: | :--- | :--- |
| `--framework` | `-m` | `langgraph` | `langgraph`, `langchain`, `deepagent`, `adk`, `bedrock` | 프로젝트에 탑재할 에이전트 오케스트레이션 프레임워크 |
| `--frontend` | `-f` | `react` | `react` (또는 `react-vite`), `streamlit`, `none` | 사용자 인터페이스 템플릿 종류 |
| `--path` | `-p` | 현재 디렉토리 (`.`) | 유효한 디렉토리 경로 문자열 | 프로젝트 폴더가 생성될 부모 디렉토리 위치 |
| `--force` | | `False` | 플래그 (지정 시 `True`) | 대상 폴더가 이미 존재하더라도 강제로 덮어쓰기 |

### 💡 실전 생성 예시

```bash
# 1. 기본 추천 조합 (LangGraph + React Vite 풀스택)
af new customer-service-bot

# 2. AWS Bedrock 엔터프라이즈 에이전트 + Streamlit 대시보드
af new enterprise-rag-agent --framework bedrock --frontend streamlit

# 3. DeepAgent 심층 추론 백엔드 전용 API (UI 제외)
af new deep-reasoning-core --framework deepagent --frontend none

# 4. 사내 특정 레포지토리 하위 경로에 강제 생성
af new internal-copilot --framework langchain --path ~/company/agents --force
```

---

## 3. CLI 운영 명령어 (`dev`, `build`, `deploy`)

프로젝트 생성 후 해당 디렉토리 내부에서 앱의 개발, 컨테이너 빌드, Kubernetes 배포를 제어할 수 있습니다.

### 1) 로컬 개발 서버 동시 실행 (`agentforge dev` / `af dev`)

백엔드(FastAPI uvicorn)와 프론트엔드(Vite / Streamlit) 개발 서버를 하나의 터미널 창에서 컬러 로그 분할로 동시 구동합니다.

```bash
cd my-agent
af dev
```

> **단축 스크립트 안내**: 생성된 프로젝트 루트의 `./run.sh` (Windows: `run.bat`)를 실행하면 가상환경 검사, Docker 인프라 기동, 개발 서버 실행까지 완전 자동 수행됩니다.

### 2) Docker 이미지 빌드 (`agentforge build` / `af build`)

프로덕션용 멀티스테이지 백엔드 및 프론트엔드(Nginx 경량 이미지) 컨테이너 이미지를 빌드합니다.

```bash
# 기본 로컬 태그 빌드
af build

# 특정 태그 및 프론트엔드/백엔드 개별 지정
af build --tag v1.0.0 --target backend
```

### 3) Kubernetes 클러스터 배포 (`agentforge deploy` / `af deploy`)

`k8s/` 매니페스트를 타겟 환경(dev/prd) 클러스터에 원클릭으로 롤아웃합니다.

```bash
# 개발(dev) 네임스페이스 배포
af deploy --env dev

# 운영(prd) 클러스터 고가용성(HA) 배포
af deploy --env prd
```

---

## 4. Python 프로그래밍 API (`ScaffoldingEngine`)

CLI뿐만 아니라 Python 코드 내에서 직접 프로젝트 합성 엔진을 임포트하여 자동화 파이프라인이나 커스텀 포털에 통합할 수 있습니다.

```python
from pathlib import Path
from agentforge.generator.engine import ScaffoldingEngine

# 1. 스캐폴딩 엔진 초기화
engine = ScaffoldingEngine()

# 2. 프로그래밍 방식으로 프로젝트 생성
project_path = engine.generate(
    project_name="automated-agent",
    target_dir=Path("./output"),
    framework="langgraph",
    frontend="react",
    force=True,
)

print(f"✨ 프로젝트 생성 완료: {project_path}")
```

---

## 5. 스캐폴딩 엔진의 5단계 합성 메커니즘

`ScaffoldingEngine`은 단순 파일 복사가 아닌, 문법 검증과 독립형(Standalone) 아키텍처 원칙에 따라 5단계로 안전하게 프로젝트를 빌드합니다:

```text
[1. 입력 검증] -> [2. 템플릿 트리 복사 & 변수 바인딩] -> [3. Core 엔진 독립 복사] 
              -> [4. AI 개발 하네스(.agents/skills) 주입] -> [5. 사후 문법 및 정합성 검증]
```

1. **입력 파라미터 검증 (`validator.py`)**: 프로젝트명 유효성, 프레임워크/프론트엔드 지원 여부, 디렉토리 권한을 사전 검증합니다.
2. **템플릿 합성 & 토큰 치환**: `backend`, `frontend`, `infra`, `k8s` 템플릿의 정적 텍스트 및 `.env` 파일 내 `{{ project_name }}`, `{{ framework }}` 토큰을 치환합니다.
3. **Standalone Core 엔진 독립 주입 (`copier.py`)**: 프레임워크 저장소에 종속되지 않도록 `BaseAgentAdapter`, `streaming`, `database`, `logging` 모듈을 생성된 프로젝트 백엔드의 `backend/src/core/`로 완전 독립 복사합니다.
4. **AI 개발 하네스 자동 주입**: AI 코딩 에이전트 협업을 위한 `.agents/skills/`(`feature-development`, `feature-enhancement`, `bugfix`, `shared/workflow-spec.md`)를 프로젝트 루트로 복사합니다.
5. **사후 문법 및 정합성 검증 (`validate_generated_project`)**: 생성된 프로젝트 내 Python 코드들의 문법 오류(`ast.parse`)를 자동 점검하여 즉시 실행 가능한 무결성 상태를 보장합니다.

---

> [🏠 README](../README.md) &nbsp;|&nbsp; [⚡ Quickstart](quickstart.md) &nbsp;|&nbsp; **[⚙️ CLI & Scaffolding](cli.md)** &nbsp;|&nbsp; [🏗️ Architecture](architecture.md) &nbsp;|&nbsp; [🛠️ AI Skills](skills.md) &nbsp;|&nbsp; [🐳 Infrastructure](infrastructure.md) &nbsp;|&nbsp; [🌱 Env Variables](env-vars.md)
