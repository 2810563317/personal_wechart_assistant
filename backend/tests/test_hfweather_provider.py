import asyncio

import pytest

from app.exceptions import ExternalProviderError
from app.weather_providers.hfweather_provider import HFWeatherProvider


class FakeHFWeatherProvider(HFWeatherProvider):
    def __init__(self, responses: dict[str, dict[str, object]]) -> None:
        self.responses = responses
        self.api_key = "fake-key"
        self.api_host = "https://fake-host"
        self.default_city = "杭州"

    async def _get_json(self, path: str, params: dict[str, str]) -> dict[str, object]:
        return self.responses[path]


def test_get_weather_text_returns_formatted_weather_text() -> None:
    provider = FakeHFWeatherProvider(
        {
            "/geo/v2/city/lookup": {
                "code": "200",
                "location": [{"id": "101210101"}],
            },
            "/v7/weather/now": {
                "code": "200",
                "now": {
                    "text": "多云",
                    "temp": "25",
                    "feelsLike": "27",
                    "humidity": "72",
                    "windDir": "东南风",
                    "windScale": "1",
                },
            },
        }
    )

    result = asyncio.run(provider.get_weather_text("杭州"))

    assert result == "杭州当前多云，气温 25℃，体感 27℃，湿度 72%，东南风 1 级。"


def test_get_location_id_raises_when_geoapi_returns_no_location() -> None:
    provider = FakeHFWeatherProvider(
        {
            "/geo/v2/city/lookup": {
                "code": "200",
                "location": [],
            }
        }
    )

    with pytest.raises(ExternalProviderError) as exc_info:
        asyncio.run(provider._get_location_id("不存在的城市"))

    assert exc_info.value.status_code == 502
    assert exc_info.value.message == "HFWeather GeoAPI returned no location."


def test_get_weather_now_raises_when_weather_api_returns_invalid_now() -> None:
    provider = FakeHFWeatherProvider(
        {
            "/v7/weather/now": {
                "code": "200",
                "now": None,
            }
        }
    )

    with pytest.raises(ExternalProviderError) as exc_info:
        asyncio.run(provider._get_weather_now("101210101"))

    assert exc_info.value.status_code == 502
    assert exc_info.value.message == "HFWeather Weather API returned invalid now data."
