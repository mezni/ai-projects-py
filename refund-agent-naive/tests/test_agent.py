from decimal import Decimal

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from resolve_agent.agent.factory import build_agent
from resolve_agent.context import AgentContext
from resolve_agent.prompts import load_prompt


class ScriptedModel(GenericFakeChatModel):
    """Replays a fixed list of AI messages and tolerates bind_tools()."""

    def bind_tools(self, tools, **kwargs):
        return self


def call(name: str, args: dict, call_id: str = "1") -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


def run(service, script, customer="c1"):
    agent = build_agent(ScriptedModel(messages=iter(script)), service, InMemorySaver())
    return agent.invoke(
        {"messages": [{"role": "user", "content": "refund please"}]},
        {"configurable": {"thread_id": "t"}},
        context=AgentContext(customer_id=customer),
    )


def test_prompt_loads():
    assert "refund requests only" in load_prompt("refund_agent.v1")


def test_happy_path_issues_refund(service, orders):
    run(
        service,
        [
            call("issue_refund", {"order_id": "A1001", "amount": "20.00", "reason": "defective"}),
            AIMessage(content="Done, 20.00 refunded."),
        ],
    )
    assert orders.get_for_customer("A1001", "c1").refunded is True


def test_model_cannot_refund_another_customers_order(service, orders):
    run(
        service,
        [
            call("issue_refund", {"order_id": "B2001", "amount": "10.00", "reason": "other"}),
            AIMessage(content="I could not find that order."),
        ],
    )
    assert orders.get_for_customer("B2001", "c2").refunded is False


def test_invalid_amount_does_not_crash_and_issues_nothing(service, orders):
    result = run(
        service,
        [
            call("issue_refund", {"order_id": "A1001", "amount": "20.999", "reason": "defective"}),
            AIMessage(content="Sorry, let me fix that."),
        ],
    )
    assert orders.get_for_customer("A1001", "c1").refunded is False
    assert result["messages"][-1].content == "Sorry, let me fix that."
