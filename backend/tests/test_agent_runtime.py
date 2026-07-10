import asyncio

from app.executors.base_executor import ExecutionContext
from app.services.agent_runtime import AgentRuntime
from app.services.planner_service import Plan, PlanStep, PlanStepType
from app.tools.tool_trace import ToolTrace


class FakePlannerService:
    def __init__(self, plan: Plan) -> None:
        self.plan_result = plan
        self.received_message: str | None = None
        self.replan_requests: list[str] = []

    def plan(self, message: str) -> Plan:
        self.received_message = message
        return self.plan_result

    def create_replan(self, reflection_result) -> Plan:
        self.replan_requests.append(reflection_result.reason)
        return Plan([PlanStep(PlanStepType.LLM)])


class FakeExecutor:
    def __init__(self, name: str, tool_success: bool = True) -> None:
        self.name = name
        self.tool_success = tool_success
        self.calls: list[tuple[str, str | None, str, str]] = []

    async def execute(self, step: PlanStep, context: ExecutionContext) -> None:
        self.calls.append(
            (step.step_type, step.name, context.message, context.session_id)
        )

        if self.name == "memory":
            if step.name == "short_term":
                context.recent_messages = [
                    {"role": "user", "content": "上一轮用户消息"},
                    {"role": "assistant", "content": "上一轮助手回复"},
                ]
            elif step.name == "long_term":
                context.long_term_facts = [
                    {
                        "key": "name",
                        "value": "Zita",
                        "reason": "用户明确说明自己的名字",
                    }
                ]
        elif self.name == "tool" and self.tool_success:
            context.tool_result = "北京当前晴，气温 30℃。"
            context.tool_trace = ToolTrace(
                used_tool=True,
                tool_name="weather",
                success=True,
                input=context.message,
                output=context.tool_result,
                error=None,
                metadata={"city": "北京", "provider": "hfweather"},
            )
        elif self.name == "tool":
            context.tool_result = "工具暂时不可用，请稍后再试。"
            context.tool_trace = ToolTrace(
                used_tool=True,
                tool_name="weather",
                success=False,
                input=context.message,
                output=None,
                error="weather api error",
                metadata={"error": "weather api error"},
            )
        elif self.name == "llm":
            context.messages = [
                {"role": "system", "content": "system"},
                *context.recent_messages,
                {"role": "user", "content": context.message},
            ]
            context.reply = f"reply with {len(context.messages)} messages"


class FakeMemoryService:
    def __init__(self) -> None:
        self.saved_conversation: tuple[str, str, str] | None = None
        self.saved_facts: tuple[str, list[dict[str, str]]] | None = None

    def save_conversation(self, session_id: str, message: str, reply: str) -> None:
        self.saved_conversation = (session_id, message, reply)

    def save_long_term_facts(
        self,
        session_id: str,
        facts: list[dict[str, str]],
    ) -> None:
        self.saved_facts = (session_id, facts)


class FakeMemoryExtractorService:
    async def extract_facts(self, message: str) -> list[dict[str, str]]:
        return [
            {
                "key": "learning",
                "value": "Execution Layer",
                "reason": "用户正在学习执行层",
            }
        ]


class FakeReflectionService:
    def reflect(self, observation):
        return type(
            "ReflectionResult",
            (),
            {
                "status": "failed",
                "reason": "Failed without replan",
                "should_replan": False,
            },
        )()


def build_plan(with_tool: bool) -> Plan:
    steps = [
        PlanStep(PlanStepType.MEMORY, "short_term"),
        PlanStep(PlanStepType.MEMORY, "long_term"),
    ]
    if with_tool:
        steps.append(PlanStep(PlanStepType.TOOL, "weather"))
    steps.append(PlanStep(PlanStepType.LLM))
    return Plan(steps)


def build_runtime(with_tool: bool, monkeypatch, tool_success: bool = True) -> tuple[
    AgentRuntime,
    FakePlannerService,
    FakeExecutor,
    FakeExecutor,
    FakeExecutor,
    FakeMemoryService,
]:
    fake_planner_service = FakePlannerService(build_plan(with_tool))
    fake_memory_executor = FakeExecutor("memory")
    fake_tool_executor = FakeExecutor("tool", tool_success=tool_success)
    fake_llm_executor = FakeExecutor("llm")
    fake_memory_service = FakeMemoryService()

    monkeypatch.setattr("app.services.agent_runtime.planner_service", fake_planner_service)
    monkeypatch.setattr("app.services.agent_runtime.memory_service", fake_memory_service)
    monkeypatch.setattr(
        "app.services.agent_runtime.memory_extractor_service",
        FakeMemoryExtractorService(),
    )

    runtime = AgentRuntime()
    runtime.executors = {
        PlanStepType.MEMORY: fake_memory_executor,
        PlanStepType.TOOL: fake_tool_executor,
        PlanStepType.LLM: fake_llm_executor,
    }
    return (
        runtime,
        fake_planner_service,
        fake_memory_executor,
        fake_tool_executor,
        fake_llm_executor,
        fake_memory_service,
    )


