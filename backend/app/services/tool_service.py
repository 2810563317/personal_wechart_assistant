"""
ToolService

负责判断一轮用户消息是否需要调用工具，并返回工具结果和工具调用轨迹。

当前版本只注册 WeatherTool。后续如果接入 MCP、工具注册中心或模型
自主工具调用，应优先在这一层扩展。
"""

from app.tools.base_tool import BaseTool
from app.tools.tool_exception import ToolException
from app.tools.tool_result import ToolResult
from app.tools.tool_trace import ToolTrace
from app.tools.weather_tool import weather_tool


class ToolService:
    """
    工具服务层。

    职责：
    - 维护当前可用工具列表
    - 遍历工具并找到第一个能处理当前消息的工具
    - 向 ChatService 返回工具结果和工具调用轨迹
    - 统一处理工具异常

    不负责：
    - 维护具体工具的触发关键词
    - 构建 Prompt
    - 调用大模型
    - 适配具体模型供应商
    """

    def __init__(self) -> None:
        """
        初始化工具服务。

        当前只注册 WeatherTool。后续新增工具时，优先把工具加入这个列表。
        """
        self.tools: list[BaseTool] = [weather_tool]

    async def run_tool_if_needed(self, message: str) -> tuple[ToolResult | None, ToolTrace]:
        """
        判断用户消息是否需要调用工具。

        Args:
            message: 用户本轮输入。

        Returns:
            工具结果和工具调用轨迹。
        """
        for tool in self.tools:
            if tool.can_handle(message):
                return await self._run_tool(tool, message)

        return None, ToolTrace(
            used_tool=False,
            tool_name=None,
            success=True,
            input=message,
            output=None,
            error=None,
        )

    async def _run_tool(self, tool: BaseTool, message: str) -> tuple[ToolResult, ToolTrace]:
        """
        执行工具并生成调用轨迹。

        Args:
            tool: 命中的工具。
            message: 用户本轮输入。

        Returns:
            工具结果和工具调用轨迹。
        """
        try:
            result = await tool.run(message)
        except ToolException as exc:
            result = ToolResult(
                tool_name=exc.tool_name,
                content="工具暂时不可用，请稍后再试。",
                success=False,
                metadata={"error": exc.message},
            )
            return result, ToolTrace(
                used_tool=True,
                tool_name=exc.tool_name,
                success=False,
                input=message,
                output=None,
                error=exc.message,
                metadata=result.metadata,
            )

        return result, ToolTrace(
            used_tool=True,
            tool_name=result.tool_name,
            success=result.success,
            input=message,
            output=result.content,
            error=None if result.success else result.content,
            metadata=result.metadata,
        )


tool_service = ToolService()
