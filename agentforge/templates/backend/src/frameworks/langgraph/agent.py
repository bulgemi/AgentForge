"""LangGraph StateGraph custom agent implementation with real LLM provider streaming."""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import sys
from typing import Annotated, Any, AsyncGenerator, List, Optional, TypedDict

# Ensure langfuse.callback points to langfuse.langchain for backwards compatibility
try:
    import langfuse
    if not hasattr(langfuse, "callback"):
        try:
            import langfuse.langchain
            sys.modules.setdefault("langfuse.callback", langfuse.langchain)
            setattr(langfuse, "callback", langfuse.langchain)
        except (ImportError, ModuleNotFoundError):
            pass
except (ImportError, ModuleNotFoundError):
    pass

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

try:
    from ....core.adapter import (
        AgentChunk,
        AgentEventType,
        AgentInput,
        AgentMessage,
        AgentOutput,
        AgentRole,
        BaseAgentAdapter,
    )
except (ImportError, ValueError):
    try:
        from src.core.adapter import (
            AgentChunk,
            AgentEventType,
            AgentInput,
            AgentMessage,
            AgentOutput,
            AgentRole,
            BaseAgentAdapter,
        )
    except (ImportError, ValueError):
        from agentforge.core.adapter import (
            AgentChunk,
            AgentEventType,
            AgentInput,
            AgentMessage,
            AgentOutput,
            AgentRole,
            BaseAgentAdapter,
        )

try:
    from ....core.config import get_settings
except (ImportError, ValueError):
    try:
        from ...core.config import get_settings
    except (ImportError, ValueError):
        try:
            from src.core.config import get_settings
        except (ImportError, ValueError):
            from agentforge.core.config import get_settings

logger = logging.getLogger(__name__)


PROVIDER_CREDENTIAL_HINTS = {
    "anthropic": "ANTHROPIC_API_KEY (또는 CLAUDE_API_KEY)",
    "claude": "ANTHROPIC_API_KEY (또는 CLAUDE_API_KEY)",
    "openai": "OPENAI_API_KEY",
    "gpt": "OPENAI_API_KEY",
    "gemini": "GOOGLE_API_KEY (또는 GEMINI_API_KEY)",
    "google": "GOOGLE_API_KEY (또는 GEMINI_API_KEY)",
    "bedrock": "AWS_ACCESS_KEY_ID 및 AWS_SECRET_ACCESS_KEY (또는 AWS IAM Role)",
    "aws": "AWS_ACCESS_KEY_ID 및 AWS_SECRET_ACCESS_KEY (또는 AWS IAM Role)",
    "aws-bedrock": "AWS_ACCESS_KEY_ID 및 AWS_SECRET_ACCESS_KEY (또는 AWS IAM Role)",
}


class AgentState(TypedDict):
    """LangGraph conversation state."""
    messages: Annotated[list[BaseMessage], add_messages]


