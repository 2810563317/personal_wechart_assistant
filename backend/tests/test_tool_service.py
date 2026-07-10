import asyncio

from app.services.tool_service import ToolService
from app.tools.tool_exception import ToolException
from app.tools.tool_result import ToolResult


class FakeWeatherTool:
    def can_handle(self, message: str) -> bool:
        return "天气" in message

    async def run(self, message: str) -> ToolResult:
        return ToolResult(
            tool_name="weather",
            content="杭州当前多云，气温 25℃。",
            metadata={"city": "杭州"},
        )


class FakeFailingTool:
    def can_handle(self, message: str) -> bool:
        return "天气" in message

    async def run(self, message: str) -> ToolResult:
        raise ToolException(tool_name="weather", message="天气服务异常")


def test_run_tool_if_needed_returns_weather_tool_result() -> None:
    service = ToolService()
    service.tools = [FakeWeatherTool()]

    result, trace = asyncio.run(service.run_tool_if_needed("杭州今天天气怎么样？"))

    assert result is not None
    assert result.tool_name == "weather"
    assert result.content == "杭州当前多云，气温 25℃。"
    assert trace.used_tool is True
    assert trace.tool_name == "weather"
    assert trace.success is True
    assert trace.output == "杭州当前多云，气温 25℃。"
    assert trace.error is None
    assert trace.metadata == {"city": "杭州"}


def test_normal_message_does_not_trigger_tool() -> None:
    service = ToolService()
    service.tools = [FakeWeatherTool()]

    result, trace = asyncio.run(service.run_tool_if_needed("你好，帮我写一段自我介绍。"))

    assert result is None
    assert trace.used_tool is False
    assert trace.tool_name is None
    assert trace.success is True
    assert trace.output is None
    assert trace.error is None


def test_tool_exception_returns_failed_result_and_trace() -> None:
    service = ToolService()
    service.tools = [FakeFailingTool()]

    result, trace = asyncio.run(service.run_tool_if_needed("杭州今天天气怎么样？"))

    assert result is not None
    assert result.tool_name == "weather"
    assert result.success is False
    assert result.content == "工具暂时不可用，请稍后再试。"
    assert result.metadata == {"error": "天气服务异常"}
    assert trace.used_tool is True
    assert trace.tool_name == "weather"
    assert trace.success is False
    assert trace.output is None
    assert trace.error == "天气服务异常"
    assert trace.metadata == {"error": "天气服务异常"}
