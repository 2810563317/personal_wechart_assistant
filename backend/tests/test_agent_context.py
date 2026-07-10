from app.services.agent_context import AgentContext, StepResult


def test_agent_context_initializes_run_state() -> None:
    context = AgentContext(session_id="user-a", user_input="你好")

    assert context.run_id != ""
    assert context.session_id == "user-a"
    assert context.user_input == "你好"
    assert context.current_plan is None
    assert context.current_step is None
    assert context.final_reply == ""
    assert context.observation is None
    assert context.reflection is None
    assert context.iteration_count == 0


def test_agent_context_default_lists_are_isolated() -> None:
    first_context = AgentContext(session_id="user-a", user_input="你好")
    second_context = AgentContext(session_id="user-b", user_input="你好")

    first_context.recent_messages.append({"role": "user", "content": "只属于 user-a"})
    first_context.execution_errors.append("user-a error")

    assert second_context.recent_messages == []
    assert second_context.execution_errors == []


def test_step_result_records_step_summary() -> None:
    result = StepResult(
        step_type="tool",
        step_name="weather",
        success=False,
        detail="weather api error",
    )

    assert result.step_type == "tool"
    assert result.step_name == "weather"
    assert result.success is False
    assert result.detail == "weather api error"
