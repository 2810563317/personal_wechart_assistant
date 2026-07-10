# 当前开发阶段

当前版本：Agent Framework V1 收尾阶段

已完成：

- FastAPI API Layer
- ChatService
- AgentRuntime
- Planner V1
- Execution Layer V1
- Observe V1
- Reflection V1
- RePlan V1
- PromptService
- ShortTermMemory
- LongTermMemory
- LLM Memory Extractor
- Tool Engineering
- Weather Tool
- ModelService
- DeepSeekProvider
- Session 隔离
- Debug
- Unit Test
- README

当前 RePlan 状态：

- 已具备 RePlan V1
- RePlan V1 是 rule-based fallback replan
- RePlan V1 不是 Retry
- 工具失败后不会重新调用失败工具，而是生成兜底 LLM Plan

暂不开发：

- 数据库
- Workflow
- MCP
- Graph
- Tool Calling
- LLM Planner
- LLM Reflection
- RAG
- Multi-Agent
- 微信接入
