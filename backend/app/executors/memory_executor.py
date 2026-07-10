"""
MemoryExecutor

负责执行 Plan 中的 MemoryStep。

MemoryExecutor 位于 Runtime 和 MemoryService 之间，只处理“读取记忆”
这一类执行动作，不负责保存对话或提取长期记忆。
"""

from app.executors.base_executor import BaseExecutor, ExecutionContext
from app.services.memory_service import memory_service
from app.services.planner_service import PlanStep


class MemoryExecutor(BaseExecutor):
    """
    MemoryStep 执行器。

    职责：
    - 执行短期记忆读取步骤
    - 执行长期记忆读取步骤
    - 将读取结果写入 ExecutionContext

    不负责：
    - 保存本轮对话
    - 提取长期事实
    - 构建 Prompt
    """

    async def execute(self, step: PlanStep, context: ExecutionContext) -> None:
        """
        执行一个 MemoryStep。

        Args:
            step: Planner 生成的 memory 类型步骤。
            context: 本轮 Agent 执行共享上下文。

        Returns:
            不返回值，读取结果写回 context。
        """
        if step.name == "short_term":
            context.recent_messages = memory_service.get_recent_messages(context.session_id)
            return

        if step.name == "long_term":
            context.long_term_facts = memory_service.get_long_term_facts(context.session_id)


memory_executor = MemoryExecutor()
