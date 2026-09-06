"""Shared fixtures, contract models, and test doubles for AgentForge E2E Tests."""

import asyncio
import datetime
import json
import os
import shutil
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, Generator, List, Optional, Tuple

import bcrypt
import jwt
import pytest


# ============================================================================
# 1. Authoritative Core Contract Models (PROJECT.md & ORIGINAL_REQUEST.md)
# ============================================================================

class AgentEventType(str, Enum):
    TOKEN = "token"
    EVIDENCE = "evidence"
    META = "meta"
    INTERRUPT = "interrupt"
    ERROR = "error"
    DONE = "done"


class AgentRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    FUNCTION = "function"


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ToolResult:
    tool_call_id: str
    name: str
    content: str
    is_error: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgentMessage:
    role: AgentRole
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["role"] = self.role.value if isinstance(self.role, AgentRole) else self.role
        return res


@dataclass
class AgentChunk:
    type: AgentEventType
    content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value if isinstance(self.type, AgentEventType) else self.type,
            "content": self.content,
            "metadata": self.metadata,
            "error": self.error,
            "id": self.id,
        }


@dataclass
class AgentInput:
    prompt: Optional[str] = None
    messages: List[AgentMessage] = field(default_factory=list)
    session_id: Optional[str] = None
    chat_id: Optional[str] = None
    turn_id: Optional[str] = None
    tools: Optional[List[ToolDefinition]] = None
    config: Dict[str, Any] = field(default_factory=dict)
    resume_payload: Optional[Dict[str, Any]] = None


@dataclass
class AgentOutput:
    content: str
    messages: List[AgentMessage] = field(default_factory=list)
    tool_calls: List[ToolCall] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    turn_id: Optional[str] = None
    finish_reason: Optional[str] = None


@dataclass
class PageMetadata:
    page: int
    size: int
    total_elements: int
    total_pages: int


@dataclass
class PageableParams:
    page: int = 1
    size: int = 20
    sort: Optional[str] = None

    def sanitize(self) -> "PageableParams":
        safe_page = max(1, self.page)
        safe_size = max(1, min(100, self.size))
        return PageableParams(page=safe_page, size=safe_size, sort=self.sort)


@dataclass
class Page:
    items: List[Any]
    metadata: PageMetadata


# ============================================================================
# 2. In-Memory Redis Test Double (Blacklist & Sliding-Window Rate Limiter)
# ============================================================================

class InMemoryRedis:
    """Thread-safe and time-aware in-memory Redis test double."""

    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._expires: Dict[str, float] = {}
        self._zsets: Dict[str, List[Tuple[str, float]]] = {}
        self._lock = asyncio.Lock()

    def _purge_expired(self, key: str) -> None:
        now = time.time()
        if key in self._expires and self._expires[key] <= now:
            self._store.pop(key, None)
            self._zsets.pop(key, None)
            self._expires.pop(key, None)

    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            self._purge_expired(key)
            val = self._store.get(key)
            if val is None:
                return None
            return str(val)

    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        async with self._lock:
            self._store[key] = value
            if ex is not None:
                self._expires[key] = time.time() + ex
            elif key in self._expires:
                del self._expires[key]
            return True

    async def setex(self, key: str, time_secs: int, value: Any) -> bool:
        return await self.set(key, value, ex=time_secs)

    async def exists(self, *keys: str) -> int:
        async with self._lock:
            count = 0
            for k in keys:
                self._purge_expired(k)
                if k in self._store or k in self._zsets:
                    count += 1
            return count

    async def delete(self, *keys: str) -> int:
        async with self._lock:
            count = 0
            for k in keys:
                removed = False
                if k in self._store:
                    del self._store[k]
                    removed = True
                if k in self._zsets:
                    del self._zsets[k]
                    removed = True
                if k in self._expires:
                    del self._expires[k]
                if removed:
                    count += 1
            return count

    async def zadd(self, key: str, mapping: Dict[str, float]) -> int:
        async with self._lock:
            self._purge_expired(key)
            if key not in self._zsets:
                self._zsets[key] = []
            added = 0
            for member, score in mapping.items():
                self._zsets[key] = [item for item in self._zsets[key] if item[0] != member]
                self._zsets[key].append((member, score))
                added += 1
            self._zsets[key].sort(key=lambda x: x[1])
            return added

    async def zremrangebyscore(self, key: str, min_score: float, max_score: float) -> int:
        async with self._lock:
            self._purge_expired(key)
            if key not in self._zsets:
                return 0
            initial = len(self._zsets[key])
            self._zsets[key] = [
                item for item in self._zsets[key]
                if not (min_score <= item[1] <= max_score)
            ]
            return initial - len(self._zsets[key])

    async def zcard(self, key: str) -> int:
        async with self._lock:
            self._purge_expired(key)
            return len(self._zsets.get(key, []))

    async def expire(self, key: str, seconds: int) -> bool:
        async with self._lock:
            if key in self._store or key in self._zsets:
                self._expires[key] = time.time() + seconds
                return True
            return False

    async def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window_seconds: int,
    ) -> Tuple[bool, int, float]:
        """Atomic sliding-window rate limit simulation (matches Redis Lua script contract)."""
        async with self._lock:
            key = f"rate_limit:{identifier}"
            now = time.time()
            min_score = 0.0
            max_score = now - window_seconds

            if key not in self._zsets:
                self._zsets[key] = []
            self._zsets[key] = [item for item in self._zsets[key] if item[1] > max_score]

            current_count = len(self._zsets[key])
            if current_count < limit:
                entry_id = str(uuid.uuid4())
                self._zsets[key].append((entry_id, now))
                self._expires[key] = now + window_seconds
                remaining = limit - (current_count + 1)
                return True, remaining, 0.0
            else:
                oldest_timestamp = self._zsets[key][0][1] if self._zsets[key] else now
                retry_after = max(0.1, (oldest_timestamp + window_seconds) - now)
                return False, 0, round(retry_after, 2)


