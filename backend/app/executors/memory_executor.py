"""
MemoryExecutor

负责执行 Plan 中的 MemoryStep。

MemoryExecutor 位于 Runtime 和 MemoryService 之间，只处理“读取记忆”
这一类执行动作，不负责保存对话或提取长期记忆。
"""

from app.executors.base_executor import BaseExecutor
from app.services.agent_context import AgentContext, StepResult
from app.services.memory_service import memory_service
from app.services.planner_service import PlanStep


class MemoryExecutor(BaseExecutor):
    """
    MemoryStep 执行器。

    职责：
    - 执行短期记忆读取步骤
    - 执行长期记忆读取步骤
    - 将读取结果写入 AgentContext

    不负责：
    - 保存本轮对话
    - 提取长期事实
    - 构建 Prompt
    """

    async def execute(self, step: PlanStep, context: AgentContext) -> None:
        """
        执行一个 MemoryStep。

        Args:
            step: Planner 生成的 memory 类型步骤。
            context: 本轮 Agent Run 的共享状态容器。

        Returns:
            不返回值，读取结果写回 context。
        """
        if step.name == "short_term":
            context.recent_messages = memory_service.get_recent_messages(context.session_id)
            self._record_step_result(step, context, "Loaded short-term memory")
            return

        if step.name == "long_term":
            context.long_term_facts = memory_service.get_long_term_facts(context.session_id)
            self._record_step_result(step, context, "Loaded long-term memory")

    def _record_step_result(
        self,
        step: PlanStep,
        context: AgentContext,
        detail: str,
    ) -> None:
        """
        在 AgentContext 中记录 MemoryStep 摘要。

        Args:
            step: 当前执行的 memory step。
            context: 本轮 Agent Run 的共享状态容器。
            detail: 可用于 debug 的执行摘要。
        """
        context.step_results.append(
            StepResult(
                step_type=step.step_type,
                step_name=step.name,
                success=True,
                detail=detail,
            )
        )


memory_executor = MemoryExecutor()
