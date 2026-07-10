"""
Application Exceptions

负责定义跨层可复用的项目异常。

Provider 层不应该依赖 FastAPI 这样的接口框架。它只需要表达
“外部服务调用失败”，由 API 层决定如何转换成 HTTP 响应。
"""


class ExternalProviderError(Exception):
    """
    外部服务供应商异常。

    职责：
    - 表达模型、天气等外部 Provider 调用失败
    - 保留建议状态码，方便 API 层转换为 HTTP 响应

    不负责：
    - 直接构造 HTTPException
    - 决定 Agent Runtime 是否重试或重新规划
    """

    def __init__(self, message: str, status_code: int = 502) -> None:
        """
        初始化外部 Provider 异常。

        Args:
            message: 外部服务失败原因。
            status_code: 建议 API 层返回的 HTTP 状态码。
        """
        self.message = message
        self.status_code = status_code
        super().__init__(message)
