"""
ShortTermMemory

负责保存短期对话记忆。

当前版本只使用进程内 dict + list 按 session_id 保存最近消息，不接数据库、
不做长期记忆、不做摘要。这样可以先把 Memory 的职责边界建立清楚，
后续再替换存储实现。
"""


class ShortTermMemory:
    """
    短期记忆存储模块。

    职责：
    - 按 session_id 保存最近几轮用户与助手消息
    - 按 session_id 返回可直接传给 PromptService 的历史消息

    不负责：
    - 组织 Prompt
    - 调用大模型
    - 决定聊天业务流程
    """

    def __init__(self, max_messages: int = 10) -> None:
        """
        初始化短期记忆。

        Args:
            max_messages: 最多保留的消息数量。这里按 message 条数计算，
                一轮对话通常包含 user 和 assistant 两条消息。
        """
        self.max_messages = max_messages
        self.messages_by_session: dict[str, list[dict[str, str]]] = {}

    def get_recent_messages(self, session_id: str) -> list[dict[str, str]]:
        """
        获取指定 session 的最近对话消息。

        Args:
            session_id: 会话标识，用于隔离不同用户或不同会话的短期记忆。

        Returns:
            最近的对话消息副本，避免外部代码直接修改内部 list。
        """
        return self.messages_by_session.get(session_id, []).copy()

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
        messages = self.messages_by_session.setdefault(session_id, [])
        messages.extend(
            [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_reply},
            ]
        )
        self.messages_by_session[session_id] = messages[-self.max_messages :]

    def clear_session(self, session_id: str) -> None:
        """
        清空指定 session 的短期记忆。

        Args:
            session_id: 会话标识，只清空该 session 的短期记忆。
        """
        self.messages_by_session.pop(session_id, None)


short_term_memory = ShortTermMemory()
