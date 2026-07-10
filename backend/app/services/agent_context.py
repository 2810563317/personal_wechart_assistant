"""
AgentContext

负责保存一次 Agent Run 的共享状态。

AgentContext 是 Framework V2 的生命周期状态容器。它只保存状态和执行结果，
不保存 Service、Provider、数据库连接或 HTTP 对象，避免变成能力容器。
"""

from dataclasses import dataclass, field
from uuid import uuid4

from app.services.observation_service import Observation
from app.services.planner_service import Plan, PlanStep
from app.services.reflection_service import ReflectionResult
from app.tools.tool_trace import ToolTrace


@dataclass
class StepResult:
    """
    单个 Step 的执行结果摘要。

    职责：
    - 记录 Step 类型和名称
    - 记录 Step 是否执行成功
    - 保存可用于 debug 的简要信息

    不负责：
    - 执行 Step
    - 保存业务对象实例
    - 决定后续计划
    """

    step_type: str
    step_name: str | None
    success: bool
    detail: str | None = None


@dataclass
class AgentContext:
    """
    一次 Agent Run 的共享状态容器。

    职责：
    - 保存 Agent 生命周期中的计划、执行、观察和反思状态
    - 在 Runtime、Planner、Executor、Observation、Reflection 之间传递状态
    - 为 debug 汇总提供统一数据来源

    不负责：
    - 持有 Service 或 Provider 实例
    - 编写业务规则
    - 执行 Tool、Memory 或 LLM 调用
    """

    session_id: str
    user_input: str
    run_id: str = field(default_factory=lambda: str(uuid4()))
    current_plan: Plan | None = None
    current_step: PlanStep | None = None
    step_results: list[StepResult] = field(default_factory=list)
    recent_messages: list[dict[str, str]] = field(default_factory=list)
    long_term_facts: list[dict[str, str]] = field(default_factory=list)
    tool_results: list[dict[str, object]] = field(default_factory=list)
    tool_traces: list[ToolTrace] = field(default_factory=list)
    messages: list[dict[str, str]] = field(default_factory=list)
    final_reply: str = ""
    observation: Observation | None = None
    reflection: ReflectionResult | None = None
    iteration_count: int = 0
    execution_errors: list[str] = field(default_factory=list)