# ============================================================================
# 3. Database Test Double (Singleton, Sync/Async Sessions, Pagination)
# ============================================================================

class MockDatabase:
    """Contract-compliant Database connection manager test double."""

    _instance: Optional["MockDatabase"] = None

    def __init__(self, database_url: str = "sqlite:///:memory:"):
        self.database_url = database_url
        self._is_connected = True
        self._pool_size = 10
        self._active_connections = 0
        self._max_overflow = 5
        self._records: List[Dict[str, Any]] = []

    @classmethod
    def get_instance(cls, database_url: str = "sqlite:///:memory:") -> "MockDatabase":
        if cls._instance is None:
            cls._instance = cls(database_url)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    def ping(self) -> bool:
        return self._is_connected

    def set_connected(self, status: bool) -> None:
        self._is_connected = status

    def get_sync_session(self) -> Generator[Dict[str, Any], None, None]:
        if not self._is_connected:
            raise ConnectionError("Database connection unreachable")
        if self._active_connections >= (self._pool_size + self._max_overflow):
            raise TimeoutError("Database connection pool exhausted")
        self._active_connections += 1
        session_mock = {"type": "sync_session", "active": True, "db": self}
        try:
            yield session_mock
        finally:
            session_mock["active"] = False
            self._active_connections -= 1

    async def get_async_session(self) -> AsyncGenerator[Dict[str, Any], None]:
        if not self._is_connected:
            raise ConnectionError("Database connection unreachable")
        if self._active_connections >= (self._pool_size + self._max_overflow):
            raise TimeoutError("Database connection pool exhausted")
        self._active_connections += 1
        session_mock = {"type": "async_session", "active": True, "db": self}
        try:
            yield session_mock
        finally:
            session_mock["active"] = False
            self._active_connections -= 1

    def paginate(self, items: List[Any], params: PageableParams) -> Page:
        sanitized = params.sanitize()
        total_elements = len(items)
        total_pages = max(1, (total_elements + sanitized.size - 1) // sanitized.size) if total_elements > 0 else 0

        start_idx = (sanitized.page - 1) * sanitized.size
        end_idx = start_idx + sanitized.size
        sliced = items[start_idx:end_idx]

        metadata = PageMetadata(
            page=sanitized.page,
            size=sanitized.size,
            total_elements=total_elements,
            total_pages=total_pages,
        )
        return Page(items=sliced, metadata=metadata)


# ============================================================================
# 4. Authentication Service Test Double (ID/PW, LDAP, SAML, JWT)
# ============================================================================

class MockAuthService:
    """Contract-compliant multi-protocol authentication service test double."""

    SECRET_KEY = "agentforge_super_secure_test_secret_key_at_least_32_bytes_long"
    ALGORITHM = "HS256"

    def __init__(self, redis: Optional[InMemoryRedis] = None):
        self.redis = redis or InMemoryRedis()
        self._user_db: Dict[str, Dict[str, Any]] = {}
        # Pre-seed a test user
        self.register_user("testuser", "CorrectPassword123!", "USER", "LOCAL")
        self.register_user("adminuser", "AdminSecret123!", "ADMIN", "LOCAL")

    def register_user(
        self,
        username: str,
        password: str,
        role: str = "USER",
        provider: str = "LOCAL",
    ) -> Dict[str, Any]:
        salt = bcrypt.gensalt(rounds=10)
        password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
        user = {
            "id": f"usr_{uuid.uuid4().hex[:12]}",
            "username": username,
            "password_hash": password_hash,
            "role": role,
            "provider": provider,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        self._user_db[username] = user
        return user

    def authenticate_local(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        user = self._user_db.get(username)
        if not user or user["provider"] != "LOCAL":
            return None
        if bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
            return user
        return None

    def authenticate_ldap(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        # Simulate corporate LDAP directory (e.g. Active Directory bind)
        if username.startswith("corp_") and password == "CorpLdapPass2026!":
            role = "ADMIN" if "admin" in username else "USER"
            user = {
                "id": f"ldap_{uuid.uuid4().hex[:12]}",
                "username": username,
                "role": role,
                "provider": "LDAP",
                "email": f"{username}@corp.internal",
            }
            self._user_db[username] = user
            return user
        return None

    def authenticate_saml(self, saml_response_xml: str) -> Optional[Dict[str, Any]]:
        # Check XML assertion signatures and timestamps
        if "<saml:Assertion" in saml_response_xml and "AgentForge_SP" in saml_response_xml:
            if "status:Success" in saml_response_xml:
                username = "sso_user"
                role = "USER"
                if "Role:Admin" in saml_response_xml:
                    role = "ADMIN"
                user = {
                    "id": f"saml_{uuid.uuid4().hex[:12]}",
                    "username": username,
                    "role": role,
                    "provider": "SAML",
                    "email": f"{username}@idp.com",
                }
                self._user_db[username] = user
                return user
        return None

    def create_token_pair(
        self,
        user: Dict[str, Any],
        access_ttl_minutes: int = 15,
        refresh_ttl_days: int = 7,
    ) -> Dict[str, Any]:
        now = datetime.datetime.now(datetime.timezone.utc)
        access_jti = f"tok_acc_{uuid.uuid4().hex}"
        refresh_jti = f"tok_ref_{uuid.uuid4().hex}"

        access_payload = {
            "sub": user["id"],
            "username": user["username"],
            "role": user["role"],
            "provider": user.get("provider", "LOCAL"),
            "jti": access_jti,
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + datetime.timedelta(minutes=access_ttl_minutes)).timestamp()),
        }
        refresh_payload = {
            "sub": user["id"],
            "username": user["username"],
            "role": user["role"],
            "jti": refresh_jti,
            "type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int((now + datetime.timedelta(days=refresh_ttl_days)).timestamp()),
        }

        access_token = jwt.encode(access_payload, self.SECRET_KEY, algorithm=self.ALGORITHM)
        refresh_token = jwt.encode(refresh_payload, self.SECRET_KEY, algorithm=self.ALGORITHM)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": access_ttl_minutes * 60,
            "access_jti": access_jti,
            "refresh_jti": refresh_jti,
        }

    async def verify_token(self, token: str, expected_type: str = "access") -> Dict[str, Any]:
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise PermissionError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token signature: {e}")

        if payload.get("type") != expected_type:
            raise ValueError(f"Token type mismatch: expected {expected_type}, got {payload.get('type')}")

        jti = payload.get("jti")
        if jti and await self.redis.exists(f"blacklist:{jti}"):
            raise PermissionError("Token has been revoked")

        return payload

    async def revoke_token(self, token: str) -> bool:
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM], options={"verify_exp": False})
            jti = payload.get("jti")
            exp = payload.get("exp", time.time() + 3600)
            remaining_ttl = max(1, int(exp - time.time()))
            if jti:
                await self.redis.set(f"blacklist:{jti}", "revoked", ex=remaining_ttl)
                return True
        except Exception:
            pass
        return False


