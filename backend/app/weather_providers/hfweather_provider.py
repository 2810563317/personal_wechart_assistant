"""
HFWeatherProvider

负责适配和风天气 API。

Provider 只处理外部天气服务的 HTTP 调用、鉴权、响应解析和错误转换，
不负责判断用户是否需要查天气，也不负责 Agent 聊天流程。
"""

import httpx

from app.config import settings
from app.exceptions import ExternalProviderError


class HFWeatherProvider:
    """
    和风天气供应商适配层。

    职责：
    - 根据城市名调用 GeoAPI 获取 location ID
    - 根据 location ID 调用实时天气 API
    - 解析和风天气返回数据
    - 返回统一天气文本

    不负责：
    - 判断用户是否需要天气工具
    - 构建 Prompt
    - 调用大模型
    - 编排聊天流程
    """

    def __init__(self) -> None:
        """
        初始化和风天气 Provider。

        配置从环境变量读取，便于本地开发和后续部署时切换 API Host。
        """
        self.api_key = settings.HFWEATHER_API_KEY
        self.api_host = settings.HFWEATHER_API_HOST.rstrip("/")
        self.default_city = settings.HFWEATHER_DEFAULT_CITY

    async def get_weather_text(self, city: str | None = None) -> str:
        """
        获取统一格式的天气文本。

        Args:
            city: 城市名。为空时使用默认城市。

        Returns:
            统一天气文本。
        """
        target_city = city or self.default_city
        location_id = await self._get_location_id(target_city)
        weather_now = await self._get_weather_now(location_id)
        return self._format_weather_text(target_city, weather_now)

    async def _get_location_id(self, city: str) -> str:
        """
        调用 GeoAPI 获取城市 location ID。

        Args:
            city: 城市名。

        Returns:
            和风天气 location ID。
        """
        data = await self._get_json(
            path="/geo/v2/city/lookup",
            params={"location": city},
        )

        locations = data.get("location")
        if not isinstance(locations, list) or not locations:
            raise ExternalProviderError(
                message="HFWeather GeoAPI returned no location.",
                status_code=502,
            )

        location_id = locations[0].get("id")
        if not location_id:
            raise ExternalProviderError(
                message="HFWeather GeoAPI returned invalid location.",
                status_code=502,
            )

        return location_id

    async def _get_weather_now(self, location_id: str) -> dict[str, str]:
        """
        调用实时天气 API。

        Args:
            location_id: 和风天气 location ID。

        Returns:
            实时天气 now 数据。
        """
        data = await self._get_json(
            path="/v7/weather/now",
            params={"location": location_id},
        )

        now = data.get("now")
        if not isinstance(now, dict):
            raise ExternalProviderError(
                message="HFWeather Weather API returned invalid now data.",
                status_code=502,
            )

        return now

    async def _get_json(self, path: str, params: dict[str, str]) -> dict[str, object]:
        """
        发起和风天气 GET 请求并返回 JSON。

        Args:
            path: API path。
            params: 查询参数。

        Returns:
            API JSON 响应。
        """
        if not self.api_key:
            raise ExternalProviderError(
                status_code=500,
                message="HFWeather API Key is not configured. Please set HFWEATHER_API_KEY in .env.",
            )

        if not self.api_host:
            raise ExternalProviderError(
                status_code=500,
                message="HFWeather API Host is not configured. Please set HFWEATHER_API_HOST in .env.",
            )

        url = f"{self.api_host}{path}"
        headers = {"X-QW-Api-Key": self.api_key}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ExternalProviderError(
                status_code=exc.response.status_code,
                message=f"HFWeather API returned an error: {exc.response.text}",
            ) from exc
        except httpx.RequestError as exc:
            raise ExternalProviderError(
                status_code=502,
                message=f"Failed to request HFWeather API: {str(exc)}",
            ) from exc

        data = response.json()
        if data.get("code") != "200":
            raise ExternalProviderError(
                status_code=502,
                message=f"HFWeather API returned code {data.get('code')}.",
            )

        return data

    def _format_weather_text(self, city: str, now: dict[str, str]) -> str:
        """
        格式化统一天气文本。

        Args:
            city: 城市名。
            now: 和风天气 now 数据。

        Returns:
            统一天气文本。
        """
        text = now.get("text", "未知")
        temp = now.get("temp", "未知")
        feels_like = now.get("feelsLike", "未知")
        humidity = now.get("humidity", "未知")
        wind_dir = now.get("windDir", "未知风向")
        wind_scale = now.get("windScale", "未知")

        return (
            f"{city}当前{text}，气温 {temp}℃，体感 {feels_like}℃，"
            f"湿度 {humidity}%，{wind_dir} {wind_scale} 级。"
        )


hfweather_provider = HFWeatherProvider()
