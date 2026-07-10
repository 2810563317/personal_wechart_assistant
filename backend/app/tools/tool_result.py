"""
ToolResult

负责定义工具执行后的统一返回结构。

当前阶段只有 WeatherTool，但先统一结果结构，可以避免 ToolService
和 ChatService 依赖某个具体工具的返回格式。
"""

from dataclasses import dataclass


@dataclass
class ToolResult:
    """
    工具执行结果。

    职责：
    - 标识由哪个工具产生结果
    - 承载工具返回的文本内容
    - 表示工具执行是否成功
    - 承载工具执行附加信息

    不负责：
    - 判断是否需要调用工具
    - 执行具体工具逻辑
    - 构建 Prompt
    """

    tool_name: str
    content: str
    success: bool = True
    metadata: dict[str, str] | None = None
