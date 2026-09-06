# AgentForge E2E Testing Infrastructure Specification

**Document Version**: 1.0.0  
**Date**: 2026-09-06  
**Track**: E2E Testing Track  
**Track Lead**: `teamwork_preview_test_writer_e2e_1`  
**Status**: APPROVED & ACTIVE  

---

## 1. Executive Summary & Testing Philosophy

AgentForge is an enterprise-grade AI agent framework and standalone scaffolding engine designed to generate zero-bloat, production-ready, fullstack monorepos. To guarantee architectural integrity, security robustness, and requirement fulfillment across all supported agent frameworks, authentication protocols, and deployment targets, AgentForge employs a **4-Tier Opaque-Box E2E Testing Methodology**.

### Core Testing Principles:
1. **Opaque-Box Requirement-Driven**: Tests are derived strictly from authoritative specifications (`ORIGINAL_REQUEST.md`, `README.md`, `PROJECT.md`) and interface contracts. Tests observe only inputs and outputs without coupling to private implementation details.
2. **Deterministic Expected Output Derivation**: Expected results are computed from contract invariants, mathematical/cryptographic properties (e.g., Bcrypt verification, JWT claims signatures, sliding-window time bounds), and standardized wire formats (e.g., SSE `text/event-stream`).
3. **Progressive Testability**: The test suite can run at any phase of the development lifecycle. It incorporates contract harnesses that seamlessly test live framework implementations as milestones complete, while maintaining self-contained verification of protocol compliance.
4. **Hermetic Isolation**: Every test creates its own sandboxed temporary state (mock Redis keyspaces, temporary directories, isolated session tokens) and guarantees clean teardown without cross-test state pollution.
5. **Adversarial & Edge-Case Rigor**: Boundary conditions, malformed payloads, injection vectors, and disconnection events are rigorously exercised to ensure high availability and resilient failure cascading.

---

## 2. 4-Tier Test Architecture & Taxonomy

```
                     ┌─────────────────────────────────────────┐
                     │  Tier 4: Real-World Scenarios (>= 5)    │
                     │  Full Scaffolding, Auth Flow, SSE Chat, │
                     │  Dev Mode Verification, K8s Dry-Run     │
                     └────────────────────┬────────────────────┘
                                          │
                     ┌────────────────────┴────────────────────┐
                     │  Tier 3: Cross-Feature Combinations     │
                     │  Auth + SSE, DB Pagination + Redis,     │
                     │  CLI Flags + Templates, Semaphores      │
                     └────────────────────┬────────────────────┘
                                          │
                     ┌────────────────────┴────────────────────┐
                     │  Tier 2: Boundary & Corner Cases        │
                     │  Empty Inputs, Disconnects, Pool Limits │
                     │  Expired Tokens, Rate Limits, Bad Flags │
                     └────────────────────┬────────────────────┘
                                          │
                     ┌────────────────────┴────────────────────┐
                     │  Tier 1: Feature Coverage (Isolation)   │
                     │  Adapter, SSE, Database, Logging/Config │
                     │  CLI, Multi-Auth, Multi-Portal, Infra   │
                     └─────────────────────────────────────────┘
```

