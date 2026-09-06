"""FastAPI application entrypoint."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from dotenv import load_dotenv
load_dotenv()

import uvicorn
from src.bootstrap import create_agent_app

# Default Framework Adapter selection
def get_default_adapter():
    """Load framework adapter based on project scaffolding."""
    framework = "{{ framework }}"
    try:
        if framework == "langgraph":
            from src.core.adapter import LangGraphAdapter
            return LangGraphAdapter(name="{{ project_name }}")
        elif framework == "langchain":
            from src.core.adapter import LangChainAdapter
            return LangChainAdapter(name="{{ project_name }}")
        elif framework == "deepagent":
            from src.core.adapter import DeepAgentAdapter
            return DeepAgentAdapter(name="{{ project_name }}")
        elif framework == "adk":
            from src.core.adapter import get_adapter
            return get_adapter("adk", name="{{ project_name }}")
        elif framework == "bedrock":
            from src.core.adapter import BedrockAdapter
            return BedrockAdapter(name="{{ project_name }}")
    except Exception:
        pass
    from src.core.adapter import LangGraphAdapter
    return LangGraphAdapter(name="{{ project_name }}")


app = create_agent_app(agent_adapter=get_default_adapter())


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("src.main:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    main()
