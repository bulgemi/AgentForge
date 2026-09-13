from pathlib import Path
import tempfile
import pytest

from agentforge.generator.engine import ScaffoldingEngine


def test_code_tutor_skill_files_exist():
    """Verify that code-tutor SKILL.md exists in both root and template directories and are identical."""
    root_dir = Path(__file__).parent.parent
    root_skill = root_dir / ".agents" / "skills" / "code-tutor" / "SKILL.md"
    template_skill = root_dir / "agentforge" / "templates" / "root" / ".agents" / "skills" / "code-tutor" / "SKILL.md"

    assert root_skill.is_file(), f"Root skill file does not exist: {root_skill}"
    assert template_skill.is_file(), f"Template skill file does not exist: {template_skill}"

    assert root_skill.read_text(encoding="utf-8") == template_skill.read_text(encoding="utf-8"), (
        "Root and template code-tutor SKILL.md contents must be identical"
    )


def test_code_tutor_skill_content_structure():
    """Verify that code-tutor SKILL.md adheres to the required design principles and templates."""
    root_dir = Path(__file__).parent.parent
    skill_file = root_dir / ".agents" / "skills" / "code-tutor" / "SKILL.md"
    content = skill_file.read_text(encoding="utf-8")

    # Metadata check
    assert "name: code-tutor" in content
    assert "description:" in content

    # Core Principles check
    assert "2단계 하이브리드 도식화" in content
    assert "ELI15 Q&A 탐구형 스토리텔링" in content
    assert "Stage 1 (컴포넌트 구조도)" in content
    assert "Stage 2 (시퀀스 다이어그램)" in content

    # 3 Core Inquiries check
    assert "왜 이렇게 설계되었을까?" in content
    assert "요청이 오면 어디로 갈까?" in content or "요청이 들어오면 데이터는 어디로 흐를까?" in content
    assert "예외나 장애는 어떻게 처리될까?" in content or "문제가 생기면(예외/실패) 어떻게 될까?" in content

    # Output & Archiving check
    assert "docs/architecture/" in content
    assert "sequenceDiagram" in content
    assert "flowchart" in content


def test_agents_routing_includes_code_tutor():
    """Verify that AGENTS.md in root and template include code-tutor in Zero-Prompt routing."""
    root_dir = Path(__file__).parent.parent
    agents_root = (root_dir / "AGENTS.md").read_text(encoding="utf-8")
    agents_template = (root_dir / "agentforge" / "templates" / "root" / "AGENTS.md").read_text(encoding="utf-8")

    for text in [agents_root, agents_template]:
        assert "code-tutor" in text
        assert ".agents/skills/code-tutor/SKILL.md" in text
        assert "하이브리드 Mermaid" in text
        assert "ELI15" in text


def test_claude_and_cursorrules_include_code_tutor():
    """Verify that CLAUDE.md and .cursorrules reference code-tutor."""
    root_dir = Path(__file__).parent.parent
    claude_root = (root_dir / "CLAUDE.md").read_text(encoding="utf-8")
    claude_tmpl = (root_dir / "agentforge" / "templates" / "root" / "CLAUDE.md").read_text(encoding="utf-8")
    cursor_root = (root_dir / ".cursorrules").read_text(encoding="utf-8")
    cursor_tmpl = (root_dir / "agentforge" / "templates" / "root" / ".cursorrules").read_text(encoding="utf-8")

    for text in [claude_root, claude_tmpl]:
        assert "code-tutor" in text
        assert "2-stage Mermaid + ELI15 Q&A" in text

    for text in [cursor_root, cursor_tmpl]:
        assert "code-tutor" in text


def test_scaffolding_engine_creates_code_tutor_skill():
    """Verify that creating a project via ScaffoldingEngine copies code-tutor SKILL.md and updates README."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = ScaffoldingEngine()
        project_dir = engine.generate(
            project_name="tutor-demo-agent",
            target_dir=tmpdir,
            framework="langgraph",
            frontend="react",
        )

        skill_file = project_dir / ".agents" / "skills" / "code-tutor" / "SKILL.md"
        assert skill_file.is_file(), f"Scaffolded project missing {skill_file}"

        skill_content = skill_file.read_text(encoding="utf-8")
        assert "name: code-tutor" in skill_content
        assert "ELI15 Q&A" in skill_content

        readme_content = (project_dir / "README.md").read_text(encoding="utf-8")
        assert "code-tutor" in readme_content
        assert "2-stage Mermaid diagrams and ELI15 Q&A" in readme_content
