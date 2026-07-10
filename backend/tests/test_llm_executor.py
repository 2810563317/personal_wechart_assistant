import asyncio

from app.executors.llm_executor import LLMExecutor
from app.services.agent_context import AgentContext
from app.services.planner_service import PlanStep, PlanStepType


class FakePromptService:
    def __init__(self) -> None:
        self.received_args: tuple[
            str,
            list[dict[str, str]],
            str | None,
            list[dict[str, str]],
        ] | None = None

    def build_messages(
        self,
        message: str,
        recent_messages: list[dict[str, str]],
        tool_result: str | None = None,
        long_term_facts: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        facts = long_term_facts or []
        self.received_args = (message, recent_messages, tool_result, facts)
        return [
            {"role": "system", "content": "system"},
            *recent_messages,
            {"role": "user", "content": message},
        ]


class FakeModelService:
    async def generate_reply(self, messages: list[dict[str, str]]) -> str:
        return f"reply with {len(messages)} messages"


def test_llm_executor_writes_messages_and_reply_to_agent_context(monkeypatch) -> None:
    fake_prompt_service = FakePromptService()
    monkeypatch.setattr("app.executors.llm_executor.prompt_service", fake_prompt_service)
    monkeypatch.setattr("app.executors.llm_executor.model_service", FakeModelService())
    context = AgentContext(session_id="user-a", user_input="我叫什么名字？")
    context.recent_messages = [
        {"role": "user", "content": "我叫 Zita"},
        {"role": "assistant", "content": "好的，我记住了。"},
    ]
    context.long_term_facts = [
        {
            "key": "name",
            "value": "Zita",
            "reason": "用户明确说明自己的名字",
        }
    ]
    step = PlanStep(PlanStepType.LLM)

    asyncio.run(LLMExecutor().execute(step, context))

    assert fake_prompt_service.received_args is not None
    assert fake_prompt_service.received_args[0] == "我叫什么名字？"
    assert fake_prompt_service.received_args[2] is None
    assert context.messages == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "我叫 Zita"},
        {"role": "assistant", "content": "好的，我记住了。"},
        {"role": "user", "content": "我叫什么名字？"},
    ]
    assert context.final_reply == "reply with 4 messages"
    assert len(context.step_results) == 1
    assert context.step_results[0].step_type == PlanStepType.LLM
    assert context.step_results[0].success is True
    assert context.step_results[0].detail == "Generated LLM reply"


def test_llm_executor_uses_latest_tool_result_as_prompt_context(monkeypatch) -> None:
    fake_prompt_service = FakePromptService()
    monkeypatch.setattr("app.executors.llm_executor.prompt_service", fake_prompt_service)
    monkeypatch.setattr("app.executors.llm_executor.model_service", FakeModelService())
    context = AgentContext(session_id="user-a", user_input="北京气温多少")
    context.tool_results = [
        {
            "tool_name": "weather",
            "content": "北京当前晴，气温 30℃。",
            "success": True,
        }
    ]
    step = PlanStep(PlanStepType.LLM)

    asyncio.run(LLMExecutor().execute(step, context))

    assert fake_prompt_service.received_args is not None
    assert fake_prompt_service.received_args[2] == "北京当前晴，气温 30℃。"
    assert context.final_reply == "reply with 2 messages"
