import asyncio

from app.executors.tool_executor import ToolExecutor
from app.services.agent_context import AgentContext
from app.services.planner_service import PlanStep, PlanStepType
from app.tools.tool_result import ToolResult
from app.tools.tool_trace import ToolTrace


class FakeToolService:
    def __init__(self, success: bool = True) -> None:
        self.success = success
        self.received_message: str | None = None

    async def run_tool_if_needed(self, message: str) -> tuple[ToolResult | None, ToolTrace]:
        self.received_message = message
        if self.success:
            result = ToolResult(
                tool_name="weather",
                content="北京当前晴，气温 30℃。",
                success=True,
            )
            trace = ToolTrace(
                used_tool=True,
                tool_name="weather",
                success=True,
                input=message,
                output=result.content,
                error=None,
            )
            return result, trace

        result = ToolResult(
            tool_name="weather",
            content="工具暂时不可用，请稍后再试。",
            success=False,
        )
        trace = ToolTrace(
            used_tool=True,
            tool_name="weather",
            success=False,
            input=message,
            output=None,
            error="weather api error",
        )
        return result, trace


def test_tool_executor_writes_success_result_to_agent_context(monkeypatch) -> None:
    fake_tool_service = FakeToolService(success=True)
    monkeypatch.setattr("app.executors.tool_executor.tool_service", fake_tool_service)
    context = AgentContext(session_id="user-a", user_input="北京气温多少")
    step = PlanStep(PlanStepType.TOOL, "weather")

    asyncio.run(ToolExecutor().execute(step, context))

    assert fake_tool_service.received_message == "北京气温多少"
    assert context.tool_results == [
        {
            "tool_name": "weather",
            "content": "北京当前晴，气温 30℃。",
            "success": True,
        }
    ]
    assert len(context.tool_traces) == 1
    assert context.tool_traces[0].success is True
    assert context.execution_errors == []
    assert len(context.step_results) == 1
    assert context.step_results[0].step_type == PlanStepType.TOOL
    assert context.step_results[0].step_name == "weather"
    assert context.step_results[0].success is True


def test_tool_executor_writes_failure_to_agent_context(monkeypatch) -> None:
    fake_tool_service = FakeToolService(success=False)
    monkeypatch.setattr("app.executors.tool_executor.tool_service", fake_tool_service)
    context = AgentContext(session_id="user-a", user_input="北京气温多少")
    step = PlanStep(PlanStepType.TOOL, "weather")

    asyncio.run(ToolExecutor().execute(step, context))

    assert context.tool_results == [
        {
            "tool_name": "weather",
            "content": "工具暂时不可用，请稍后再试。",
            "success": False,
        }
    ]
    assert len(context.tool_traces) == 1
    assert context.tool_traces[0].success is False
    assert context.execution_errors == ["weather api error"]
    assert len(context.step_results) == 1
    assert context.step_results[0].success is False
    assert context.step_results[0].detail == "weather api error"
