import asyncio

from app.executors.memory_executor import MemoryExecutor
from app.services.agent_context import AgentContext
from app.services.planner_service import PlanStep, PlanStepType


class FakeMemoryService:
    def get_recent_messages(self, session_id: str) -> list[dict[str, str]]:
        return [
            {"role": "user", "content": f"{session_id} 上一轮用户消息"},
            {"role": "assistant", "content": "上一轮助手回复"},
        ]

    def get_long_term_facts(self, session_id: str) -> list[dict[str, str]]:
        return [
            {
                "key": "name",
                "value": "Zita",
                "reason": f"{session_id} 的长期事实",
            }
        ]


def test_memory_executor_loads_short_term_memory(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.executors.memory_executor.memory_service",
        FakeMemoryService(),
    )
    context = AgentContext(session_id="user-a", user_input="你好")
    step = PlanStep(PlanStepType.MEMORY, "short_term")

    asyncio.run(MemoryExecutor().execute(step, context))

    assert context.recent_messages == [
        {"role": "user", "content": "user-a 上一轮用户消息"},
        {"role": "assistant", "content": "上一轮助手回复"},
    ]
    assert context.long_term_facts == []
    assert len(context.step_results) == 1
    assert context.step_results[0].step_type == PlanStepType.MEMORY
    assert context.step_results[0].step_name == "short_term"
    assert context.step_results[0].success is True
    assert context.step_results[0].detail == "Loaded short-term memory"


def test_memory_executor_loads_long_term_memory(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.executors.memory_executor.memory_service",
        FakeMemoryService(),
    )
    context = AgentContext(session_id="user-a", user_input="我叫什么名字？")
    step = PlanStep(PlanStepType.MEMORY, "long_term")

    asyncio.run(MemoryExecutor().execute(step, context))

    assert context.recent_messages == []
    assert context.long_term_facts == [
        {
            "key": "name",
            "value": "Zita",
            "reason": "user-a 的长期事实",
        }
    ]
    assert len(context.step_results) == 1
    assert context.step_results[0].step_type == PlanStepType.MEMORY
    assert context.step_results[0].step_name == "long_term"
    assert context.step_results[0].success is True
    assert context.step_results[0].detail == "Loaded long-term memory"


def test_memory_executor_records_step_result_when_using_agent_context(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.executors.memory_executor.memory_service",
        FakeMemoryService(),
    )
    context = AgentContext(session_id="user-a", user_input="你好")
    step = PlanStep(PlanStepType.MEMORY, "short_term")

    asyncio.run(MemoryExecutor().execute(step, context))

    assert context.recent_messages == [
        {"role": "user", "content": "user-a 上一轮用户消息"},
        {"role": "assistant", "content": "上一轮助手回复"},
    ]
    assert len(context.step_results) == 1
    assert context.step_results[0].step_type == PlanStepType.MEMORY
    assert context.step_results[0].step_name == "short_term"
    assert context.step_results[0].success is True
    assert context.step_results[0].detail == "Loaded short-term memory"