def test_agent_runtime_dispatches_executors_in_plan_order(monkeypatch) -> None:
    (
        runtime,
        fake_planner_service,
        fake_memory_executor,
        fake_tool_executor,
        fake_llm_executor,
        fake_memory_service,
    ) = build_runtime(with_tool=True, monkeypatch=monkeypatch)

    reply, debug = asyncio.run(runtime.run("北京气温多少", "user-weather"))

    assert fake_planner_service.received_message == "北京气温多少"
    assert fake_memory_executor.calls == [
        (PlanStepType.MEMORY, "short_term", "北京气温多少", "user-weather"),
        (PlanStepType.MEMORY, "long_term", "北京气温多少", "user-weather"),
    ]
    assert fake_tool_executor.calls == [
        (PlanStepType.TOOL, "weather", "北京气温多少", "user-weather")
    ]
    assert fake_llm_executor.calls == [
        (PlanStepType.LLM, None, "北京气温多少", "user-weather")
    ]
    assert reply == "reply with 4 messages"
    assert fake_memory_service.saved_conversation == (
        "user-weather",
        "北京气温多少",
        reply,
    )
    assert debug["used_tool"] is True
    assert debug["tool_result"] == "北京当前晴，气温 30℃。"
    assert debug["tool_metadata"] == {"city": "北京", "provider": "hfweather"}
    assert debug["recent_messages_count"] == 2
    assert debug["long_term_facts_count"] == 1
    assert debug["prompt_messages_count"] == 4
    assert debug["has_tool_context"] is True
    assert debug["reflection_status"] == "success"
    assert debug["reflection_reason"] is None
    assert debug["should_replan"] is False


def test_agent_runtime_does_not_replan_when_reflection_disables_replan(
    monkeypatch,
) -> None:
    (
        runtime,
        fake_planner_service,
        _fake_memory_executor,
        _fake_tool_executor,
        fake_llm_executor,
        _fake_memory_service,
    ) = build_runtime(with_tool=False, monkeypatch=monkeypatch)
    monkeypatch.setattr("app.services.agent_runtime.reflection_service", FakeReflectionService())

    _reply, debug = asyncio.run(runtime.run("你好", "user-a"))

    assert fake_planner_service.replan_requests == []
    assert fake_llm_executor.calls == [
        (PlanStepType.LLM, None, "你好", "user-a")
    ]
    assert debug["reflection_status"] == "failed"
    assert debug["reflection_reason"] == "Failed without replan"
    assert debug["should_replan"] is False


def test_agent_runtime_does_not_dispatch_tool_executor_without_tool_step(
    monkeypatch,
) -> None:
    (
        runtime,
        _fake_planner_service,
        _fake_memory_executor,
        fake_tool_executor,
        _fake_llm_executor,
        _fake_memory_service,
    ) = build_runtime(with_tool=False, monkeypatch=monkeypatch)

    _, debug = asyncio.run(runtime.run("你好", "user-a"))

    assert fake_tool_executor.calls == []
    assert debug["used_tool"] is False
    assert debug["tool_result"] is None
    assert debug["tool_success"] is True
    assert debug["tool_error"] is None
    assert debug["tool_metadata"] is None
    assert debug["has_tool_context"] is False
    assert debug["reflection_status"] == "success"
    assert debug["reflection_reason"] is None
    assert debug["should_replan"] is False


def test_agent_runtime_saves_extracted_facts_after_executor_steps(monkeypatch) -> None:
    (
        runtime,
        _fake_planner_service,
        _fake_memory_executor,
        _fake_tool_executor,
        _fake_llm_executor,
        fake_memory_service,
    ) = build_runtime(with_tool=False, monkeypatch=monkeypatch)

    _, debug = asyncio.run(runtime.run("我在学 Execution Layer", "user-a"))

    expected_facts = [
        {
            "key": "learning",
            "value": "Execution Layer",
            "reason": "用户正在学习执行层",
        }
    ]
    assert fake_memory_service.saved_facts == ("user-a", expected_facts)
    assert debug["extracted_facts_count"] == 1
    assert debug["extracted_facts"] == expected_facts


def test_agent_runtime_replans_with_llm_only_plan_when_tool_execution_failed(
    monkeypatch,
) -> None:
    (
        runtime,
        fake_planner_service,
        _fake_memory_executor,
        fake_tool_executor,
        fake_llm_executor,
        _fake_memory_service,
    ) = build_runtime(with_tool=True, monkeypatch=monkeypatch, tool_success=False)

    reply, debug = asyncio.run(runtime.run("北京气温多少", "user-weather"))

    assert fake_planner_service.replan_requests == ["Tool execution failed"]
    assert fake_tool_executor.calls == [
        (PlanStepType.TOOL, "weather", "北京气温多少", "user-weather")
    ]
    assert fake_llm_executor.calls == [
        (PlanStepType.LLM, None, "北京气温多少", "user-weather"),
        (PlanStepType.LLM, None, "北京气温多少", "user-weather"),
    ]
    assert reply == "reply with 4 messages"
    assert debug["used_tool"] is False
    assert debug["tool_result"] == "工具暂时不可用，请稍后再试。"
    assert debug["reflection_status"] == "success"
    assert debug["reflection_reason"] is None
    assert debug["should_replan"] is False
