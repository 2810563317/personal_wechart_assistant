"""
MemoryExtractorService

负责从用户消息中提取值得长期保存的结构化事实。

当前 V2 复用现有 ModelService 调用 LLM，不新增新的 LLM Provider。
本服务只负责提取和解析，不负责保存长期记忆，也不参与聊天流程编排。
"""

import json

from app.services.model_service import model_service


class MemoryExtractorService:
    """
    长期记忆提取服务。

    职责：
    - 构建长期记忆提取 Prompt
    - 调用 ModelService 获取 LLM 输出
    - 将 LLM 输出解析为结构化 facts

    不负责：
    - 保存长期记忆
    - 读取短期记忆
    - 构建聊天 Prompt
    - 调用工具
    """

    def __init__(self, model_service_instance=model_service) -> None:
        """
        初始化长期记忆提取服务。

        Args:
            model_service_instance: 模型服务实例。允许测试时注入 fake model service。
        """
        self.model_service = model_service_instance

    async def extract_facts(self, message: str) -> list[dict[str, str]]:
        """
        从用户消息中提取长期事实。

        Args:
            message: 用户本轮输入。

        Returns:
            结构化长期事实列表。如果没有可保存事实或解析失败，返回空列表。
        """
        messages = self._build_extraction_messages(message)
        reply = await self.model_service.generate_reply(messages)
        return self._parse_facts(reply)

    def _build_extraction_messages(self, message: str) -> list[dict[str, str]]:
        """
        构建长期记忆提取 messages。

        Args:
            message: 用户本轮输入。

        Returns:
            发送给模型的提取任务 messages。
        """
        return [
            {
                "role": "system",
                "content": (
                    "你负责从用户消息中提取值得长期保存的事实。"
                    "只返回 JSON，不要返回解释。"
                    "如果没有值得保存的信息，返回 {\"facts\": []}。"
                    "返回格式必须是："
                    "{\"facts\":[{\"key\":\"name\",\"value\":\"Zita\",\"reason\":\"用户明确说明自己的名字\"}]}"
                ),
            },
            {
                "role": "user",
                "content": message,
            },
        ]

    def _parse_facts(self, reply: str) -> list[dict[str, str]]:
        """
        解析 LLM 返回的长期事实 JSON。

        Args:
            reply: LLM 返回文本。

        Returns:
            校验后的结构化 facts。格式不符合预期时返回空列表。
        """
        try:
            data = json.loads(reply)
        except json.JSONDecodeError:
            return []

        if not isinstance(data, dict):
            return []

        facts = data.get("facts")
        if not isinstance(facts, list):
            return []

        return [fact for fact in facts if self._is_valid_fact(fact)]

    def _is_valid_fact(self, fact: object) -> bool:
        """
        判断单条 fact 是否符合结构要求。

        Args:
            fact: 待校验的 fact。

        Returns:
            如果包含非空 key、value、reason，返回 True。
        """
        if not isinstance(fact, dict):
            return False

        return all(
            isinstance(fact.get(field), str) and fact.get(field).strip()
            for field in ["key", "value", "reason"]
        )


memory_extractor_service = MemoryExtractorService()
