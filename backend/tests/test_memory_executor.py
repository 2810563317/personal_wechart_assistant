import asyncio

from app.executors.base_executor import ExecutionContext
from app.executors.memory_executor import MemoryExecutor
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
    context = ExecutionContext(message="你好", session_id="user-a")
    step = PlanStep(PlanStepType.MEMORY, "short_term")

    asyncio.run(MemoryExecutor().execute(step, context))

    assert context.recent_messages == [
        {"role": "user", "content": "user-a 上一轮用户消息"},
        {"role": "assistant", "content": "上一轮助手回复"},
    ]
    assert context.long_term_facts == []


def test_memory_executor_loads_long_term_memory(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.executors.memory_executor.memory_service",
        FakeMemoryService(),
    )
    context = ExecutionContext(message="我叫什么名字？", session_id="user-a")
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
