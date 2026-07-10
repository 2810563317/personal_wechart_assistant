"""
ToolException

负责定义工具执行失败时的统一异常类型。

ToolException 属于 Tool Layer，不直接决定 HTTP 返回，也不直接构建 Prompt。
后续 ToolService 会统一捕获它，并转换为可 trace 的工具失败结果。
"""


class ToolException(Exception):
    """
    工具异常。

    职责：
    - 标识哪个工具执行失败
    - 承载工具失败原因

    不负责：
    - 转换 HTTP 响应
    - 构建模型 Prompt
    - 决定 ChatService 流程
    """

    def __init__(self, tool_name: str, message: str) -> None:
        """
        初始化工具异常。

        Args:
            tool_name: 发生异常的工具名称。
            message: 工具失败原因。
        """
        self.tool_name = tool_name
        self.message = message
        super().__init__(message)
