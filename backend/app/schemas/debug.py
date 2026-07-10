"""
Debug Schemas

负责定义本地调试接口使用的数据结构。

这些 schema 仅用于本地开发调试接口，生产环境不应暴露对应接口。
"""

from pydantic import BaseModel, Field


class DebugPromptRequest(BaseModel):
    """
    Prompt 调试请求。

    职责：
    - 接收本轮用户消息
    - 接收可选 session_id

    不负责：
    - 读取 Memory
    - 调用 Tool
    - 构建 Prompt
    """

    message: str = Field(..., min_length=1, description="User message")
    session_id: str | None = Field(None, description="Conversation session id")


class DebugPromptResponse(BaseModel):
    """
    Prompt 调试响应。

    职责：
    - 返回 Prompt 构建过程中的关键调试信息
    - 返回最终将发送给模型的 messages

    不负责：
    - 表示正式聊天接口响应
    - 存储调试日志
    """

    session_id: str
    used_tool: bool
    tool_name: str | None
    tool_result: str | None
    recent_messages_count: int
    long_term_facts_count: int
    messages: list[dict[str, str]]
