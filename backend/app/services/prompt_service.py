"""
PromptService

负责统一构建发送给大模型的 messages。

当前版本负责：
- System Prompt
- 长期事实记忆
- 最近对话消息
- 工具上下文
- 当前用户消息

不负责读取或保存 Memory，Memory 的获取由 ChatService 编排。
"""

Fact = dict[str, str]


class PromptService:
    """
    Prompt 构建服务。

    职责：
    - 统一组织模型需要的 messages 结构
    - 明确区分 system_prompt、long_term_facts、recent_messages、tool_context、current_user_message
    - 决定 system message、长期事实、历史消息、当前用户消息的顺序

    不负责：
    - 调用大模型
    - 保存聊天记忆
    - 编排聊天业务流程
    """

    def build_messages(
        self,
        message: str,
        recent_messages: list[dict[str, str]] | None = None,
        tool_result: str | None = None,
        long_term_facts: list[Fact] | None = None,
    ) -> list[dict[str, str]]:
        """
        构建发送给模型的消息列表。

        Args:
            message: 用户本轮输入。
            recent_messages: 最近对话消息，由 MemoryService 提供。
            tool_result: 工具返回结果，由 ToolService 提供。
            long_term_facts: 长期事实记忆，由 MemoryService 提供。

        Returns:
            符合模型接口要求的 messages 列表。
        """
        recent_messages = recent_messages or []
        long_term_facts = long_term_facts or []
        system_prompt = self._build_system_prompt()
        long_term_memory_message = self._build_long_term_memory_message(long_term_facts)
        tool_context = self._build_tool_context(tool_result)
        current_user_message = self._build_current_user_message(message, tool_context)

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
        ]

        if long_term_memory_message is not None:
            messages.append(long_term_memory_message)

        messages.extend(recent_messages)
        messages.append(
            {
                "role": "user",
                "content": current_user_message,
            }
        )

        return messages

    def _build_system_prompt(self) -> str:
        """
        构建系统提示词。

        Returns:
            当前助手的系统提示词。
        """
        return "你是一个有帮助的个人微信助手。"

    def _build_long_term_memory_message(
        self,
        long_term_facts: list[Fact],
    ) -> dict[str, str] | None:
        """
        构建长期记忆消息。

        Args:
            long_term_facts: 当前 session 已保存的长期事实。

        Returns:
            如果存在长期事实，返回 system message；否则返回 None。
        """
        if not long_term_facts:
            return None

        facts_text = "\n".join(
            f"- {fact['key']}: {fact['value']}（{fact['reason']}）"
            for fact in long_term_facts
            if self._is_valid_fact(fact)
        )
        if not facts_text:
            return None

        return {
            "role": "system",
            "content": f"长期记忆：\n{facts_text}",
        }

    def _is_valid_fact(self, fact: Fact) -> bool:
        """
        判断长期事实是否符合 Prompt 格式化要求。

        Args:
            fact: 结构化长期事实。

        Returns:
            如果包含非空 key、value、reason，返回 True。
        """
        return all(
            isinstance(fact.get(field), str) and fact.get(field).strip()
            for field in ["key", "value", "reason"]
        )

    def _build_tool_context(self, tool_result: str | None) -> str | None:
        """
        构建工具上下文。

        Args:
            tool_result: 工具返回结果，由 ToolService 提供。

        Returns:
            如果存在工具结果，返回工具上下文；否则返回 None。
        """
        if not tool_result:
            return None

        return f"工具查询结果：{tool_result}"

    def _build_current_user_message(
        self,
        message: str,
        tool_context: str | None,
    ) -> str:
        """
        构建当前用户消息。

        Args:
            message: 用户本轮输入。
            tool_context: 本轮工具上下文。

        Returns:
            当前 user message 的 content。
        """
        if not tool_context:
            return message

        return (
            f"用户问题：{message}\n\n"
            f"{tool_context}\n\n"
            "回答要求：请基于工具查询结果回答用户问题，不要使用自己的天气知识。"
        )


prompt_service = PromptService()
