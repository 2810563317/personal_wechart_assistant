import asyncio

from app.api import debug as debug_api
from app.schemas.debug import DebugPromptRequest
from app.tools.tool_result import ToolResult
from app.tools.tool_trace import ToolTrace


class FakeMemoryService:
    def get_recent_messages(self, session_id: str) -> list[dict[str, str]]:
        return [{"role": "user", "content": "上一轮消息"}]

    def get_long_term_facts(self, session_id: str) -> list[dict[str, str]]:
        return [
            {
                "key": "city",
                "value": "杭州",
                "reason": "用户明确说明所在城市",
            }
        ]


class FakeToolService:
    async def run_tool_if_needed(
        self,
        message: str,
    ) -> tuple[ToolResult | None, ToolTrace]:
        return (
            ToolResult(
                tool_name="weather",
                content="杭州当前多云，气温 25℃。",
                metadata={"city": "杭州"},
            ),
            ToolTrace(
                used_tool=True,
                tool_name="weather",
                success=True,
                input=message,
                output="杭州当前多云，气温 25℃。",
                error=None,
                metadata={"city": "杭州"},
            ),
        )


class FakePromptService:
    def build_messages(
        self,
        message: str,
        recent_messages: list[dict[str, str]],
        tool_result: str | None,
        long_term_facts: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": "system"},
            *recent_messages,
            {"role": "user", "content": f"{message} / {tool_result}"},
        ]


def test_build_debug_prompt_handles_tool_result_and_trace_tuple(monkeypatch) -> None:
    monkeypatch.setattr(debug_api, "memory_service", FakeMemoryService())
    monkeypatch.setattr(debug_api, "tool_service", FakeToolService())
    monkeypatch.setattr(debug_api, "prompt_service", FakePromptService())

    response = asyncio.run(
        debug_api.build_debug_prompt(
            DebugPromptRequest(message="杭州今天天气怎么样？", session_id="user-a")
        )
    )

    assert response.used_tool is True
    assert response.tool_name == "weather"
    assert response.tool_result == "杭州当前多云，气温 25℃。"
    assert response.recent_messages_count == 1
    assert response.long_term_facts_count == 1
    assert response.messages[-1]["content"] == "杭州今天天气怎么样？ / 杭州当前多云，气温 25℃。"
