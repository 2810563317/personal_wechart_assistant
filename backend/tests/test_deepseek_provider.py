import asyncio

import pytest

from app.exceptions import ExternalProviderError
from app.model_providers.deepseek_provider import DeepSeekProvider


def test_generate_reply_raises_provider_error_when_api_key_is_missing() -> None:
    provider = DeepSeekProvider()
    provider.api_key = ""

    with pytest.raises(ExternalProviderError) as exc_info:
        asyncio.run(provider.generate_reply([{"role": "user", "content": "你好"}]))

    assert exc_info.value.status_code == 500
    assert exc_info.value.message == (
        "DeepSeek API Key is not configured. Please set DEEPSEEK_API_KEY in .env."
    )
