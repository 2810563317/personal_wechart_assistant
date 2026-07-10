"""
ReflectionService

负责评价一轮 Agent 执行结果。

Reflection 只判断本轮结果是否成功，不执行重试、不重新规划、
不调用 Tool、Memory 或 LLM。这样可以避免评价层和执行层混在一起。
"""

from dataclasses import dataclass

from app.services.observation_service import Observation


@dataclass
class ReflectionResult:
    """
    一轮 Agent 执行结果的评价。

    职责：
    - 描述本轮执行是否成功
    - 描述失败原因
    - 预留是否需要重新规划的信号

    不负责：
    - 执行重试
    - 重新生成 Plan
    - 修改 Runtime 执行流程
    """

    status: str
    reason: str | None
    should_replan: bool


class ReflectionService:
    """
    Rule-based Reflection 服务。

    职责：
    - 根据 Observation 生成 ReflectionResult
    - 用简单规则识别空回复和工具失败

    不负责：
    - 调用 LLM 做反思
    - 决定是否重试
    - 执行重新规划
    """

    def reflect(
        self,
        observation: Observation,
    ) -> ReflectionResult:
        """
        评价一轮 Agent 执行结果。

        Args:
            observation: 本轮 Agent 执行完成后的观察结果。

        Returns:
            本轮执行结果评价。
        """
        if observation.final_reply.strip() == "":
            return ReflectionResult(
                status="failed",
                reason="Empty LLM response",
                should_replan=True,
            )

        if observation.execution_errors:
            return ReflectionResult(
                status="failed",
                reason="Tool execution failed",
                should_replan=True,
            )

        return ReflectionResult(
            status="success",
            reason=None,
            should_replan=False,
        )


reflection_service = ReflectionService()
