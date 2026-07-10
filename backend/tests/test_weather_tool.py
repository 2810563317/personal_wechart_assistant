import asyncio

import pytest

from app.exceptions import ExternalProviderError
from app.tools.tool_exception import ToolException
from app.tools.weather_tool import WeatherTool


class FakeWeatherProvider:
    def __init__(self) -> None:
        self.received_city: str | None = None

    async def get_weather_text(self, city: str | None = None) -> str:
        self.received_city = city
        target_city = city or "杭州"
        return f"{target_city}当前多云，气温 25℃，体感 27℃，湿度 72%，东南风 1 级。"


class FakeFailingWeatherProvider:
    async def get_weather_text(self, city: str | None = None) -> str:
        raise ExternalProviderError("HFWeather API unavailable", status_code=502)


def test_can_handle_weather_message() -> None:
    tool = WeatherTool()

    assert tool.can_handle("杭州今天天气怎么样？") is True
    assert tool.can_handle("杭州今天会下雨吗？") is True
    assert tool.can_handle("杭州今天气温多少？") is True


def test_metadata_describes_weather_tool() -> None:
    tool = WeatherTool()

    assert tool.metadata.name == "weather"
    assert tool.metadata.description == "查询指定城市的实时天气"
    assert tool.metadata.keywords == ["天气", "下雨", "气温"]


def test_can_not_handle_normal_message() -> None:
    tool = WeatherTool()

    assert tool.can_handle("你好，帮我写一段自我介绍。") is False


def test_run_returns_tool_result() -> None:
    provider = FakeWeatherProvider()
    tool = WeatherTool(weather_provider=provider)

    result = asyncio.run(tool.run("杭州今天天气怎么样？"))

    assert result.tool_name == "weather"
    assert result.content == "杭州当前多云，气温 25℃，体感 27℃，湿度 72%，东南风 1 级。"
    assert result.success is True
    assert result.metadata == {"city": "杭州", "provider": "hfweather"}
    assert provider.received_city == "杭州"


def test_extract_city_from_rain_message() -> None:
    provider = FakeWeatherProvider()
    tool = WeatherTool(weather_provider=provider)

    result = asyncio.run(tool.run("上海会下雨吗？"))

    assert result.content.startswith("上海当前")
    assert provider.received_city == "上海"


def test_extract_city_from_temperature_message() -> None:
    provider = FakeWeatherProvider()
    tool = WeatherTool(weather_provider=provider)

    result = asyncio.run(tool.run("北京气温多少？"))

    assert result.content.startswith("北京当前")
    assert provider.received_city == "北京"


def test_use_default_city_when_city_can_not_be_extracted() -> None:
    provider = FakeWeatherProvider()
    tool = WeatherTool(weather_provider=provider)

    result = asyncio.run(tool.run("今天天气怎么样？"))

    assert result.content.startswith("杭州当前")
    assert result.metadata == {"city": "default", "provider": "hfweather"}
    assert provider.received_city is None


def test_provider_error_is_converted_to_tool_exception() -> None:
    tool = WeatherTool(weather_provider=FakeFailingWeatherProvider())

    with pytest.raises(ToolException) as exc_info:
        asyncio.run(tool.run("杭州今天天气怎么样？"))

    assert exc_info.value.tool_name == "weather"
    assert exc_info.value.message == "HFWeather API unavailable"
