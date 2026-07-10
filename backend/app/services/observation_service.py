"""
Observation

负责描述一轮 Agent 执行完成后的可观察结果。

Observation 位于 Runtime 和 Reflection 之间。Runtime 负责构建它，
Reflection 负责读取它并评价结果，这样 Reflection 不需要依赖 Runtime
内部零散变量。
"""

from dataclasses import dataclass, field


@dataclass
class Observation:
    """
    一轮 Agent 执行后的观察结果。

    职责：
    - 承载最终回复
    - 承载工具执行结果摘要
    - 承载执行错误
    - 承载 Prompt 和 Memory 使用情况

    不负责：
    - 判断执行是否成功
    - 决定是否重试
    - 执行重新规划
    """

    final_reply: str
    tool_results: list[dict[str, object]] = field(default_factory=list)
    execution_errors: list[str] = field(default_factory=list)
    prompt_messages_count: int = 0
    memory_used: bool = False