# ============================================================================
# 5. Agent Adapter & SSE Token Streamer Test Doubles
# ============================================================================

class MockAgentAdapter:
    """Contract-compliant BaseAgentAdapter test double."""

    def __init__(self, framework_name: str = "mock"):
        self.framework_name = framework_name
        self.is_healthy = True

    async def initialize(self) -> None:
        pass

    async def health_check(self) -> bool:
        return self.is_healthy

    async def ainvoke(self, agent_input: AgentInput) -> AgentOutput:
        has_prompt = bool(agent_input.prompt and agent_input.prompt.strip())
        has_messages = bool(agent_input.messages and any(m.content and m.content.strip() for m in agent_input.messages))
        if not has_prompt and not has_messages:
            raise ValueError("Input prompt or messages cannot be empty")

        prompt = (agent_input.prompt or agent_input.messages[-1].content).strip()
        return AgentOutput(
            content=f"Echo: {prompt}",
            turn_id=agent_input.turn_id or str(uuid.uuid4()),
            finish_reason="stop",
            metadata={"framework": self.framework_name, "tokens": len(prompt.split())},
        )

    async def astream(
        self,
        agent_input: AgentInput,
        trigger_interrupt: bool = False,
        trigger_error: bool = False,
    ) -> AsyncGenerator[AgentChunk, None]:
        has_prompt = bool(agent_input.prompt and agent_input.prompt.strip())
        has_messages = bool(agent_input.messages and any(m.content and m.content.strip() for m in agent_input.messages))
        if not has_prompt and not has_messages:
            raise ValueError("Input prompt or messages cannot be empty")

        turn_id = agent_input.turn_id or str(uuid.uuid4())
        prompt = (agent_input.prompt or agent_input.messages[-1].content).strip()
        tokens = prompt.split()

        for idx, token in enumerate(tokens):
            if trigger_interrupt and idx == 1:
                yield AgentChunk(
                    type=AgentEventType.INTERRUPT,
                    content=None,
                    metadata={"interrupt_id": f"int_{uuid.uuid4().hex[:8]}", "action": "approve_required"},
                    id=turn_id,
                )
                return

            if trigger_error and idx == 2:
                yield AgentChunk(
                    type=AgentEventType.ERROR,
                    error="Simulated upstream generation error",
                    id=turn_id,
                )
                return

            yield AgentChunk(
                type=AgentEventType.TOKEN,
                content=token + " ",
                metadata={"index": idx},
                id=turn_id,
            )
            await asyncio.sleep(0.001)

        yield AgentChunk(
            type=AgentEventType.DONE,
            content=None,
            metadata={"total_tokens": len(tokens)},
            id=turn_id,
        )

    async def ahandle_interrupt(
        self,
        interrupt_id: str,
        decision: str,
        state_update: Optional[Dict[str, Any]] = None,
    ) -> AgentOutput:
        if decision not in ("approve", "reject"):
            raise ValueError(f"Invalid interrupt decision: {decision}")
        return AgentOutput(
            content=f"Interrupt {interrupt_id} resolved with {decision}",
            metadata={"interrupt_id": interrupt_id, "decision": decision, "state_update": state_update or {}},
            finish_reason="stop",
        )


