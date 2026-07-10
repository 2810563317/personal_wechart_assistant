from app.services.observation_service import Observation
from app.services.reflection_service import ReflectionService


def test_reflect_fails_when_reply_is_empty() -> None:
    service = ReflectionService()
    observation = Observation(final_reply="   ")

    result = service.reflect(observation)

    assert result.status == "failed"
    assert result.reason == "Empty LLM response"
    assert result.should_replan is True


def test_reflect_fails_when_tool_execution_failed() -> None:
    service = ReflectionService()
    observation = Observation(
        final_reply="工具暂时不可用，请稍后再试。",
        tool_results=[
            {
                "tool_name": "weather",
                "content": "工具暂时不可用，请稍后再试。",
                "success": False,
            }
        ],
        execution_errors=["weather api error"],
    )

    result = service.reflect(observation)

    assert result.status == "failed"
    assert result.reason == "Tool execution failed"
    assert result.should_replan is True


def test_reflect_succeeds_when_reply_exists_and_tool_succeeded() -> None:
    service = ReflectionService()
    observation = Observation(
        final_reply="杭州当前多云，气温 25℃。",
        tool_results=[
            {
                "tool_name": "weather",
                "content": "杭州当前多云，气温 25℃。",
                "success": True,
            }
        ],
        execution_errors=[],
    )

    result = service.reflect(observation)

    assert result.status == "success"
    assert result.reason is None
    assert result.should_replan is False


def test_reflect_succeeds_when_no_tool_was_used() -> None:
    service = ReflectionService()
    observation = Observation(final_reply="你好，我是你的个人助手。")

    result = service.reflect(observation)

    assert result.status == "success"
    assert result.reason is None
    assert result.should_replan is False
