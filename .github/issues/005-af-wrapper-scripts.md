---
title: "feat(cli): provide ./af and af.bat project-level wrapper scripts for standalone zero-install execution"
labels: ["enhancement", "stage:done", "status:completed", "cli", "wrapper", "sandbox"]
status: "completed"
created_at: "2026-09-15T22:45:00+09:00"
closed_at: "2026-09-15T23:01:00+09:00"
issue_url: "https://github.com/bulgemi/AgentForge/issues/33"
---

# feat(cli): Provide `./af` and `af.bat` Project-Level Wrapper Scripts for Standalone Zero-Install Execution

## Overview
Provide `./af` (POSIX shell) and `af.bat` (Windows batch) wrapper scripts in scaffolded projects (similar to Gradle's `./gradlew`).
This allows developers who clone the standalone project to execute sandbox and other CLI commands without needing a globally installed `agentforge` CLI, falling back to `uvx` or guidance.

## Tasks
- [ ] Create `agentforge/templates/scripts/af`
- [ ] Create `agentforge/templates/scripts/af.bat`
- [ ] Update `agentforge/generator/engine.py` to copy `af` and `af.bat` to project root with executable permissions
- [ ] Update scaffolded `README.md` and `docs/sandbox.md` to highlight `./af` and `af.bat` usage
- [ ] Add unit tests in `tests/test_generator.py` to verify wrapper scripts
- [ ] Verify test suite passes
