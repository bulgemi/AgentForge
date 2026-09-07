"""AWS Bedrock enterprise agent implementation with real streaming."""

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
    """Custom AWS Bedrock Agent adapter using LangGraph and ChatBedrockConverse."""

    def __init__(self, name: str = "{{ project_name }}", **kwargs: Any) -> None:
        super().__init__(name=name, **kwargs)
        self.name = name

    def _init_llm(self) -> Any:
        """Initialize Bedrock Converse LLM from environment variables."""
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

    def _build_graph(self, llm: Any) -> Any:
        """Compile a LangGraph StateGraph with the Bedrock model node."""
        workflow = StateGraph(AgentState)

        system_prompt = (
            f"You are {self.name}, an AWS Bedrock-powered enterprise AI agent. "
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
                    f"[{self.name}] AWS Bedrock 자격 증명이 설정되지 않았습니다. "
                    "backend/.env 파일에 AWS_ACCESS_KEY_ID 및 AWS_SECRET_ACCESS_KEY를 설정해주세요."
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
            logger.error("Bedrock execution error: %s", e)
            return AgentOutput(content=f"Error executing agent: {e}")

    async def astream(self, input_data: AgentInput, context: Optional[Any] = None) -> AsyncGenerator[AgentChunk, None]:
        llm = self._init_llm()
        if not llm:
            notice = (
                f"[{self.name}] AWS Bedrock 인증 정보가 설정되지 않았습니다.\n\n"
                "backend/.env 파일에 유효한 AWS_ACCESS_KEY_ID 및 AWS_SECRET_ACCESS_KEY를 설정한 후 다시 시도해주세요."
            )
            for char in notice:
                yield AgentChunk(event=AgentEventType.TOKEN, data=char, content=char)
                await asyncio.sleep(0.01)
            yield AgentChunk(event=AgentEventType.DONE, data={"status": "fallback_no_credentials"})
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
            logger.error("Bedrock streaming execution error: %s", e, exc_info=True)
            err_detail = str(e)
            if "UnrecognizedClientException" in err_detail or "security token" in err_detail.lower():
                friendly_msg = "\n\n[AWS Bedrock 인증 오류]: AWS 자격 증명(Access Key / Secret Key)이 유효하지 않습니다. backend/.env 설정을 확인해주세요."
            else:
                friendly_msg = f"\n\n[Bedrock Execution Error]: {err_detail}"
            yield AgentChunk(event=AgentEventType.TOKEN, data=friendly_msg, content=friendly_msg)
            yield AgentChunk(event=AgentEventType.ERROR, error=str(e), data={"status": "error", "provider": "bedrock"})

    async def ahandle_interrupt(
        self,
        interrupt_id: str,
        decision: str,
        state_update: Optional[dict[str, Any]] = None,
        context: Optional[Any] = None,
    ) -> AgentOutput:
        return AgentOutput(
            content=f"[Bedrock: {self.name}] Resumed at {interrupt_id} with decision: '{decision}'",
            metadata={"resumed": True, "interrupt_id": interrupt_id, "decision": decision},
        )
