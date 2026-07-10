"""
LongTermMemory

负责保存长期事实记忆。

当前使用进程内 dict + list 按 session_id 保存结构化事实，不接数据库、
不做向量库、不做人物画像、不做复杂记忆压缩。
"""

Fact = dict[str, str]


class LongTermMemory:
    """
    长期记忆存储模块。

    职责：
    - 按 session_id 保存长期事实
    - 返回指定 session 的结构化长期事实
    - 暂时保留 V1 简单规则提取能力，方便学习和测试
    - 返回指定 session 的长期事实

    不负责：
    - 组织 Prompt
    - 调用大模型
    - 编排聊天流程
    """

    def __init__(self) -> None:
        """
        初始化长期记忆。

        当前先用内存 dict 按 session_id 存储事实，后续可替换为数据库或向量库。
        """
        self.facts_by_session: dict[str, list[Fact]] = {}

    def get_facts(self, session_id: str) -> list[Fact]:
        """
        获取指定 session 的长期事实。

        Args:
            session_id: 会话标识，用于隔离不同用户或不同会话的长期事实。

        Returns:
            长期事实副本，避免外部代码直接修改内部 list。
        """
        return self.facts_by_session.get(session_id, []).copy()

    def extract_facts(self, message: str) -> list[Fact]:
        """
        从用户消息中提取长期事实。

        Args:
            message: 用户本轮输入。

        Returns:
            从消息中提取到的长期事实列表。
        """
        rules = [
            ("我叫", "name", "用户明确说明自己的名字"),
            ("我是", "identity", "用户明确说明自己的身份"),
            ("我在学", "learning", "用户明确说明自己正在学习的内容"),
        ]

        for prefix, key, reason in rules:
            if message.startswith(prefix):
                fact_value = message.removeprefix(prefix).strip()
                if fact_value:
                    return [
                        {
                            "key": key,
                            "value": fact_value,
                            "reason": reason,
                        }
                    ]

        return []

    def save_facts(self, session_id: str, facts: list[Fact]) -> None:
        """
        保存指定 session 的长期事实。

        Args:
            session_id: 会话标识，用于隔离不同用户或不同会话的长期事实。
            facts: 需要保存的长期事实列表。
        """
        saved_facts = self.facts_by_session.setdefault(session_id, [])

        for fact in facts:
            if self._is_valid_fact(fact) and not self._has_same_key_value(saved_facts, fact):
                saved_facts.append(fact)

    def extract_and_save_facts(self, session_id: str, message: str) -> list[Fact]:
        """
        从用户消息中提取并保存长期事实。

        Args:
            session_id: 会话标识，用于隔离不同用户或不同会话的长期事实。
            message: 用户本轮输入。

        Returns:
            本轮提取到的长期事实列表。
        """
        facts = self.extract_facts(message)
        self.save_facts(session_id, facts)
        return facts

    def _is_valid_fact(self, fact: Fact) -> bool:
        """
        判断长期事实是否符合结构要求。

        Args:
            fact: 待校验的长期事实。

        Returns:
            如果包含非空 key、value、reason，返回 True。
        """
        return all(
            isinstance(fact.get(field), str) and fact.get(field).strip()
            for field in ["key", "value", "reason"]
        )

    def _has_same_key_value(self, saved_facts: list[Fact], fact: Fact) -> bool:
        """
        判断是否已经存在相同 key 和 value 的事实。

        Args:
            saved_facts: 当前 session 已保存的长期事实。
            fact: 待保存的长期事实。

        Returns:
            如果已存在相同 key 和 value，返回 True。
        """
        return any(
            saved_fact.get("key") == fact.get("key")
            and saved_fact.get("value") == fact.get("value")
            for saved_fact in saved_facts
        )

    def clear_session(self, session_id: str) -> None:
        """
        清空指定 session 的长期事实。

        Args:
            session_id: 会话标识，只清空该 session 的长期事实。
        """
        self.facts_by_session.pop(session_id, None)


long_term_memory = LongTermMemory()