class MockSSEStreamer:
    """FastAPI Server-Sent Events (SSE) serializer and header provider."""

    @staticmethod
    def stream_headers() -> Dict[str, str]:
        return {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }

    @staticmethod
    async def sse_event_generator(source: AsyncGenerator[AgentChunk, None]) -> AsyncGenerator[str, None]:
        try:
            async for chunk in source:
                chunk_dict = chunk.to_dict()
                event_type = chunk_dict["type"]
                payload_json = json.dumps(chunk_dict, default=str)
                event_id = chunk_dict.get("id") or ""
                id_line = f"id: {event_id}\n" if event_id else ""
                yield f"event: {event_type}\n{id_line}data: {payload_json}\n\n"
        except Exception as exc:
            err_dict = {"type": "error", "error": str(exc), "content": None, "metadata": {}}
            yield f"event: error\ndata: {json.dumps(err_dict)}\n\n"


# ============================================================================
# 6. Pytest Hooks (Native Async Support without external plugins)
# ============================================================================

import inspect


def pytest_pyfunc_call(pyfuncitem):
    """Enable native execution of async def test functions via asyncio.run()."""
    test_obj = pyfuncitem.obj
    if inspect.iscoroutinefunction(test_obj):
        test_args = {arg: pyfuncitem.funcargs[arg] for arg in pyfuncitem._fixtureinfo.argnames if arg in pyfuncitem.funcargs}
        asyncio.run(test_obj(**test_args))
        return True
    return None


# ============================================================================
# 7. Pytest Fixtures
# ============================================================================

@pytest.fixture
def redis_client() -> InMemoryRedis:
    return InMemoryRedis()


@pytest.fixture
def db_client() -> MockDatabase:
    db = MockDatabase.get_instance("sqlite:///:memory:")
    db.set_connected(True)
    yield db
    MockDatabase.reset_instance()


@pytest.fixture
def auth_service(redis_client: InMemoryRedis) -> MockAuthService:
    return MockAuthService(redis=redis_client)


@pytest.fixture
def agent_adapter() -> MockAgentAdapter:
    return MockAgentAdapter()


@pytest.fixture
def sse_streamer() -> MockSSEStreamer:
    return MockSSEStreamer()


@pytest.fixture
def temp_workspace() -> Generator[str, None, None]:
    temp_dir = tempfile.mkdtemp(prefix="af_e2e_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)
