"""
ToolTrace

负责记录工具调用过程。

ToolTrace 面向 debug 和排查问题，不直接作为 Prompt 内容。
它和 ToolResult 分开，避免工具结果和调试信息混在一起。
"""

from dataclasses import dataclass


@dataclass
class ToolTrace:
    """
    工具调用轨迹。

    职责：
    - 记录是否使用工具
    - 记录工具名称
    - 记录工具是否成功
    - 记录工具输入、输出、错误和附加信息

    不负责：
    - 执行工具
    - 判断工具是否可处理消息
    - 构建 Prompt
    """

    used_tool: bool
    tool_name: str | None
    success: bool
    input: str
    output: str | None
    error: str | None
    metadata: dict[str, str] | None = None