class ProjectAgentAdapter(BaseAgentAdapter):
    """Production LangGraph agent adapter connecting real LLM providers."""

    def __init__(self, name: str = "{{ project_name }}", **kwargs: Any) -> None:
        super().__init__(name=name, **kwargs)
        self.name = name

    def _get_langfuse_callback(self, input_data: AgentInput) -> Optional[Any]:
        """Initialize Langfuse CallbackHandler if enabled and credentials are present.

        Returns:
            CallbackHandler instance if enabled and configured, otherwise None.
        """
        try:
            settings = get_settings()
        except Exception as e:
            logger.debug("Failed to retrieve settings for Langfuse callback: %s", e)
            return None

        if not getattr(settings, "langfuse_enabled", False):
            return None

        public_key = getattr(settings, "langfuse_public_key", None)
        secret_key = getattr(settings, "langfuse_secret_key", None)
        if not (public_key and str(public_key).strip() and secret_key and str(secret_key).strip()):
            return None

        public_key = str(public_key).strip()
        secret_key = str(secret_key).strip()
        raw_host = (
            getattr(settings, "langfuse_base_url", None)
            or getattr(settings, "langfuse_host", None)
            or "http://localhost:3000"
        )
        host = str(raw_host).strip().rstrip("/") if raw_host else "http://localhost:3000"
        raw_uid = getattr(input_data, "user_id", None) if input_data else None
        user_id = str(raw_uid).strip() if raw_uid and str(raw_uid).strip() else None

        raw_sid = getattr(input_data, "session_id", None) if input_data else None
        raw_cid = getattr(input_data, "chat_id", None) if input_data else None
        session_id = None
        if raw_sid and str(raw_sid).strip():
            session_id = str(raw_sid).strip()
        elif raw_cid and str(raw_cid).strip():
            session_id = str(raw_cid).strip()
        tags = [self.name, "agentforge"]

        cb_cls = None
        try:
            from langfuse.callback import CallbackHandler as _CB
            cb_cls = _CB
        except (ImportError, ModuleNotFoundError):
            try:
                from langfuse.langchain import CallbackHandler as _CB
                cb_cls = _CB
                import sys
                sys.modules.setdefault("langfuse.callback", sys.modules.get("langfuse.langchain"))
            except (ImportError, ModuleNotFoundError):
                cb_cls = None

        if cb_cls is None:
            logger.debug("Langfuse callback package is not installed or available.")
            return None

        # Synchronize environment variables for Langfuse SDK
        if host:
            os.environ["LANGFUSE_HOST"] = host
            os.environ["LANGFUSE_BASE_URL"] = host
        if public_key:
            os.environ["LANGFUSE_PUBLIC_KEY"] = public_key
        if secret_key:
            os.environ["LANGFUSE_SECRET_KEY"] = secret_key

        # In Langfuse v4+, register the client singleton in LangfuseResourceManager
        # so CallbackHandler resolves to an active, enabled client.
        try:
            from langfuse import Langfuse
            Langfuse(public_key=public_key, secret_key=secret_key, host=host)
        except Exception as lf_init_err:
            logger.debug("Langfuse client pre-initialization notice: %s", lf_init_err)

        try:
            try:
                # Langfuse v2/v3 CallbackHandler constructor signature
                kwargs: dict[str, Any] = {
                    "public_key": public_key,
                    "secret_key": secret_key,
                    "host": host,
                }
                if user_id:
                    kwargs["user_id"] = str(user_id)
                if session_id:
                    kwargs["session_id"] = str(session_id)
                if tags:
                    kwargs["tags"] = tags
                handler = cb_cls(**kwargs)
            except TypeError:
                # Langfuse v4+ CallbackHandler constructor signature
                try:
                    handler = cb_cls(public_key=public_key)
                except TypeError:
                    handler = cb_cls()

            if handler is not None:
                # Guarantee attribute consistency across Langfuse versions
                if user_id is not None and getattr(handler, "user_id", None) is None:
                    try:
                        setattr(handler, "user_id", str(user_id))
                    except Exception:
                        pass
                if session_id is not None and getattr(handler, "session_id", None) is None:
                    try:
                        setattr(handler, "session_id", str(session_id))
                    except Exception:
                        pass
                if host is not None and getattr(handler, "host", None) is None:
                    try:
                        setattr(handler, "host", str(host))
                    except Exception:
                        pass
                if tags is not None and getattr(handler, "tags", None) is None:
                    try:
                        setattr(handler, "tags", tags)
                    except Exception:
                        pass

                if not hasattr(handler, "flush") or not callable(getattr(handler, "flush", None)):
                    client = getattr(handler, "_langfuse_client", None)
                    if client and hasattr(client, "flush") and callable(client.flush):
                        handler.flush = client.flush

            return handler
        except Exception as e:
            logger.warning("Failed to initialize Langfuse CallbackHandler: %s", e)
            return None

    def _init_llm(self) -> Any:
        """Initialize LLM based on environment variables."""
        provider = os.getenv("LLM_PROVIDER", "anthropic").lower().strip()

        # 1. Anthropic Claude
        if provider in ("anthropic", "claude"):
            api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
            if not api_key or api_key.startswith("sk-placeholder") or len(api_key.strip()) < 10:
                logger.warning("Anthropic API key is not configured or is a placeholder.")
                return None
            model_name = os.getenv("CLAUDE_MODEL_NAME", "claude-haiku-4-5-20251001")
            try:
                from langchain_anthropic import ChatAnthropic
                return ChatAnthropic(
                    api_key=api_key,
                    model=model_name,
                    streaming=True,
                    max_tokens=2048,
                )
            except Exception as e:
                logger.error("Failed to initialize ChatAnthropic: %s", e)
                return None

        # 2. OpenAI
        elif provider in ("openai", "gpt"):
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key or api_key.startswith("sk-placeholder") or len(api_key.strip()) < 10:
                logger.warning("OpenAI API key is not configured.")
                return None
            model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")
            try:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    api_key=api_key,
                    model=model_name,
                    streaming=True,
                )
            except Exception as e:
                logger.error("Failed to initialize ChatOpenAI: %s", e)
                return None

        # 3. Google Gemini
        elif provider in ("gemini", "google"):
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key or api_key.startswith("your_") or len(api_key.strip()) < 10:
                logger.warning("Google API key is not configured.")
                return None
            model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(
                    google_api_key=api_key,
                    model=model_name,
                    streaming=True,
                )
            except Exception as e:
                logger.error("Failed to initialize ChatGoogleGenerativeAI: %s", e)
                return None

        # 4. AWS Bedrock
        elif provider in ("bedrock", "aws", "aws-bedrock"):
            model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")
            region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "ap-northeast-2")
            aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            aws_session_token = os.getenv("AWS_SESSION_TOKEN")

            if not aws_access_key and not os.path.exists(os.path.expanduser("~/.aws/credentials")):
                logger.warning("AWS credentials not found for Bedrock.")
                return None

            try:
                from langchain_aws import ChatBedrockConverse
                kwargs: dict[str, Any] = {
                    "model": model_id,
                    "region_name": region,
                    "streaming": True,
                }
                if aws_access_key and aws_secret_key:
                    kwargs["aws_access_key_id"] = aws_access_key
                    kwargs["aws_secret_access_key"] = aws_secret_key
                    if aws_session_token:
                        kwargs["aws_session_token"] = aws_session_token
                return ChatBedrockConverse(**kwargs)
            except Exception as e:
                logger.error("Failed to initialize ChatBedrockConverse: %s", e)
                return None

        logger.warning("Unsupported or unconfigured LLM provider: %s", provider)
        return None

    def _build_graph(self, llm: Any) -> Any:
        """Compile a LangGraph StateGraph with the LLM node."""
        workflow = StateGraph(AgentState)

        system_prompt = (
            f"You are {self.name}, an intelligent AI assistant built with AgentForge Clean Architecture. "
            "Please respond helpfully, politely, accurately, and naturally in the user's language."
        )

        async def agent_node(state: AgentState) -> dict[str, Any]:
            messages = state["messages"]
            if not messages or not isinstance(messages[0], SystemMessage):
                prompt_messages = [SystemMessage(content=system_prompt)] + list(messages)
            else:
                prompt_messages = list(messages)
            response = await llm.ainvoke(prompt_messages)
            return {"messages": [response]}

        workflow.add_node("agent", agent_node)
        workflow.add_edge(START, "agent")
        workflow.add_edge("agent", END)
        return workflow.compile()

    @staticmethod
    def _extract_text_content(content: Any) -> str:
        """Safely extract plain text string from str, list of content blocks, or dict payloads."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    if item.get("type") == "text" and "text" in item:
                        parts.append(str(item["text"]))
                    elif "text" in item:
                        parts.append(str(item["text"]))
            return "".join(parts) if parts else str(content)
        if content is None:
            return ""
        return str(content)

    def _prepare_messages(self, input_data: Optional[AgentInput]) -> list[BaseMessage]:
        """Convert input messages or prompt to LangChain BaseMessage list."""
        lc_messages: list[BaseMessage] = []
        if not input_data:
            return lc_messages
        if input_data.messages:
            for msg in input_data.messages:
                role = getattr(msg, "role", "user")
                role_val = role.value if hasattr(role, "value") else str(role)
                if role_val in ("user", "human"):
                    lc_messages.append(HumanMessage(content=msg.content))
                elif role_val in ("assistant", "ai"):
                    lc_messages.append(AIMessage(content=msg.content))
                elif role_val == "system":
                    lc_messages.append(SystemMessage(content=msg.content))
        else:
            prompt = input_data.get_prompt_or_last_message() if hasattr(input_data, "get_prompt_or_last_message") else getattr(input_data, "prompt", "")
            if prompt:
                lc_messages.append(HumanMessage(content=prompt))
        return lc_messages

    def _build_execution_config(self, input_data: Optional[AgentInput], handler: Optional[Any]) -> dict[str, Any]:
        """Safely prepare LangGraph execution configuration with callbacks, metadata, and tags."""
        execution_config: dict[str, Any] = {}
        try:
            raw_config = getattr(input_data, "config", None) if input_data else None
            if isinstance(raw_config, dict):
                execution_config = dict(raw_config)

            if handler is not None:
                raw_callbacks = execution_config.get("callbacks")
                if isinstance(raw_callbacks, list):
                    callbacks = list(raw_callbacks)
                elif isinstance(raw_callbacks, (tuple, set)):
                    callbacks = list(raw_callbacks)
                elif raw_callbacks is not None:
                    callbacks = [raw_callbacks]
                else:
                    callbacks = []

                if handler not in callbacks:
                    callbacks.append(handler)
                execution_config["callbacks"] = callbacks

                raw_meta = execution_config.get("metadata")
                metadata: dict[str, Any] = dict(raw_meta) if isinstance(raw_meta, dict) else {}
                raw_uid = getattr(input_data, "user_id", None) if input_data else None
                if raw_uid and str(raw_uid).strip():
                    metadata.setdefault("langfuse_user_id", str(raw_uid).strip())
                raw_sid = getattr(input_data, "session_id", None) if input_data else None
                raw_cid = getattr(input_data, "chat_id", None) if input_data else None
                if raw_sid and str(raw_sid).strip():
                    metadata.setdefault("langfuse_session_id", str(raw_sid).strip())
                elif raw_cid and str(raw_cid).strip():
                    metadata.setdefault("langfuse_session_id", str(raw_cid).strip())
                if self.name:
                    metadata.setdefault("langfuse_trace_name", self.name)
                if metadata:
                    execution_config["metadata"] = metadata

                raw_tags = execution_config.get("tags")
                if isinstance(raw_tags, list):
                    tags = list(raw_tags)
                elif isinstance(raw_tags, (tuple, set)):
                    tags = list(raw_tags)
                elif raw_tags is not None:
                    tags = [str(raw_tags)]
                else:
                    tags = []
                for t in [self.name, "agentforge"]:
                    if t and t not in tags:
                        tags.append(t)
                execution_config["tags"] = tags
        except Exception as err:
            logger.debug("Non-blocking error assembling execution config: %s", err)

        return execution_config

    async def ainvoke(self, input_data: AgentInput, context: Optional[Any] = None) -> AgentOutput:
        llm = self._init_llm()
        if not llm:
            provider = os.getenv("LLM_PROVIDER", "anthropic").lower().strip()
            req_cred = PROVIDER_CREDENTIAL_HINTS.get(provider, "API 키")
            return AgentOutput(
                content=(
                    f"[{self.name}] LLM Provider '{provider}'의 인증 정보가 설정되지 않았습니다. "
                    f"backend/.env 파일에 유효한 {req_cred}를 설정해주세요."
                )
            )

        graph = self._build_graph(llm)
        lc_messages = self._prepare_messages(input_data)
        handler = self._get_langfuse_callback(input_data)
        execution_config = self._build_execution_config(input_data, handler)

        try:
            res = await graph.ainvoke(
                {"messages": lc_messages},
                config=execution_config if execution_config else None,
            )
            out_messages = res.get("messages", [])
            raw_final = out_messages[-1].content if out_messages else ""
            final_content = self._extract_text_content(raw_final)
            return AgentOutput(content=final_content)
        except Exception as e:
            logger.error("LangGraph execution error: %s", e)
            return AgentOutput(content=f"Error executing agent: {e}")
        finally:
            if handler is not None:
                try:
                    if hasattr(handler, "flush") and callable(handler.flush):
                        res = handler.flush()
                        if inspect.isawaitable(res):
                            await res
                    elif hasattr(handler, "_langfuse_client") and hasattr(handler._langfuse_client, "flush") and callable(handler._langfuse_client.flush):
                        res = handler._langfuse_client.flush()
                        if inspect.isawaitable(res):
                            await res
                except Exception as flush_err:
                    logger.debug("Langfuse handler flush failed: %s", flush_err)

    async def astream(self, input_data: AgentInput, context: Optional[Any] = None) -> AsyncGenerator[AgentChunk, None]:
        llm = self._init_llm()
        if not llm:
            provider = os.getenv("LLM_PROVIDER", "anthropic").lower().strip()
            req_cred = PROVIDER_CREDENTIAL_HINTS.get(provider, "API 키")
            notice = (
                f"[{self.name}] LLM Provider '{provider}'의 인증 정보가 설정되지 않았습니다.\n\n"
                f"backend/.env 파일에 유효한 {req_cred}를 설정한 후 다시 시도해주세요."
            )
            for char in notice:
                yield AgentChunk(event=AgentEventType.TOKEN, data=char, content=char)
                await asyncio.sleep(0.01)
            yield AgentChunk(event=AgentEventType.DONE, data={"status": "fallback_no_credentials"})
            return

        graph = self._build_graph(llm)
        lc_messages = self._prepare_messages(input_data)
        handler = self._get_langfuse_callback(input_data)
        execution_config = self._build_execution_config(input_data, handler)

        try:
            async for chunk, meta in graph.astream(
                {"messages": lc_messages},
                config=execution_config if execution_config else None,
                stream_mode="messages",
            ):
                raw_content = getattr(chunk, "content", "")
                text_content = self._extract_text_content(raw_content)
                if text_content:
                    yield AgentChunk(event=AgentEventType.TOKEN, data=text_content, content=text_content)
            yield AgentChunk(event=AgentEventType.DONE, data={"status": "completed"})
        except Exception as e:
            logger.error("LangGraph streaming execution error: %s", e, exc_info=True)
            provider = os.getenv("LLM_PROVIDER", "anthropic").lower().strip()
            err_detail = str(e)
            if "API_KEY_INVALID" in err_detail or "Incorrect API key" in err_detail or "401" in err_detail:
                friendly_msg = f"\n\n[{provider.upper()} 인증 오류]: 설정된 API 키가 유효하지 않습니다. backend/.env의 API 키를 확인해주세요."
            elif "UnrecognizedClientException" in err_detail or "security token" in err_detail.lower():
                friendly_msg = f"\n\n[AWS Bedrock 인증 오류]: AWS 자격 증명(Access Key / Secret Key)이 유효하지 않습니다. backend/.env 설정을 확인해주세요."
            else:
                friendly_msg = f"\n\n[Agent Execution Error ({provider})]: {err_detail}"
            yield AgentChunk(event=AgentEventType.TOKEN, data=friendly_msg, content=friendly_msg)
            yield AgentChunk(event=AgentEventType.ERROR, error=str(e), data={"status": "error", "provider": provider})
        finally:
            if handler is not None:
                try:
                    if hasattr(handler, "flush") and callable(handler.flush):
                        res = handler.flush()
                        if inspect.isawaitable(res):
                            await res
                    elif hasattr(handler, "_langfuse_client") and hasattr(handler._langfuse_client, "flush") and callable(handler._langfuse_client.flush):
                        res = handler._langfuse_client.flush()
                        if inspect.isawaitable(res):
                            await res
                except Exception as flush_err:
                    logger.debug("Langfuse handler flush failed: %s", flush_err)

    async def ahandle_interrupt(
        self,
        interrupt_id: str,
        decision: str,
        state_update: Optional[dict[str, Any]] = None,
        context: Optional[Any] = None,
    ) -> AgentOutput:
        return AgentOutput(
            content=f"[LangGraph Agent: {self.name}] Resumed at {interrupt_id} with decision: '{decision}'",
            metadata={"resumed": True, "interrupt_id": interrupt_id, "decision": decision},
        )
