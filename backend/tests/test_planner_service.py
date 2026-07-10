from app.services.planner_service import PlannerService, PlanStepType
from app.services.reflection_service import ReflectionResult


def test_weather_message_generates_weather_tool_step() -> None:
    service = PlannerService()

    plan = service.plan("杭州今天天气怎么样？")

    assert [step.step_type for step in plan.steps] == [
        PlanStepType.MEMORY,
        PlanStepType.MEMORY,
        PlanStepType.TOOL,
        PlanStepType.LLM,
    ]
    assert plan.steps[2].name == "weather"


def test_rain_message_generates_weather_tool_step() -> None:
    service = PlannerService()

    plan = service.plan("上海会下雨吗？")

    assert any(
        step.step_type == PlanStepType.TOOL and step.name == "weather"
        for step in plan.steps
    )


def test_temperature_message_generates_weather_tool_step() -> None:
    service = PlannerService()

    plan = service.plan("北京气温多少？")

    assert any(
        step.step_type == PlanStepType.TOOL and step.name == "weather"
        for step in plan.steps
    )


def test_normal_message_does_not_generate_tool_step() -> None:
    service = PlannerService()

    plan = service.plan("你好，帮我写一段自我介绍。")

    assert all(step.step_type != PlanStepType.TOOL for step in plan.steps)


def test_all_plans_include_memory_and_llm_steps() -> None:
    service = PlannerService()

    plan = service.plan("你好")

    assert plan.steps[0].step_type == PlanStepType.MEMORY
    assert plan.steps[0].name == "short_term"
    assert plan.steps[1].step_type == PlanStepType.MEMORY
    assert plan.steps[1].name == "long_term"
    assert plan.steps[-1].step_type == PlanStepType.LLM
    assert plan.steps[-1].name is None


def test_create_replan_returns_llm_only_plan_after_failure() -> None:
    service = PlannerService()
    reflection_result = ReflectionResult(
        status="failed",
        reason="Tool execution failed",
        should_replan=True,
    )

    plan = service.create_replan(reflection_result)

    assert len(plan.steps) == 1
    assert plan.steps[0].step_type == PlanStepType.LLM
    assert plan.steps[0].name is None
    assert all(step.step_type != PlanStepType.TOOL for step in plan.steps)
