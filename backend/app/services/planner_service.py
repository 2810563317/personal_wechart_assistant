"""
PlannerService

负责根据用户消息生成一轮 Agent 的执行计划。

Planner 只回答“Runtime 应该执行哪些步骤”，不亲自执行任何步骤。
这样以后从 rule-based Planner 升级到 AI Planner 时，不会影响 Tool、
Memory、Prompt、Model 的具体执行逻辑。
"""

from dataclasses import dataclass

from app.services.reflection_service import ReflectionResult


class PlanStepType:
    """
    Plan Step 类型常量。

    职责：
    - 统一描述 Runtime 可执行的步骤类型
    - 避免各处直接散落字符串

    不负责：
    - 执行具体步骤
    - 判断用户意图
    """

    MEMORY = "memory"
    TOOL = "tool"
    LLM = "llm"


@dataclass
class PlanStep:
    """
    单个计划步骤。

    职责：
    - 描述 Runtime 需要执行的一个步骤
    - 用 name 进一步区分同类步骤中的具体目标

    不负责：
    - 调用 Tool
    - 调用 Memory
    - 调用 LLM
    """

    step_type: str
    name: str | None = None


@dataclass
class Plan:
    """
    一轮 Agent 执行计划。

    职责：
    - 按顺序保存 Runtime 应执行的步骤
    - 作为 Planner 和 Runtime 之间的简单协议

    不负责：
    - 执行步骤
    - 保存执行结果
    - 生成最终回复
    """

    steps: list[PlanStep]


class PlannerService:
    """
    Rule-based Planner。

    职责：
    - 根据用户消息生成 Plan
    - 根据 ReflectionResult 生成 RePlan
    - 用简单规则识别当前是否需要天气工具

    不负责：
    - 调用 Tool
    - 调用 Memory
    - 调用 LLM
    - 编排 Runtime 执行过程
    """

    def __init__(self) -> None:
        self.weather_keywords = ["天气", "下雨", "气温"]

    def plan(self, message: str) -> Plan:
        """
        根据用户消息生成执行计划。

        Args:
            message: 用户本轮输入。

        Returns:
            Runtime 可按顺序执行的计划。
        """
        steps = [
            PlanStep(PlanStepType.MEMORY, "short_term"),
            PlanStep(PlanStepType.MEMORY, "long_term"),
        ]

        if self._needs_weather_tool(message):
            steps.append(PlanStep(PlanStepType.TOOL, "weather"))

        steps.append(PlanStep(PlanStepType.LLM))
        return Plan(steps)

    def create_replan(self, reflection_result: ReflectionResult) -> Plan:
        """
        根据 ReflectionResult 生成重新规划。

        Args:
            reflection_result: ReflectionService 对上一轮执行结果的评价。

        Returns:
            Runtime 可执行的新计划。
        """
        # RePlan V1 只做兜底回复，不再次调用工具，避免把重新规划误做成重试。
        return Plan([PlanStep(PlanStepType.LLM)])

    def _needs_weather_tool(self, message: str) -> bool:
        """
        判断消息是否需要天气工具。

        Args:
            message: 用户本轮输入。

        Returns:
            如果命中天气相关关键词，返回 True。
        """
        return any(keyword in message for keyword in self.weather_keywords)


planner_service = PlannerService()
