"""
ToolExecutor

负责执行 Plan 中的 ToolStep。

ToolExecutor 位于 Runtime 和 ToolService 之间，只处理“执行工具步骤”
这一类动作，不判断用户意图，也不直接调用具体 Tool。
"""

from app.executors.base_executor import BaseExecutor
from app.services.agent_context import AgentContext, StepResult
from app.services.planner_service import PlanStep
from app.services.tool_service import tool_service


class ToolExecutor(BaseExecutor):
    """
    ToolStep 执行器。

    职责：
    - 执行工具步骤
    - 调用 ToolService 获取工具结果和工具轨迹
    - 将工具结果写入 AgentContext

    不负责：
    - 判断是否需要工具
    - 直接调用 WeatherTool
    - 构建 Prompt
    """

    async def execute(self, step: PlanStep, context: AgentContext) -> None:
        """
        执行一个 ToolStep。

        Args:
            step: Planner 生成的 tool 类型步骤。
            context: 本轮 Agent Run 的共享状态容器。

        Returns:
            不返回值，工具执行结果写回 context。
        """
        tool_result, tool_trace = await tool_service.run_tool_if_needed(context.user_input)
        self._sync_agent_context(step, context, tool_result, tool_trace)

    def _sync_agent_context(
        self,
        step: PlanStep,
        context: AgentContext,
        tool_result,
        tool_trace,
    ) -> None:
        """
        将工具执行结果同步到 AgentContext。

        Args:
            step: 当前执行的 tool step。
            context: 本轮 Agent Run 的共享状态容器。
            tool_result: ToolService 返回的工具结果。
            tool_trace: ToolService 返回的工具轨迹。
        """
        if tool_result is not None:
            context.tool_results.append(
                {
                    "tool_name": tool_result.tool_name,
                    "content": tool_result.content,
                    "success": tool_result.success,
                }
            )

        context.tool_traces.append(tool_trace)

        if tool_trace.error is not None:
            context.execution_errors.append(tool_trace.error)

        context.step_results.append(
            StepResult(
                step_type=step.step_type,
                step_name=step.name,
                success=tool_trace.success,
                detail=tool_trace.error,
            )
        )


tool_executor = ToolExecutor()
