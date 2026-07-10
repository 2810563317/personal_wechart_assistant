import httpx

from app.config import settings
from app.exceptions import ExternalProviderError


class DeepSeekProvider:
    def __init__(self) -> None:
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL.rstrip("/")
        self.model = settings.DEEPSEEK_MODEL

    async def generate_reply(self, messages: list[dict[str, str]]) -> str:
        if not self.api_key:
            raise ExternalProviderError(
                status_code=500,
                message="DeepSeek API Key is not configured. Please set DEEPSEEK_API_KEY in .env.",
            )

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ExternalProviderError(
                status_code=exc.response.status_code,
                message=f"DeepSeek API returned an error: {exc.response.text}",
            ) from exc
        except httpx.RequestError as exc:
            raise ExternalProviderError(
                status_code=502,
                message=f"Failed to request DeepSeek API: {str(exc)}",
            ) from exc

        data = response.json()

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ExternalProviderError(
                status_code=502,
                message="DeepSeek API returned an unexpected response format.",
            ) from exc


deepseek_provider = DeepSeekProvider()