### 2.1 Tier 1: Feature Coverage (Isolation)
Tests each inventoried feature in isolation to verify contract conformance, return types, error handling, and parameter validation.
- **Coverage Requirement**: $\ge 5$ tests per feature area across all inventoried features.
- **Feature Areas**:
  1. `F1_ADAPTER`: BaseAgentAdapter standard interface (`ainvoke`, `astream`, `ahandle_interrupt`), `AgentChunk`, `AgentEventType` normalization, and tool call serialization.
  2. `F2_STREAMING`: `SSETokenStreamer` wire format (`event: ...\ndata: ...\n\n`), anti-buffering HTTP headers (`X-Accel-Buffering: no`), and `RuntimeContext` cancellation tracking.
  3. `F3_DATABASE`: `Database` singleton connection pool manager, sync/async session generators, database health ping (`SELECT 1`), and `PageableParams` pagination metadata.
  4. `F4_LOGGING_CONFIG`: Structured JSON logger (`setup_logger`, ISO timestamps, correlation ID propagation) and Pydantic configuration (`BaseAppSettings`).
  5. `F5_CLI_GENERATOR`: CLI main dispatcher (`agentforge`, `af`), standalone core copier, template parameter substitution engine, and scaffolding validator.
  6. `F6_AUTH_SECURITY`: Multi-protocol authentication (Bcrypt ID/PW, LDAP bind, SAML 2.0 metadata/ACS), Redis token blacklist (`blacklist:{jti}`), and sliding-window rate limiter.
  7. `F7_FRONTEND_MULTI_PORTAL`: Multi-entrypoint Vite configuration (`index.html` chat, `admin.html` admin), frontend SSE chunk parser, HITL approval cards, and offline zero-CDN vector UI.
  8. `F8_INFRA_K8S`: Zero-bloat `docker-compose.yml` 4-service stack, Kubernetes `dev`/`prd` manifests, and `k8s-deploy.sh` preflight/checksum automation.

### 2.2 Tier 2: Boundary & Corner Cases
Exercises extreme inputs, hostile conditions, and edge boundaries.
- **Coverage Requirement**: $\ge 5$ tests per boundary area.
- **Boundary Areas**:
  1. `B1_EMPTY_INPUTS`: Empty prompts, whitespace-only messages, null configurations, extreme payload sizes ($>1\text{ MB}$).
  2. `B2_DISCONNECTS`: Client connection drops midway through SSE streaming, generator aborts, semaphore auto-release on disconnect.
  3. `B3_POOL_LIMITS`: Database connection pool saturation, concurrency semaphore limits, queueing timeouts.
  4. `B4_AUTH_EXPIRED_INVALID`: Expired JWT tokens, tampered signatures, blacklisted JTI tokens, invalid LDAP credentials, expired SAML assertions.
  5. `B5_RATE_LIMIT_EXCEEDED`: Rapid burst traffic exceeding window threshold, HTTP 429 Too Many Requests response, sliding window recovery.
  6. `B6_INVALID_FLAGS`: Invalid framework names, unsupported frontend selections, illegal project slugs, existing non-empty target paths without `--force`.

### 2.3 Tier 3: Cross-Feature Combinations (Pairwise Coverage)
Evaluates module interoperability and contract adherence across feature boundaries.
- **Pairs Covered**:
  1. **Auth + Streaming**: Authenticated SSE streaming, token revocation during active streaming session, unauthenticated rejection (401), role-based streaming gates.
  2. **DB Pagination + Redis Session**: Paginated query execution bound to active Redis session state, token invalidation during multi-page traversal.
  3. **CLI Flags + Template Generation**: Combinations of `--framework` (`langgraph`, `bedrock`, `deepagent`, `langchain`, `adk`) and `--frontend` (`react`, `streamlit`, `none`).
  4. **Concurrency Semaphore + Streaming**: Concurrent SSE streams competing for limited execution semaphores with graceful queuing.
  5. **SSO + JIT User Provisioning + Database**: LDAP bind / SAML ACS assertion driving dynamic user model upsert in SQLModel database.

### 2.4 Tier 4: Real-World Application Scenarios
Full end-to-end integration journeys simulating realistic developer and user interactions.
- **Scenarios Covered**:
  1. **Scenario 1 (Full Scaffolding Lifecycle)**: Run `agentforge new`, verify directory layout, verify standalone core copied without parent dependencies, verify `compileall` syntax validity, verify `package.json` and Dockerfiles.
  2. **Scenario 2 (Multi-Protocol Auth & Token Lifecycle)**: Login via ID/PW -> issue JWT pair -> access protected endpoints -> rotate refresh token -> logout -> verify Redis blacklist blocks subsequent requests.
  3. **Scenario 3 (Multi-Turn Chat with HITL Interrupt Approval)**: User sends chat message -> SSE stream begins -> agent pauses at human approval gate (`event: interrupt`) -> operator approves via REST API -> stream resumes and completes with `event: done`.
  4. **Scenario 4 (Local Dev Mode Startup & Health Verification)**: Simulate `agentforge dev` orchestration -> verify backend `/healthz` endpoint reporting DB/Redis status -> verify frontend Vite reverse-proxy configuration.
  5. **Scenario 5 (Container Build & Kubernetes Deploy Dry-Run)**: Multi-stage Dockerfile inspection -> Kubernetes manifest validation -> execute `k8s-deploy.sh --dry-run` for dev and prd environments.

