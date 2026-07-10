"""
MemoryService

负责为业务流程提供统一的记忆能力入口。

当前版本只封装 ShortTermMemory。后续如果增加长期记忆、摘要记忆或
向量记忆，ChatService 仍然可以优先依赖 MemoryService，而不是直接
依赖具体存储实现。
"""

from app.memory.long_term_memory import long_term_memory
from app.memory.short_term_memory import short_term_memory

Fact = dict[str, str]


class MemoryService:
    """
    记忆服务层。

    职责：
    - 按 session_id 向 ChatService 提供最近对话
    - 按 session_id 保存一轮完整对话
    - 按 session_id 提供长期事实
    - 从用户消息中提取并保存长期事实
    - 为本地调试提供指定 session 的记忆快照和清空能力
    - 隔离具体 Memory 实现

    不负责：
    - 构建 Prompt
    - 调用大模型
    - 编排完整聊天流程
    """

    def get_recent_messages(self, session_id: str) -> list[dict[str, str]]:
        """
        获取指定 session 的最近对话消息。

        Args:
            session_id: 会话标识，用于隔离不同用户或不同会话的短期记忆。

        Returns:
            最近的用户与助手消息列表。
        """
        return short_term_memory.get_recent_messages(session_id)

    def save_conversation(
        self,
        session_id: str,
        user_message: str,
        assistant_reply: str,
    ) -> None:
        """
        保存指定 session 的一轮完整对话。

        Args:
            session_id: 会话标识，用于隔离不同用户或不同会话的短期记忆。
            user_message: 用户本轮输入。
            assistant_reply: 助手本轮回复。
        """
        short_term_memory.save_conversation(session_id, user_message, assistant_reply)

    def get_long_term_facts(self, session_id: str) -> list[Fact]:
        """
        获取指定 session 的长期事实。

        Args:
            session_id: 会话标识，用于隔离不同用户或不同会话的长期事实。

        Returns:
            指定 session 的长期事实列表。
        """
        return long_term_memory.get_facts(session_id)

    def save_long_term_facts(self, session_id: str, facts: list[Fact]) -> None:
        """
        保存指定 session 的结构化长期事实。

        Args:
            session_id: 会话标识，用于隔离不同用户或不同会话的长期事实。
            facts: 需要保存的结构化长期事实列表。
        """
        long_term_memory.save_facts(session_id, facts)

    def extract_and_save_long_term_facts(
        self,
        session_id: str,
        message: str,
    ) -> list[Fact]:
        """
        从用户消息中提取并保存长期事实。

        Args:
            session_id: 会话标识，用于隔离不同用户或不同会话的长期事实。
            message: 用户本轮输入。

        Returns:
            本轮提取到的长期事实列表。
        """
        return long_term_memory.extract_and_save_facts(session_id, message)

    def get_memory_snapshot(self, session_id: str) -> dict[str, object]:
        """
        获取指定 session 的记忆快照。

        Args:
            session_id: 会话标识，用于隔离不同用户或不同会话的记忆。

        Returns:
            包含短期记忆和长期事实的调试快照。
        """
        return {
            "session_id": session_id,
            "recent_messages": short_term_memory.get_recent_messages(session_id),
            "long_term_facts": long_term_memory.get_facts(session_id),
        }

    def clear_session_memory(self, session_id: str) -> None:
        """
        清空指定 session 的全部记忆。

        Args:
            session_id: 会话标识，只清空该 session 的短期记忆和长期事实。
        """
        short_term_memory.clear_session(session_id)
        long_term_memory.clear_session(session_id)


memory_service = MemoryService()
