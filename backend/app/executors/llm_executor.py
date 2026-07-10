"""
LLMExecutor

负责执行 Plan 中的 LLMStep。

LLMExecutor 位于 Runtime 和 Prompt/Model Service 之间，只处理
“构建模型输入并生成回复”这一类执行动作。
"""

from app.executors.base_executor import BaseExecutor, ExecutionContext
from app.services.model_service import model_service
from app.services.planner_service import PlanStep
from app.services.prompt_service import prompt_service


class LLMExecutor(BaseExecutor):
    """
    LLMStep 执行器。

    职责：
    - 基于 ExecutionContext 构建模型 messages
    - 调用 ModelService 生成助手回复
    - 将 messages 和 reply 写入 ExecutionContext

    不负责：
    - 读取 Memory
    - 调用 Tool
    - 保存对话
    """

    async def execute(self, step: PlanStep, context: ExecutionContext) -> None:
        """
        执行一个 LLMStep。

        Args:
            step: Planner 生成的 llm 类型步骤。
            context: 本轮 Agent 执行共享上下文。

        Returns:
            不返回值，模型输入和回复写回 context。
        """
        context.messages = prompt_service.build_messages(
            context.message,
            context.recent_messages,
            context.tool_result,
            context.long_term_facts,
        )
        context.reply = await model_service.generate_reply(context.messages)


llm_executor = LLMExecutor()
