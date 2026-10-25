from typing import Any, ClassVar

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from refund_agent_simple.agent import RefundAgent
from refund_agent_simple.tools import REFUNDS


class CapturingChatModel(FakeListChatModel):
    captured: ClassVar[list[list[BaseMessage]]] = []
    bound_tools: ClassVar[list[Any]] = []

    def bind_tools(self, tools: Any, **kwargs: Any) -> "CapturingChatModel":
        self.bound_tools.extend(tools)
        return self

    def _call(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> str:
        self.captured.append(messages)
        return super()._call(messages, stop, run_manager, **kwargs)


class ScriptedChatModel(CapturingChatModel):
    script: ClassVar[list[AIMessage]] = []
    index: int = 0

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.captured.append(messages)
        message = self.script[self.index % len(self.script)]
        self.index += 1
        return ChatResult(generations=[ChatGeneration(message=message)])


@pytest.fixture(autouse=True)
def reset_state():
    CapturingChatModel.captured.clear()
    CapturingChatModel.bound_tools.clear()
    ScriptedChatModel.script = []
    REFUNDS.clear()
    yield
    REFUNDS.clear()


def test_agent_returns_model_response():
    llm = CapturingChatModel(responses=["Please share your order ID."])
    agent = RefundAgent(llm=llm)

    result = agent.ask("I want a refund.")

    assert result.status == "completed"
    assert result.message == "Please share your order ID."


def test_agent_passes_customer_message_to_model():
    llm = CapturingChatModel(responses=["ok"])
    agent = RefundAgent(llm=llm)

    agent.ask("Refund order 42")

    messages = llm.captured[0]
    assert messages[-1].content == "Refund order 42"


def test_agent_has_default_tools():
    llm = CapturingChatModel(responses=["ok"])
    agent = RefundAgent(llm=llm)

    agent.ask("Refund order 42")

    names = {tool.name for tool in llm.bound_tools}
    assert names == {"lookup_order", "check_refund_policy", "issue_refund"}


def test_agent_accepts_custom_tools():
    llm = CapturingChatModel(responses=["ok"])
    agent = RefundAgent(llm=llm, tools=[])

    agent.ask("Refund order 42")

    assert llm.bound_tools == []


def test_high_value_refund_pauses_for_approval():
    ScriptedChatModel.script = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "issue_refund",
                    "args": {"order_id": "4824", "reason": "Changed my mind."},
                    "id": "call_1",
                }
            ],
        ),
        AIMessage(content="Your refund was processed."),
    ]
    llm = ScriptedChatModel(responses=[])
    agent = RefundAgent(llm=llm)

    result = agent.ask("Refund order 4824", thread_id="approval")

    assert result.status == "pending_approval"
    assert result.interrupt is not None
    assert "4824" not in REFUNDS


def test_approved_refund_is_processed():
    ScriptedChatModel.script = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "issue_refund",
                    "args": {"order_id": "4824", "reason": "Changed my mind."},
                    "id": "call_1",
                }
            ],
        ),
        AIMessage(content="Your refund was processed."),
    ]
    llm = ScriptedChatModel(responses=[])
    agent = RefundAgent(llm=llm)

    agent.ask("Refund order 4824", thread_id="approve")
    result = agent.resume("approve", thread_id="approve")

    assert result.status == "completed"
    assert result.message == "Your refund was processed."
    assert REFUNDS["4824"]["status"] == "refunded"


def test_rejected_refund_is_not_processed():
    ScriptedChatModel.script = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "issue_refund",
                    "args": {"order_id": "4824", "reason": "Changed my mind."},
                    "id": "call_1",
                }
            ],
        ),
        AIMessage(content="The refund was rejected."),
    ]
    llm = ScriptedChatModel(responses=[])
    agent = RefundAgent(llm=llm)

    agent.ask("Refund order 4824", thread_id="reject")
    result = agent.resume("reject", thread_id="reject")

    assert result.status == "completed"
    assert "4824" not in REFUNDS
