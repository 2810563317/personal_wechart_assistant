"""
ToolExecutor

负责执行 Plan 中的 ToolStep。

ToolExecutor 位于 Runtime 和 ToolService 之间，只处理“执行工具步骤”
这一类动作，不判断用户意图，也不直接调用具体 Tool。
"""

from app.executors.base_executor import BaseExecutor, ExecutionContext
from app.services.planner_service import PlanStep
from app.services.tool_service import tool_service


class ToolExecutor(BaseExecutor):
    """
    ToolStep 执行器。

    职责：
    - 执行工具步骤
    - 调用 ToolService 获取工具结果和工具轨迹
    - 将工具结果写入 ExecutionContext

    不负责：
    - 判断是否需要工具
    - 直接调用 WeatherTool
    - 构建 Prompt
    """

    async def execute(self, step: PlanStep, context: ExecutionContext) -> None:
        """
        执行一个 ToolStep。

        Args:
            step: Planner 生成的 tool 类型步骤。
            context: 本轮 Agent 执行共享上下文。

        Returns:
            不返回值，工具执行结果写回 context。
        """
        tool_result, tool_trace = await tool_service.run_tool_if_needed(context.message)
        context.tool_result = tool_result.content if tool_result is not None else None
        context.tool_trace = tool_trace


tool_executor = ToolExecutor()
