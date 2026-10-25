from dataclasses import dataclass
from typing import Any, Literal

from langchain.agents import create_agent
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    InterruptOnConfig,
    ToolCallRequest,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from refund_agent_simple.llm import get_llm
from refund_agent_simple.prompts import REFUND_SYSTEM_PROMPT
from refund_agent_simple.tools import (
    _policy_result,
    check_refund_policy,
    issue_refund,
    lookup_order,
)

ApprovalDecision = Literal["approve", "reject"]


@dataclass
class AgentResult:
    status: Literal["completed", "pending_approval"]
    message: str
    interrupt: Any | None = None


def _requires_approval(request: ToolCallRequest) -> bool:
    order_id = request.tool_call["args"].get("order_id", "")
    return bool(_policy_result(str(order_id)).get("requires_human_approval"))


class RefundAgent:
    def __init__(
        self,
        llm: BaseChatModel | None = None,
        tools: list | None = None,
        checkpointer: Any | None = None,
    ) -> None:
        self._agent = create_agent(
            model=llm or get_llm(),
            tools=(
                [lookup_order, check_refund_policy, issue_refund]
                if tools is None
                else tools
            ),
            system_prompt=REFUND_SYSTEM_PROMPT,
            middleware=[
                HumanInTheLoopMiddleware(
                    interrupt_on={
                        "issue_refund": InterruptOnConfig(
                            allowed_decisions=["approve", "reject"],
                            when=_requires_approval,
                        )
                    }
                )
            ],
            checkpointer=checkpointer or InMemorySaver(),
        )

    def ask(self, message: str, thread_id: str = "default") -> AgentResult:
        result = self._agent.invoke(
            {"messages": [HumanMessage(content=message)]},
            self._config(thread_id),
        )
        return self._to_result(result)

    def resume(
        self,
        decision: ApprovalDecision,
        thread_id: str = "default",
    ) -> AgentResult:
        result = self._agent.invoke(
            Command(resume={"decisions": [{"type": decision}]}),
            self._config(thread_id),
        )
        return self._to_result(result)

    @staticmethod
    def _config(thread_id: str) -> dict[str, Any]:
        return {"configurable": {"thread_id": thread_id}}

    @staticmethod
    def _to_result(result: dict[str, Any]) -> AgentResult:
        if interrupts := result.get("__interrupt__"):
            return AgentResult(
                status="pending_approval",
                message="This refund requires human approval.",
                interrupt=interrupts[0],
            )
        return AgentResult(
            status="completed",
            message=result["messages"][-1].text,
            interrupt=None,
        )