---

## 3. Directory Layout & Artifacts

All test files reside strictly in `tests/e2e/`. No test code or user files are placed in `.agents/`.

```text
AgentForge/
├── TEST_INFRA.md                          # Test infrastructure specification (this document)
├── TEST_READY.md                          # Readiness and verification summary
├── tests/
│   ├── __init__.py
│   └── e2e/
│       ├── __init__.py
│       ├── conftest.py                    # Shared fixtures, test doubles, contract harnesses
│       ├── test_tier1_features.py         # 41 Tier 1 feature isolation tests
│       ├── test_tier2_boundaries.py       # 31 Tier 2 boundary & corner case tests
│       ├── test_tier3_combinations.py     # 15 Tier 3 pairwise cross-feature tests
│       ├── test_tier4_scenarios.py        # 5 Tier 4 real-world application scenario tests
│       └── run_tests.py                   # Unified test runner with tier filtering and reporting
```

---

## 4. Test Harness & Fixture Architecture (`conftest.py`)

The test harness provides contract-accurate test doubles and fixtures:
1. **`InMemoryRedis`**: Fully implements Redis operations (`get`, `set`, `setex`, `exists`, `delete`, `zadd`, `zremrangebyscore`, `zcard`, `expire`) with time-aware sliding-window Lua simulation for rate limiting and token blacklisting.
2. **`MockDatabase`**: In-memory SQLite connection manager mimicking the `Database` singleton, providing sync (`Session`) and async (`AsyncSession`) session makers, connection ping, and pagination helpers.
3. **`MockAuthService`**: Standardized Bcrypt hasher, JWT signer (PyJWT) with expiration and JTI claims, LDAP credential validator, and SAML assertion parser.
4. **`MockAgentAdapter`**: Standard `BaseAgentAdapter` implementation providing configurable chunk emission (`token`, `evidence`, `interrupt`, `done`, `error`) and HITL interrupt state resume.
5. **`MockSSEStreamer`**: Formats async chunk streams into standard SSE wire protocol lines and verifies anti-buffering headers.
6. **`TempWorkspace`**: Temporary directory fixture ensuring complete isolation for scaffolding tests and CLI file operations.

---

## 5. Execution Commands & Test Runner

### 5.1 Running with the Unified Test Runner
The custom test runner (`tests/e2e/run_tests.py`) provides formatted console reporting, tier selection, and timing statistics:

```bash
# Run all 4 tiers (complete E2E test suite)
python3 tests/e2e/run_tests.py

# Run specific tiers
python3 tests/e2e/run_tests.py --tier 1
python3 tests/e2e/run_tests.py --tier 2
python3 tests/e2e/run_tests.py --tier 3
python3 tests/e2e/run_tests.py --tier 4

# Run with verbose output
python3 tests/e2e/run_tests.py -v
```

### 5.2 Running with Pytest
Standard pytest execution is fully supported:

```bash
# Run all E2E tests
pytest tests/e2e -v

# Run a specific tier
pytest tests/e2e/test_tier1_features.py -v
pytest tests/e2e/test_tier2_boundaries.py -v
pytest tests/e2e/test_tier3_combinations.py -v
pytest tests/e2e/test_tier4_scenarios.py -v

# Run with keyword filter
pytest tests/e2e -k "rate_limit or auth"
```

---

## 6. Verification & Quality Gate Policies

1. **Pass Criteria**: 100% of all 92 tests across Tiers 1–4 must pass.
2. **Zero Facade Policy**: Every test must assert concrete values, payload schemas, exception types, or wire protocol formats. No vacuous `assert True` tests are permitted.
3. **Defect Escalation**: Any discrepancy between actual implementation output and the authoritative interface contracts must be formally escalated to the implementing agent with reproducible inputs and expected vs. actual outputs.
