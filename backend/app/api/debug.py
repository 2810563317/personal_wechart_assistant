"""
Debug API

仅用于本地开发调试。

这里的接口会暴露进程内的调试数据，生产环境不应暴露。
"""

from fastapi import APIRouter

from app.schemas.debug import DebugPromptRequest, DebugPromptResponse
from app.services.memory_service import memory_service
from app.services.prompt_service import prompt_service
from app.services.tool_service import tool_service


router = APIRouter()


@router.get("/debug/memory")
async def get_debug_memory() -> dict[str, object]:
    """
    查看 default session 的记忆快照。

    该接口仅用于本地开发调试，生产环境不应暴露。

    Returns:
        当前进程内 default session 的短期记忆和长期事实。
    """
    return memory_service.get_memory_snapshot("default")


@router.get("/debug/memory/{session_id}")
async def get_debug_memory_by_session(session_id: str) -> dict[str, object]:
    """
    查看指定 session 的记忆快照。

    该接口仅用于本地开发调试，生产环境不应暴露。

    Args:
        session_id: 会话标识。

    Returns:
        指定 session 的短期记忆和长期事实。
    """
    return memory_service.get_memory_snapshot(session_id)


@router.delete("/debug/memory/{session_id}")
async def clear_debug_memory_by_session(session_id: str) -> dict[str, object]:
    """
    清空指定 session 的记忆。

    该接口仅用于本地开发调试，生产环境不应暴露。

    Args:
        session_id: 会话标识。

    Returns:
        清空结果。
    """
    memory_service.clear_session_memory(session_id)
    return {"session_id": session_id, "cleared": True}


@router.post("/debug/prompt", response_model=DebugPromptResponse)
async def build_debug_prompt(request: DebugPromptRequest) -> DebugPromptResponse:
    """
    查看本轮请求最终构建出的 Prompt messages。

    该接口仅用于本地开发调试，生产环境不应暴露。
    它不会调用 DeepSeek，不会保存短期记忆，也不会提取或保存长期事实。

    Args:
        request: Prompt 调试请求。

    Returns:
        Prompt 构建结果和相关调试信息。
    """
    session_id = request.session_id or "default"
    recent_messages = memory_service.get_recent_messages(session_id)
    long_term_facts = memory_service.get_long_term_facts(session_id)
    tool_result, tool_trace = await tool_service.run_tool_if_needed(request.message)
    tool_result_content = tool_result.content if tool_result is not None else None
    messages = prompt_service.build_messages(
        request.message,
        recent_messages,
        tool_result_content,
        long_term_facts,
    )

    return DebugPromptResponse(
        session_id=session_id,
        used_tool=tool_trace.used_tool,
        tool_name=tool_trace.tool_name,
        tool_result=tool_result_content,
        recent_messages_count=len(recent_messages),
        long_term_facts_count=len(long_term_facts),
        messages=messages,
    )
