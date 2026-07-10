from app.services.agent_runtime import agent_runtime


class ChatService:
    """
    聊天接口服务层。

    职责：
    - 接收 Router 传入的聊天参数
    - 调用 AgentRuntime 执行一轮 Agent 对话
    - 向 Router 返回 reply 和 debug

    不负责：
    - HTTP 请求处理
    - Agent 执行流程编排
    - 具体 Memory、Tool、Prompt、Model 能力
    """

    async def chat(
        self,
        message: str,
        session_id: str = "default",
    ) -> tuple[str, dict[str, object]]:
        """
        执行一次聊天流程。

        Args:
            message: 用户本轮输入。
            session_id: 会话标识，用于隔离不同用户或不同会话的短期记忆。

        Returns:
            助手回复内容和本轮调试信息。
        """
        # ChatService 只做接口服务适配，Agent 执行生命周期交给 Runtime 管理。
        return await agent_runtime.run(message, session_id)


chat_service = ChatService()
