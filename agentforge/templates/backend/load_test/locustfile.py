"""Locust Load Testing Suite for AgentForge Backend.

Scenario:
  1. Login (ID/PW -> Bearer Token)
  2. Create Conversation Session
  3. Sequentially ask 5 questions over SSE streaming
     - Measure Time to First Token (TTFT)
     - Measure Total Streaming Latency
  4. Logout & Invalidate Session
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any

from locust import HttpUser, SequentialTaskSet, between, events, task

logger = logging.getLogger("agentforge.loadtest")

# Configuration defaults with environment variable overrides
DEFAULT_USERNAME = os.getenv("LOAD_TEST_USER", "admin")
DEFAULT_PASSWORD = os.getenv("LOAD_TEST_PASSWORD", "admin1234!")
QUESTIONS_FILE_PATH = os.getenv(
    "LOAD_TEST_QUESTIONS_FILE",
    str(Path(__file__).resolve().parent / "questions.json"),
)


def load_questions() -> list[dict[str, Any]]:
    """Load Q&A questions from questions.json or provide standard fallbacks."""
    q_path = Path(QUESTIONS_FILE_PATH)
    if q_path.exists():
        try:
            with open(q_path, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception as e:
            logger.warning("Failed to load questions from %s: %s", q_path, e)

    return [
        {"id": 1, "question": "AgentForge의 아키텍처와 주요 컴포넌트에 대해 설명해주세요."},
        {"id": 2, "question": "Clean Architecture 계층 분리와 책임에 대해 알려주세요."},
        {"id": 3, "question": "FastAPI SSE 스트리밍 처리 과정과 어댑터 연동 방식을 설명해주세요."},
        {"id": 4, "question": "JWT 인증 및 Redis 세션 관리 구조를 설명해주세요."},
        {"id": 5, "question": "OpenSearch 및 Langfuse 관측성 연동은 어떻게 동작하나요?"},
    ]


SCENARIO_QUESTIONS = load_questions()


class AgentForgeUserWorkflow(SequentialTaskSet):
    """Sequential workflow simulating realistic user session lifecycle."""

    def on_start(self) -> None:
        """Initialize user state and unique session identifiers."""
        self.session_id = str(uuid.uuid4())
        self.token: str | None = None
        self.chat_id: str | None = None
        self.auth_headers: dict[str, str] = {}

    @task
    def task_1_login(self) -> None:
        """Step 1: Authenticate with username and password to obtain JWT token."""
        login_payload = {
            "username": DEFAULT_USERNAME,
            "password": DEFAULT_PASSWORD,
            "auth_type": "id_pw",
        }

        with self.client.post(
            "/api/v1/auth/login",
            json=login_payload,
            catch_response=True,
            name="/api/v1/auth/login",
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.token = data.get("access_token")
                    if self.token:
                        self.auth_headers = {
                            "Authorization": f"Bearer {self.token}",
                            "Content-Type": "application/json",
                        }
                        response.success()
                        return
                    else:
                        response.failure("Missing access_token in login response")
                except Exception as e:
                    response.failure(f"JSON decode failed: {e}")
            else:
                response.failure(f"Login failed with HTTP {response.status_code}: {response.text}")

        # If login failed, interrupt flow
        self.interrupt()

    @task
    def task_2_create_chat(self) -> None:
        """Step 2: Create a dedicated chat conversation thread."""
        if not self.token:
            self.interrupt()
            return

        payload = {"title": f"LoadTest-{self.session_id[:8]}"}

        with self.client.post(
            "/api/v1/chats",
            json=payload,
            headers=self.auth_headers,
            catch_response=True,
            name="/api/v1/chats [Create]",
        ) as response:
            if response.status_code == 201:
                try:
                    data = response.json()
                    self.chat_id = data.get("id")
                    if self.chat_id:
                        response.success()
                        return
                    else:
                        response.failure("Missing chat id in response")
                except Exception as e:
                    response.failure(f"JSON decode error: {e}")
            else:
                response.failure(f"Create chat failed with HTTP {response.status_code}: {response.text}")

        self.interrupt()

    @task
    def task_3_chat_dialogue_5_turns(self) -> None:
        """Step 3: Sequentially submit 5 questions and stream SSE token chunks.
        
        Measures:
          - TTFT (Time To First Token) in ms
          - Total Streaming Completion Latency in ms
        """
        if not self.chat_id or not self.token:
            self.interrupt()
            return

        for idx, item in enumerate(SCENARIO_QUESTIONS[:5], start=1):
            question_text = item.get("question", "")
            payload = {
                "message": question_text,
                "session_id": self.chat_id,
            }

            req_start_time = time.time()
            first_token_time: float | None = None
            total_bytes = 0
            chunk_count = 0
            is_success = False
            error_message = ""

            try:
                with self.client.post(
                    f"/api/v1/chats/{self.chat_id}/stream",
                    json=payload,
                    headers=self.auth_headers,
                    stream=True,
                    catch_response=True,
                    name=f"/api/v1/chats/stream [Q{idx}]",
                ) as response:
                    if response.status_code == 200:
                        # Iterate raw SSE stream lines
                        for line in response.iter_lines():
                            if not line:
                                continue
                            if first_token_time is None:
                                first_token_time = time.time()
                            chunk_count += 1
                            total_bytes += len(line)

                        is_success = True
                        response.success()
                    else:
                        error_message = f"HTTP {response.status_code}: {response.text}"
                        response.failure(error_message)

            except Exception as e:
                error_message = str(e)
                logger.error("SSE stream request error on Q%d: %s", idx, e)

            finish_time = time.time()
            total_duration_ms = (finish_time - req_start_time) * 1000

            # Record custom metrics
            if is_success and first_token_time is not None:
                ttft_ms = (first_token_time - req_start_time) * 1000
                events.request.fire(
                    request_type="SSE_TTFT",
                    name=f"/api/v1/chats/stream [TTFT - Q{idx}]",
                    response_time=ttft_ms,
                    response_length=0,
                    context={},
                    exception=None,
                )
            elif not is_success:
                events.request.fire(
                    request_type="SSE_TTFT",
                    name=f"/api/v1/chats/stream [TTFT - Q{idx}]",
                    response_time=0,
                    response_length=0,
                    context={},
                    exception=Exception(error_message or "Stream failed"),
                )

            # Record Total Streaming Latency
            events.request.fire(
                request_type="SSE_TOTAL",
                name=f"/api/v1/chats/stream [Total - Q{idx}]",
                response_time=total_duration_ms,
                response_length=total_bytes,
                context={},
                exception=None if is_success else Exception(error_message or "Stream failed"),
            )

            # Realistic reading pause between conversation turns
            time.sleep(1.0)

    @task
    def task_4_logout(self) -> None:
        """Step 4: Explicitly logout and terminate authenticated session."""
        if not self.token:
            self.interrupt()
            return

        with self.client.post(
            "/api/v1/auth/logout",
            headers=self.auth_headers,
            catch_response=True,
            name="/api/v1/auth/logout",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Logout failed with HTTP {response.status_code}: {response.text}")

        # Complete scenario lifecycle for this virtual user iteration
        self.interrupt()


class AgentForgeUser(HttpUser):
    """Simulated user executing sequential AgentForge conversational workflows."""

    tasks = [AgentForgeUserWorkflow]
    wait_time = between(1.0, 3.0)
    host = os.getenv("LOAD_TEST_HOST", "http://localhost:8000")
