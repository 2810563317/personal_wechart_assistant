"""
LLMExecutor

负责执行 Plan 中的 LLMStep。

LLMExecutor 位于 Runtime 和 Prompt/Model Service 之间，只处理
“构建模型输入并生成回复”这一类执行动作。
"""

from app.executors.base_executor import BaseExecutor
from app.services.agent_context import AgentContext, StepResult
from app.services.model_service import model_service
from app.services.planner_service import PlanStep
from app.services.prompt_service import prompt_service


class LLMExecutor(BaseExecutor):
    """
    LLMStep 执行器。

    职责：
    - 基于执行上下文构建模型 messages
    - 调用 ModelService 生成助手回复
    - 将 messages 和 reply 写入 AgentContext

    不负责：
    - 读取 Memory
    - 调用 Tool
    - 保存对话
    """

    async def execute(self, step: PlanStep, context: AgentContext) -> None:
        """
        执行一个 LLMStep。

        Args:
            step: Planner 生成的 llm 类型步骤。
            context: 本轮 Agent Run 的共享状态容器。

        Returns:
            不返回值，模型输入和回复写回 context。
        """
        context.messages = prompt_service.build_messages(
            context.user_input,
            context.recent_messages,
            self._latest_tool_result(context),
            context.long_term_facts,
        )
        reply = await model_service.generate_reply(context.messages)

        context.final_reply = reply
        context.step_results.append(
            StepResult(
                step_type=step.step_type,
                step_name=step.name,
                success=True,
                detail="Generated LLM reply",
            )
        )

    def _latest_tool_result(self, context: AgentContext) -> str | None:
        """
        获取最近一次工具结果文本。

        Args:
            context: 本轮 Agent Run 的共享状态。

        Returns:
            最近一次工具结果文本，没有工具结果时返回 None。
        """
        if not context.tool_results:
            return None

        content = context.tool_results[-1].get("content")
        return content if isinstance(content, str) else None


llm_executor = LLMExecutor()
