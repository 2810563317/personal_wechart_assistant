"""
ToolMetadata

负责定义工具的元信息。

Tool Metadata 描述“工具是什么”，不描述“工具执行结果是什么”。
后续所有 Tool 都应提供统一 metadata，方便 ToolService、debug、
未来 function calling 或 MCP 复用。
"""

from dataclasses import dataclass


@dataclass
class ToolMetadata:
    """
    工具元信息。

    职责：
    - 描述工具名称
    - 描述工具用途
    - 描述工具触发关键词

    不负责：
    - 判断当前消息是否需要工具
    - 执行工具
    - 承载工具执行结果
    """

    name: str
    description: str
    keywords: list[str]
