"""
BaseExecutor

负责定义 Execution Layer 的基础协议。

Executor 位于 Runtime 和 Service 之间。Runtime 只调度 Step，
Executor 负责执行某一种 Step，Service 负责具体能力落地。
"""

from abc import ABC, abstractmethod

from app.services.agent_context import AgentContext
from app.services.planner_service import PlanStep


class BaseExecutor(ABC):
    """
    Executor 抽象基类。

    职责：
    - 规定所有 Executor 的统一执行接口
    - 让 Runtime 可以按相同方式调度不同 Step
    - 以 AgentContext 作为 Framework V2 的标准执行上下文

    不负责：
    - 保存 Executor 列表
    - 生成 Plan
    - 实现具体业务能力
    """

    @abstractmethod
    async def execute(self, step: PlanStep, context: AgentContext) -> None:
        """
        执行一个 PlanStep，并把结果写回 AgentContext。

        Args:
            step: Planner 生成的单个计划步骤。
            context: 本轮 Agent Run 的共享状态容器。

        Returns:
            不返回值，执行结果通过 context 传递给后续步骤。
        """
        raise NotImplementedError
