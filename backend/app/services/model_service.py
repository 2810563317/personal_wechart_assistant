from app.model_providers.deepseek_provider import deepseek_provider


class ModelService:
    async def generate_reply(self, messages: list[dict[str, str]]) -> str:
        reply = await deepseek_provider.generate_reply(messages)
        return reply


model_service = ModelService()
