"""
BaseExecutor

负责定义 Execution Layer 的基础协议。

Executor 位于 Runtime 和 Service 之间。Runtime 只调度 Step，
Executor 负责执行某一种 Step，Service 负责具体能力落地。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.services.planner_service import PlanStep
from app.tools.tool_trace import ToolTrace


@dataclass
class ExecutionContext:
    """
    一轮 Agent 执行过程中的共享上下文。

    职责：
    - 保存 Runtime 执行 Plan 时产生的中间结果
    - 在不同 Executor 之间传递 Memory、Tool、LLM 的结果
    - 为 Runtime 汇总 debug 提供数据来源

    不负责：
    - 执行 Step
    - 调用 Service
    - 决定执行计划
    """

    message: str
    session_id: str
    recent_messages: list[dict[str, str]] = field(default_factory=list)
    long_term_facts: list[dict[str, str]] = field(default_factory=list)
    tool_result: str | None = None
    tool_trace: ToolTrace | None = None
    messages: list[dict[str, str]] = field(default_factory=list)
    reply: str = ""


class BaseExecutor(ABC):
    """
    Executor 抽象基类。

    职责：
    - 规定所有 Executor 的统一执行接口
    - 让 Runtime 可以按相同方式调度不同 Step

    不负责：
    - 保存 Executor 列表
    - 生成 Plan
    - 实现具体业务能力
    """

    @abstractmethod
    async def execute(self, step: PlanStep, context: ExecutionContext) -> None:
        """
        执行一个 PlanStep，并把结果写回 ExecutionContext。

        Args:
            step: Planner 生成的单个计划步骤。
            context: 本轮 Agent 执行共享上下文。

        Returns:
            不返回值，执行结果通过 context 传递给后续步骤。
        """
        raise NotImplementedError
