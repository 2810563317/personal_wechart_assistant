from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message")
    session_id: str | None = Field(None, description="Conversation session id")


class ChatDebug(BaseModel):
    """
    聊天调试信息。

    职责：
    - 描述本轮 Agent 执行过程中的关键中间状态
    - 帮助本地开发阶段验证 Memory、Tool 和 Reflection 链路

    不负责：
    - 存储调试日志
    - 控制业务流程
    """

    used_tool: bool = Field(..., description="Whether a tool was used")
    tool_name: str | None = Field(None, description="Tool name when a tool was used")
    tool_result: str | None = Field(None, description="Tool result when a tool was used")
    tool_success: bool = Field(..., description="Whether the tool call succeeded")
    tool_error: str | None = Field(None, description="Tool error when a tool call failed")
    tool_metadata: dict[str, str] | None = Field(None, description="Tool execution metadata")
    session_id: str = Field(..., description="Conversation session id")
    recent_messages_count: int = Field(..., description="Recent message count")
    long_term_facts_count: int = Field(..., description="Long-term fact count")
    extracted_facts_count: int = Field(..., description="Extracted long-term fact count")
    extracted_facts: list[dict[str, str]] = Field(..., description="Extracted long-term facts")
    prompt_messages_count: int = Field(..., description="Prompt message count")
    has_tool_context: bool = Field(..., description="Whether tool context was added")
    reflection_status: str = Field(..., description="Reflection status")
    reflection_reason: str | None = Field(None, description="Reflection failure reason")
    should_replan: bool = Field(..., description="Whether the result suggests replanning")


class ChatResponse(BaseModel):
    reply: str
    debug: ChatDebug | None = None
