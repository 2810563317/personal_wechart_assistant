"""
BaseTool

负责定义所有工具必须遵守的标准接口。

以后新增 CalendarTool、SearchTool、MCPTool 等，都应该继承 BaseTool，
并实现 metadata、can_handle 和 run。
"""

from abc import ABC, abstractmethod

from app.tools.tool_metadata import ToolMetadata
from app.tools.tool_result import ToolResult


class BaseTool(ABC):
    """
    工具抽象基类。

    职责：
    - 规定 Tool Metadata 标准
    - 规定工具触发判断接口
    - 规定工具执行接口

    不负责：
    - 维护工具列表
    - 编排聊天流程
    - 调用模型
    """

    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """
        获取工具元信息。

        Returns:
            工具元信息。
        """
        raise NotImplementedError

    @abstractmethod
    def can_handle(self, message: str) -> bool:
        """
        判断工具是否能处理当前消息。

        Args:
            message: 用户本轮输入。

        Returns:
            如果工具可以处理当前消息，返回 True。
        """
        raise NotImplementedError

    @abstractmethod
    async def run(self, message: str) -> ToolResult:
        """
        执行工具。

        Args:
            message: 用户本轮输入。

        Returns:
            标准工具执行结果。
        """
        raise NotImplementedError
