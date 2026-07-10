"""
WeatherTool

负责提供天气查询能力。

当前版本通过 HFWeatherProvider 获取天气，不直接编写 HTTP 请求。
这样可以把工具能力和外部天气供应商适配逻辑分开。
"""

from app.tools.base_tool import BaseTool
from app.exceptions import ExternalProviderError
from app.tools.tool_exception import ToolException
from app.tools.tool_metadata import ToolMetadata
from app.weather_providers.hfweather_provider import hfweather_provider
from app.tools.tool_result import ToolResult


class WeatherTool(BaseTool):
    """
    天气工具。

    职责：
    - 判断天气工具是否能处理当前消息
    - 返回天气查询结果
    - 隔离天气能力的具体实现

    不负责：
    - 构建 Prompt
    - 调用大模型
    - 编排聊天流程
    """

    def __init__(self, weather_provider=hfweather_provider) -> None:
        """
        初始化天气工具。

        Args:
            weather_provider: 天气供应商适配器。允许测试时注入 fake provider。

        天气相关关键词属于 WeatherTool 自己的能力边界，ToolService 只负责遍历工具。
        """
        self.keywords = ["天气", "下雨", "气温"]
        self.weather_provider = weather_provider

    @property
    def metadata(self) -> ToolMetadata:
        """
        获取天气工具元信息。

        Returns:
            天气工具元信息。
        """
        return ToolMetadata(
            name="weather",
            description="查询指定城市的实时天气",
            keywords=self.keywords,
        )

    def can_handle(self, message: str) -> bool:
        """
        判断天气工具是否能处理当前消息。

        Args:
            message: 用户本轮输入。

        Returns:
            如果消息包含天气相关关键词，返回 True。
        """
        return any(keyword in message for keyword in self.keywords)

    async def run(self, message: str) -> ToolResult:
        """
        执行天气工具。

        Args:
            message: 用户本轮输入。当前版本暂不解析具体城市，使用默认城市。

        Returns:
            统一工具执行结果。
        """
        city = self._extract_city(message)
        try:
            weather_text = await self.weather_provider.get_weather_text(city)
        except ExternalProviderError as exc:
            raise ToolException(tool_name=self.metadata.name, message=exc.message) from exc

        return ToolResult(
            tool_name=self.metadata.name,
            content=weather_text,
            metadata={
                "city": city or "default",
                "provider": "hfweather",
            },
        )

    def _extract_city(self, message: str) -> str | None:
        """
        从天气类消息中提取城市名。

        Args:
            message: 用户本轮输入。

        Returns:
            提取到的城市名。无法提取时返回 None，由 Provider 使用默认城市。
        """
        for keyword in self.keywords:
            if keyword in message:
                candidate = message.split(keyword, maxsplit=1)[0]
                return self._clean_city_candidate(candidate)

        return None

    def _clean_city_candidate(self, candidate: str) -> str | None:
        """
        清理城市候选文本。

        Args:
            candidate: 天气关键词前面的文本。

        Returns:
            清理后的城市名。没有有效城市时返回 None。
        """
        city = candidate.strip()

        for word in ["今天", "明天", "现在", "会", "的"]:
            city = city.replace(word, "")

        city = city.strip(" ，。？！?！")
        return city or None


weather_tool = WeatherTool()
