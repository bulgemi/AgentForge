"""LangGraph StateGraph custom agent implementation with real LLM provider streaming."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Annotated, Any, AsyncGenerator, List, Optional, TypedDict

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
    from src.core.adapter import (
        AgentChunk,
        AgentEventType,
        AgentInput,
        AgentMessage,
        AgentOutput,
        AgentRole,
        BaseAgentAdapter,
    )

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """LangGraph conversation state."""
    messages: Annotated[list[BaseMessage], add_messages]


class ProjectAgentAdapter(BaseAgentAdapter):
    """Production LangGraph agent adapter connecting real LLM providers."""

    def __init__(self, name: str = "{{ project_name }}", **kwargs: Any) -> None:
        super().__init__(name=name, **kwargs)
        self.name = name

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
            if not api_key or len(api_key.strip()) < 10:
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

    def _prepare_messages(self, input_data: AgentInput) -> list[BaseMessage]:
        """Convert input messages or prompt to LangChain BaseMessage list."""
        lc_messages: list[BaseMessage] = []
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

    async def ainvoke(self, input_data: AgentInput, context: Optional[Any] = None) -> AgentOutput:
        llm = self._init_llm()
        if not llm:
            return AgentOutput(
                content=(
                    f"[{self.name}] LLM API 키가 설정되지 않았습니다. "
                    "backend/.env 파일에 유효한 API 키(ANTHROPIC_API_KEY, OPENAI_API_KEY 등)를 설정해주세요."
                )
            )

        graph = self._build_graph(llm)
        lc_messages = self._prepare_messages(input_data)
        try:
            res = await graph.ainvoke({"messages": lc_messages})
            out_messages = res.get("messages", [])
            final_content = out_messages[-1].content if out_messages else ""
            return AgentOutput(content=str(final_content))
        except Exception as e:
            logger.error("LangGraph execution error: %s", e)
            return AgentOutput(content=f"Error executing agent: {e}")

    async def astream(self, input_data: AgentInput, context: Optional[Any] = None) -> AsyncGenerator[AgentChunk, None]:
        llm = self._init_llm()
        if not llm:
            provider = os.getenv("LLM_PROVIDER", "anthropic")
            notice = (
                f"[{self.name}] LLM Provider '{provider}'의 API 키가 설정되지 않았습니다.\n\n"
                "backend/.env 파일에 유효한 API 키(예: ANTHROPIC_API_KEY)를 입력한 후 다시 시도해주세요."
            )
            for char in notice:
                yield AgentChunk(event=AgentEventType.TOKEN, data=char, content=char)
                await asyncio.sleep(0.01)
            yield AgentChunk(event=AgentEventType.DONE, data={"status": "fallback_no_api_key"})
            return

        graph = self._build_graph(llm)
        lc_messages = self._prepare_messages(input_data)

        try:
            async for chunk, meta in graph.astream({"messages": lc_messages}, stream_mode="messages"):
                content = getattr(chunk, "content", "")
                if content:
                    yield AgentChunk(event=AgentEventType.TOKEN, data=content, content=content)
            yield AgentChunk(event=AgentEventType.DONE, data={"status": "completed"})
        except Exception as e:
            logger.error("LangGraph streaming execution error: %s", e, exc_info=True)
            err_msg = f"\n\n[Agent Execution Error]: {str(e)}"
            yield AgentChunk(event=AgentEventType.TOKEN, data=err_msg, content=err_msg)
            yield AgentChunk(event=AgentEventType.ERROR, error=str(e), data={"status": "error"})

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
