# Personal WeChat Assistant Backend

Personal WeChat Assistant 是一个个人微信助手项目。

当前阶段完成的是后端最小聊天闭环，并开始向 Agent 架构演进：

```text
用户输入消息
  |
  v
FastAPI POST /chat
  |
  v
ChatService
  |
  v
AgentRuntime
  |
  v
PlannerService 生成 Plan
  |
  v
Executor 执行 Plan Step
  |
  v
MemoryService / ToolService / PromptService / ModelService
  |
  v
DeepSeekProvider / WeatherTool / Memory
  |
  v
AgentRuntime
  |
  v
ReflectionService 评价本轮结果
  |
  +-- should_replan=true 且未超过最大循环次数
  |       |
  |       v
  |   PlannerService.create_replan()
  |       |
  |       v
  |   Executor 执行新 Plan
  |
  v
MemoryService 保存本轮对话和长期事实
  |
  v
返回 AI 回复
```

本阶段不接微信、不做前端、不接数据库，重点是把后端 API、大模型调用、短期记忆、长期记忆、真实天气 Tool，以及基础 Agent 分层边界跑通。

当前已具备 RePlan V1。RePlan V1 是 rule-based fallback replan，不是 Retry：

- Retry 表示重新执行失败动作，例如再次调用失败的天气工具。
- RePlan V1 表示根据 ReflectionResult 生成一个新的兜底 Plan。
- 当前工具失败后，新 Plan 只包含 LLM Step，不会再次调用失败工具。

## 项目结构

```text
backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   └── chat.py
│   ├── schemas/
│   │   ├── chat.py
│   │   └── debug.py
│   ├── memory/
│   │   ├── long_term_memory.py
│   │   └── short_term_memory.py
│   ├── executors/
│   │   ├── base_executor.py
│   │   ├── llm_executor.py
│   │   ├── memory_executor.py
│   │   └── tool_executor.py
│   ├── tools/
│   │   ├── base_tool.py
│   │   ├── tool_exception.py
│   │   ├── tool_metadata.py
│   │   ├── tool_result.py
│   │   ├── tool_trace.py
│   │   └── weather_tool.py
│   ├── weather_providers/
│   │   └── hfweather_provider.py
│   ├── services/
│   │   ├── agent_runtime.py
│   │   ├── chat_service.py
│   │   ├── memory_extractor_service.py
│   │   ├── memory_service.py
│   │   ├── model_service.py
│   │   ├── observation_service.py
│   │   ├── planner_service.py
│   │   ├── prompt_service.py
│   │   ├── reflection_service.py
│   │   └── tool_service.py
│   └── model_providers/
│       ├── __init__.py
│       └── deepseek_provider.py
├── tests/
│   ├── test_agent_runtime.py
│   ├── test_long_term_memory.py
│   ├── test_memory_extractor_service.py
│   ├── test_memory_executor.py
│   ├── test_memory_service.py
│   ├── test_planner_service.py
│   ├── test_prompt_service.py
│   ├── test_reflection_service.py
│   ├── test_hfweather_provider.py
│   ├── test_short_term_memory.py
│   ├── test_tool_service.py
│   └── test_weather_tool.py
├── .env.example
├── requirements.txt
└── README.md
```

## 当前分层职责

### API Router

文件：

```text
app/api/chat.py
```

职责：

- 声明 `POST /chat` 接口
- 接收并校验请求参数
- 调用 `ChatService`
- 返回 `ChatResponse`

Router 不负责聊天流程，也不直接调用 DeepSeek。

### Schema

文件：

```text
app/schemas/chat.py
```

职责：

- 定义请求结构 `ChatRequest`
- 定义响应结构 `ChatResponse`
- 定义调试结构 `ChatDebug`
- 保证接口返回格式稳定

当前 `ChatRequest` 支持：

```json
{
  "message": "你好",
  "session_id": "user-a"
}
```

`session_id` 是可选字段。如果请求没有传，后端会默认使用 `"default"`。

当前 `POST /chat` 返回格式：

```json
{
  "reply": "...",
  "debug": {
    "used_tool": false,
    "tool_name": null,
    "tool_result": null,
    "tool_success": true,
    "tool_error": null,
    "tool_metadata": null,
    "session_id": "default",
    "recent_messages_count": 0,
    "long_term_facts_count": 0,
    "extracted_facts_count": 0,
    "extracted_facts": [],
    "prompt_messages_count": 2,
    "has_tool_context": false,
    "reflection_status": "success",
    "reflection_reason": null,
    "should_replan": false
  }
}
```

`debug` 是可选字段，用于本地开发阶段观察 Agent 执行过程。后续正式接口可以选择不返回或不展示该字段。

### ChatService

文件：

```text
app/services/chat_service.py
```

职责：

- 接收 Router 传入的聊天参数
- 调用 `AgentRuntime` 执行一轮 Agent 对话
- 返回 reply 和 debug

ChatService 是接口服务层，不再负责具体 Agent 执行流程。

它不直接调用 Memory、Tool、Prompt、Model，也不直接调用模型供应商。

### AgentRuntime

文件：

```text
app/services/agent_runtime.py
```

职责：

- 协调一轮 Agent 的完整执行过程
- 调用 `PlannerService` 生成执行计划
- 在最大循环次数内执行 RePlan
- 按 Plan 调度对应 Executor
- 维护一轮执行的 `ExecutionContext`
- 调用 `ReflectionService` 评价本轮结果
- 保存本轮短期对话
- 调用 `MemoryExtractorService` 提取长期事实
- 保存长期事实
- 返回 reply 和 debug

AgentRuntime 是 Agent 的执行协调者。它不负责制定计划，不直接执行具体 Step，也不编写 Reflection 评价规则。RePlan 时，Runtime 只负责调用 Planner 生成新 Plan 并执行，不决定新 Plan 内容。

当前 Runtime 流程：

```text
AgentRuntime.run(message, session_id)
  |
  |-- PlannerService.plan()
  |-- MemoryStep(short_term) -> MemoryExecutor
  |-- MemoryStep(long_term)  -> MemoryExecutor
  |-- ToolStep(weather)     -> ToolExecutor
  |-- LLMStep()             -> LLMExecutor
  |-- 构建 Observation
  |-- ReflectionService.reflect(observation)
  |-- 如果 failed 且未超过 max_iterations
  |     |-- PlannerService.create_replan()
  |     |-- 执行 RePlan
  |-- MemoryService.save_conversation()
  |-- MemoryExtractorService.extract_facts()
  |-- MemoryService.save_long_term_facts()
  |
  v
reply, debug
```

当前 debug 信息包括：

```json
{
  "used_tool": true,
  "tool_name": "weather",
  "tool_result": "杭州今天多云，气温 25-31℃，傍晚可能有小雨。",
  "tool_success": true,
  "tool_error": null,
  "tool_metadata": {
    "city": "杭州",
    "provider": "hfweather"
  },
  "session_id": "user-a",
  "recent_messages_count": 4,
  "long_term_facts_count": 2,
  "extracted_facts_count": 1,
  "extracted_facts": [
    {
      "key": "name",
      "value": "Zita",
      "reason": "用户明确说明自己的名字"
    }
  ],
  "prompt_messages_count": 6,
  "has_tool_context": true,
  "reflection_status": "success",
  "reflection_reason": null,
  "should_replan": false
}
```

这些信息只用于观察本轮 Agent 流程，不会写入数据库。

### PlannerService

文件：

```text
app/services/planner_service.py
```

职责：

- 根据用户消息生成 Plan
- 用简单规则判断是否需要天气工具步骤
- 把“要做什么”交给 `AgentRuntime`

不负责：

- 调用 Tool
- 调用 Memory
- 调用 LLM
- 执行 Plan

当前 Planner V1 是 rule-based Planner，不使用 LLM 做规划，不引入 Workflow，不引入 Graph，也不接 MCP。

当前 Plan 数据结构：

```python
Plan(
    steps=[
        PlanStep(step_type="memory", name="short_term"),
        PlanStep(step_type="memory", name="long_term"),
        PlanStep(step_type="tool", name="weather"),
        PlanStep(step_type="llm"),
    ]
)
```

当前规则：

```text
如果用户消息包含 “天气” / “下雨” / “气温”
  -> MemoryStep(short_term)
  -> MemoryStep(long_term)
  -> ToolStep(weather)
  -> LLMStep()

否则
  -> MemoryStep(short_term)
  -> MemoryStep(long_term)
  -> LLMStep()
```

Planner 只描述 Runtime 应该执行哪些步骤。Runtime 负责调度 Executor，真正的 Memory 读取、Tool 调用、Prompt 构建和 Model 调用由对应 Executor 触发。

当前 RePlan V1 规则：

```text
如果 ReflectionResult.should_replan 为 true
  -> PlannerService.create_replan()
  -> 返回只包含 LLMStep() 的 Plan
```

RePlan V1 不是 Retry。Retry 是再次执行失败动作，例如再次调用天气工具；RePlan 是生成新的执行计划。当前工具失败后，新 Plan 不包含 ToolStep，只让 LLM 基于已有上下文生成兜底回复。

### Observation

文件：

```text
app/services/observation_service.py
```

职责：

- 描述一轮 Agent 执行完成后的可观察结果
- 作为 Runtime 和 Reflection 之间的数据协议
- 统一承载最终回复、工具结果、执行错误、Prompt 数量和 Memory 使用情况

不负责：

- 判断执行是否成功
- 执行重试
- 重新规划
- 调用 Tool、Memory 或 LLM

当前结构：

```python
Observation(
    final_reply="...",
    tool_results=[
        {
            "tool_name": "weather",
            "content": "北京当前晴，气温 30℃。",
            "success": True,
        }
    ],
    execution_errors=[],
    prompt_messages_count=4,
    memory_used=True,
)
```

Observe V1 后，Reflection 不再接收 `reply`、`tool_result`、`tool_trace` 等零散字段，而是统一接收 `Observation`。

### ReflectionService

文件：

```text
app/services/reflection_service.py
```

职责：

- 评价一轮 Agent 执行结果
- 接收 `Observation`
- 判断本轮结果是 `success` 还是 `failed`
- 返回失败原因
- 预留 `should_replan` 信号

不负责：

- 执行重试
- 重新规划
- 调用 Tool
- 调用 Memory
- 调用 LLM

当前 Reflection V1 是 rule-based Reflection，不使用 LLM 做反思。

当前规则：

```text
如果 observation.final_reply 为空
  -> failed / Empty LLM response / should_replan=true

如果 observation.execution_errors 非空
  -> failed / Tool execution failed / should_replan=true

其他情况
  -> success / None / should_replan=false
```

`should_replan` 是 Runtime 是否调用 `PlannerService.create_replan()` 的控制信号。当前已实现 RePlan V1，但不实现 Retry。

### Execution Layer

目录：

```text
app/executors/
```

职责：

- 执行 Planner 生成的具体 Step
- 将执行结果写入 `ExecutionContext`
- 隔离 Runtime 和具体 Service 调用细节

当前 Executor：

- `MemoryExecutor`：执行 `MemoryStep`，内部调用 `MemoryService`
- `ToolExecutor`：执行 `ToolStep`，内部调用 `ToolService`
- `LLMExecutor`：执行 `LLMStep`，内部调用 `PromptService` 和 `ModelService`

Executor 不负责生成 Plan，也不负责保存对话收尾逻辑。

### MemoryService

文件：

```text
app/services/memory_service.py
```

职责：

- 作为记忆能力的统一服务入口
- 向 `AgentRuntime` 提供最近对话
- 保存一轮完整对话
- 向 `AgentRuntime` 提供长期事实
- 从用户消息中提取并保存长期事实
- 为本地调试提供指定 session 的记忆快照
- 为本地调试清空指定 session 的短期记忆和长期事实
- 隔离具体 Memory 实现

当前默认封装：

- `ShortTermMemory`
- `LongTermMemory`

后续如果增加长期记忆、摘要记忆、Redis、数据库或向量记忆，优先在这一层扩展，而不是让 `AgentRuntime` 直接依赖具体存储实现。

### ShortTermMemory

文件：

```text
app/memory/short_term_memory.py
```

职责：

- 使用进程内 dict + list 按 session_id 保存最近对话消息
- 按 session_id 保存 user message 和 assistant reply
- 按 session_id 返回最近消息给 `MemoryService`

当前限制：

- 不接数据库
- 不做长期记忆
- 不做摘要

当前短期记忆已经支持基于 `session_id` 的会话隔离，但仍然只保存在当前进程内。服务重启后，内存中的短期记忆会清空。

短期记忆当前保存的消息结构：

```python
[
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好，我是你的个人助手。"},
]
```

### LongTermMemory

文件：

```text
app/memory/long_term_memory.py
```

职责：

- 使用进程内 dict + list 按 session_id 保存结构化长期事实
- 按 session_id 返回结构化长期事实给 `MemoryService`
- 对相同 key 和 value 的重复事实做简单去重
- 暂时保留 V1 简单规则提取能力，方便学习和测试

当前限制：

- 不接数据库
- 不做向量库
- 不做人物画像
- 不做复杂记忆压缩

Memory V2 的长期事实结构：

```python
{
    "key": "name",
    "value": "Zita",
    "reason": "用户明确说明自己的名字",
}
```

当前保存的长期事实示例：

```python
[
    {
        "key": "name",
        "value": "Zita",
        "reason": "用户明确说明自己的名字",
    },
    {
        "key": "learning",
        "value": "FastAPI",
        "reason": "用户明确说明自己正在学习的内容",
    },
]
```

V1 简单规则仍然保留，但 AgentRuntime 已改为使用 MemoryExtractorService 做 LLM 自动提取：

```text
我叫xxx   -> {"key": "name", "value": "xxx", ...}
我是xxx   -> {"key": "identity", "value": "xxx", ...}
我在学xxx -> {"key": "learning", "value": "xxx", ...}
```

### MemoryExtractorService

文件：

```text
app/services/memory_extractor_service.py
```

职责：

- 构建长期记忆提取 Prompt
- 复用 `ModelService` 调用 LLM
- 要求 LLM 返回结构化 JSON
- 解析并校验 LLM 输出
- 返回结构化 facts 给 `AgentRuntime`

不负责：

- 保存长期记忆
- 读取短期记忆
- 构建聊天 Prompt
- 调用工具

期望 LLM 返回：

```json
{
  "facts": [
    {
      "key": "name",
      "value": "Zita",
      "reason": "用户明确说明自己的名字"
    }
  ]
}
```

如果没有值得保存的信息，返回：

```json
{
  "facts": []
}
```

如果 LLM 返回的不是合法 JSON，或 facts 结构不符合要求，当前版本会返回空列表，避免影响主聊天流程。

当前采用“本轮保存，下轮生效”：

```text
本轮先读取已有长期事实构建 Prompt
模型回复后，再由 MemoryExtractorService 从本轮用户输入中提取并保存新事实
新事实从下一轮开始进入 Prompt
```

### ToolService

文件：

```text
app/services/tool_service.py
```

职责：

- 维护当前可用工具列表
- 遍历工具并找到第一个能处理当前消息的工具
- 调用命中的工具
- 捕获工具执行中的受控异常
- 向 `AgentRuntime` 返回工具结果和工具调用轨迹

当前只支持天气工具。

当前注册的工具列表：

```python
tools = [weather_tool]
```

ToolService 不负责维护具体工具的触发关键词，不负责构建 Prompt，不负责调用大模型，也不属于 `DeepSeekProvider`。

这样设计的原因是：工具调用是 Agent 业务流程的一部分，不是某个模型供应商的职责。后续即使从 DeepSeek 切换到 OpenAI、Qwen 或 Claude，工具判断逻辑也不应该重复写到每个 Provider 里。

当前工具路由流程：

```python
for tool in tools:
    if tool.can_handle(message):
        result = await tool.run(message)
        return result, trace

return None, trace
```

### BaseTool

文件：

```text
app/tools/base_tool.py
```

职责：

- 定义所有 Tool 必须遵守的抽象接口
- 要求 Tool 提供 `metadata`
- 要求 Tool 提供 `can_handle(message)`
- 要求 Tool 提供 `run(message)`

以后新增 Calendar、Search、MCP Tool 时，都应先继承 `BaseTool`，而不是直接让 `ToolService` 依赖具体实现。

标准接口：

```python
class BaseTool:
    @property
    def metadata(self) -> ToolMetadata:
        ...

    def can_handle(self, message: str) -> bool:
        ...

    async def run(self, message: str) -> ToolResult:
        ...
```

### ToolMetadata

文件：

```text
app/tools/tool_metadata.py
```

职责：

- 描述工具名称
- 描述工具用途
- 描述工具触发关键词

`ToolMetadata` 描述“工具是什么”，不描述“工具执行结果是什么”。

当前结构：

```python
ToolMetadata(
    name="weather",
    description="查询指定城市的实时天气",
    keywords=["天气", "下雨", "气温"],
)
```

### ToolResult

文件：

```text
app/tools/tool_result.py
```

职责：

- 定义工具执行后的统一返回结构
- 标识由哪个工具产生结果
- 承载工具返回的文本内容
- 表示工具是否执行成功
- 承载工具结果的附加元信息

当前结构：

```python
ToolResult(
    tool_name="weather",
    content="杭州当前多云，气温 25℃，体感 27℃，湿度 72%，东南风 1 级。",
    success=True,
    metadata={
        "city": "杭州",
        "provider": "hfweather",
    },
)
```

`tool_name` 用于 debug，`content` 用于注入 Prompt，`metadata` 用于观察工具实际执行细节。

### ToolException

文件：

```text
app/tools/tool_exception.py
```

职责：

- 定义工具执行失败时的统一异常类型
- 标识失败工具名称
- 承载工具失败原因

Tool 本身可以抛出 `ToolException`，但不直接决定 HTTP 返回。`ToolService` 会统一捕获异常，并转换成失败的 `ToolResult` 和 `ToolTrace`。

### ToolTrace

文件：

```text
app/tools/tool_trace.py
```

职责：

- 记录本轮是否使用了工具
- 记录工具名称、输入、输出和错误
- 记录工具是否执行成功
- 为 `/chat` 的 debug 字段提供数据来源

`ToolTrace` 面向本地调试和学习，不直接作为 Prompt 内容。它和 `ToolResult` 分开，是为了避免“给模型看的结果”和“给开发者看的过程”混在一起。

### WeatherTool

文件：

```text
app/tools/weather_tool.py
```

职责：

- 判断天气工具是否能处理当前消息
- 提供天气查询能力
- 通过 HFWeatherProvider 获取天气文本
- 隔离天气能力的具体实现
- 作为后续所有 Tool 的标准实现模板

当前实现 `BaseTool` 的三个核心能力：

```python
metadata -> ToolMetadata
can_handle(message: str) -> bool
async run(message: str) -> ToolResult
```

触发天气工具的关键词：

```python
["天气", "下雨", "气温"]
```

当前支持简单城市提取：

```text
杭州今天天气怎么样 -> 杭州
上海会下雨吗       -> 上海
北京气温多少       -> 北京
今天天气怎么样     -> 使用 HFWEATHER_DEFAULT_CITY
```

如果无法从用户消息中提取城市名，WeatherTool 会把 `None` 传给 HFWeatherProvider，由 Provider 使用 `.env` 中的 `HFWEATHER_DEFAULT_CITY`。

当前不接：

- MCP
- 数据库
- 微信

当前天气结果示例：

```text
杭州当前多云，气温 25℃，体感 27℃，湿度 72%，东南风 1 级。
```

工具结果不会直接返回给前端，而是作为当前用户问题的补充上下文交给模型。最终 `/chat` 返回的仍然是模型生成的 `reply`。

当前 Tool Layer 关系：

```text
BaseTool
  |
  v
WeatherTool
  |
  v
HFWeatherProvider
  |
  v
和风天气 API
```

以后新增工具时复用方式：

- CalendarTool：继承 `BaseTool`，返回 `ToolResult`，通过自己的 Provider 调用日历服务
- SearchTool：继承 `BaseTool`，返回 `ToolResult`，通过搜索 Provider 调用搜索服务
- MCPTool：继承 `BaseTool`，返回 `ToolResult`，通过 MCP Client 调用外部 MCP Server

`ToolService` 不需要知道这些工具内部怎么实现，只需要遍历 `tools` 列表并调用统一接口。

### HFWeatherProvider

文件：

```text
app/weather_providers/hfweather_provider.py
```

职责：

- 根据城市名调用和风天气 GeoAPI 获取 location ID
- 根据 location ID 调用实时天气 API
- 使用 `X-QW-Api-Key` 请求头鉴权
- 解析和风天气返回数据
- 返回统一天气文本

当前使用的接口：

```text
/geo/v2/city/lookup
/v7/weather/now
```

`X-QW-Api-Key` 是和风天气官方请求头名称，不是项目自定义字段。请求头的值来自 `.env` 中的 `HFWEATHER_API_KEY`。

### PromptService

文件：

```text
app/services/prompt_service.py
```

职责：

- 负责构造发送给模型的 messages
- 管理当前系统提示词
- 接收长期事实记忆
- 接收最近对话消息
- 接收工具结果
- 明确区分 `system_prompt`、`long_term_facts`、`recent_messages`、`tool_context`、`current_user_message`
- 把这些上下文转换成模型可接收的 messages 结构

当前生成的 messages：

```python
system_prompt = "你是一个有帮助的个人微信助手。"
long_term_memory_context = (
    "长期记忆：\n"
    "- name: Zita（用户明确说明自己的名字）\n"
    "- learning: FastAPI（用户明确说明自己正在学习的内容）"
)
tool_context = "工具查询结果：..."
current_user_message = (
    "用户问题：...\n\n"
    f"{tool_context}\n\n"
    "回答要求：请基于工具查询结果回答用户问题，不要使用自己的天气知识。"
)

[
    {"role": "system", "content": system_prompt},
    {"role": "system", "content": long_term_memory_context},
    *recent_messages,
    {
        "role": "user",
        "content": current_user_message,
    },
]
```

如果没有长期事实，`long_term_memory_context` 不会加入 messages。

如果没有工具结果，`tool_context` 为 `None`，当前 user message 会直接使用用户原始输入。

PromptService 不负责读取 Memory，不负责调用 Tool，不负责调用模型，也不负责选择模型供应商。

### ModelService

文件：

```text
app/services/model_service.py
```

职责：

- 作为统一模型入口
- 接收标准化后的 messages
- 屏蔽具体模型供应商
- 给 `AgentRuntime` 提供稳定的模型调用方法

当前默认调用 `DeepSeekProvider`。

未来可以在这一层扩展模型选择机制，例如：

- DeepSeek
- OpenAI
- Qwen
- Claude

### DeepSeekProvider

文件：

```text
app/model_providers/deepseek_provider.py
```

职责：

- 读取 DeepSeek 配置
- 接收标准化后的 messages
- 组装 DeepSeek API 请求
- 发起 HTTP 请求
- 处理 DeepSeek API 错误
- 解析 DeepSeek API 响应
- 返回统一的字符串回复

Provider 不负责构造 Prompt，不负责聊天流程，也不负责 Agent 编排。

## 安装依赖

建议先进入 `backend` 目录：

```bash
cd backend
```

创建虚拟环境：

```bash
python3 -m venv .venv
```

激活虚拟环境：

```bash
source .venv/bin/activate
```

安装依赖：

```bash
pip install -r requirements.txt
```

## 运行单元测试

在 `backend` 目录下执行：

```bash
python3 -m pytest tests
```

当前测试不调用真实 DeepSeek API，不启动 `/chat` 端到端接口，不接数据库，也不接微信。

当前测试覆盖：

- `PlannerService`
  - 天气类消息会生成 `ToolStep(weather)`
  - 普通消息不会生成 ToolStep
  - 所有 Plan 都包含短期记忆、长期记忆和 LLM 步骤
  - RePlan 失败后只生成 LLMStep，不包含 ToolStep
- `AgentRuntime`
  - Runtime 会根据 Plan 决定是否执行 Tool
  - Plan 中没有 ToolStep 时不会调用 Tool
  - Plan 中有 ToolStep 时会把工具结果传给 Prompt
  - Runtime 会构建 Observation 并交给 Reflection
  - Reflection failed 后会调用 Planner 生成 RePlan
  - RePlan 后不会再次执行 ToolStep
  - Runtime 会保存短期对话并提取长期记忆
- `MemoryExecutor`
  - 执行 `MemoryStep(short_term)` 后写入 recent_messages
  - 执行 `MemoryStep(long_term)` 后写入 long_term_facts
- `ReflectionService`
  - 空回复会返回 failed
  - Observation 中存在 execution_errors 时会返回 failed
  - 正常回复会返回 success
  - `should_replan` 当前保持 false
- `ShortTermMemory`
  - 保存 user 和 assistant 消息后，可以读取 recent_messages
  - 超过最大长度后，只保留最近消息
  - clear_session 只清空目标 session 的短期记忆
- `LongTermMemory`
  - 可以从“我叫xxx”“我是xxx”“我在学xxx”中提取结构化长期事实
  - 普通消息不会提取长期事实
  - 不同 session 的长期事实互不影响
  - 重复事实不会重复保存
  - clear_session 只清空目标 session 的长期事实
- `MemoryExtractorService`
  - 正常 JSON 可以解析出结构化 facts
  - `{"facts":[]}` 返回空列表
  - 非 JSON 返回空列表
  - facts 不是 list 时返回空列表
  - 不完整 fact 会被过滤
- `MemoryService`
  - get_memory_snapshot 可以同时返回短期记忆和长期事实
  - clear_session_memory 可以同时清空短期记忆和长期事实
- `ToolService`
  - 命中工具时返回 ToolResult 和 ToolTrace
  - 普通消息不触发工具，并返回未使用工具的 ToolTrace
  - 工具抛出 ToolException 时返回失败的 ToolResult 和 ToolTrace
- `WeatherTool`
  - can_handle 可以识别“天气”“下雨”“气温”
  - metadata 返回工具名称、用途和触发关键词
  - 可以从“杭州今天天气怎么样”“上海会下雨吗”“北京气温多少”中提取城市
  - 无法提取城市时使用默认城市
  - 普通消息不会被 WeatherTool 处理
  - run 返回 ToolResult
- `HFWeatherProvider`
  - 使用 fake provider 测试，不真实请求和风天气
  - GeoAPI 成功时能解析 location ID
  - 实时天气 API 成功时能格式化统一天气文本
  - API 数据异常时抛出受控异常
- `PromptService`
  - 无工具结果时，messages 包含 system、recent_messages、当前 user message
  - 有工具结果时，当前 user message 包含工具上下文
  - tool_result 不会作为独立用户消息插到当前问题之前
  - 有长期事实时，messages 包含长期记忆 context
  - 长期记忆 context 位于 recent_messages 之前
  - 空 long_term_facts 不会额外插入长期记忆 message

## 创建 .env

复制环境变量示例文件：

```bash
cp .env.example .env
```

然后编辑 `.env`：

```env
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
HFWEATHER_API_KEY=your_hfweather_api_key_here
HFWEATHER_API_HOST=https://your_hfweather_api_host
HFWEATHER_DEFAULT_CITY=杭州
```

请把：

- `your_api_key_here` 替换成你自己的 DeepSeek API Key
- `your_hfweather_api_key_here` 替换成你自己的和风天气 API Key
- `HFWEATHER_API_HOST` 替换成和风天气控制台中配置的 API Host

和风天气请求使用请求头：

```text
X-QW-Api-Key: HFWEATHER_API_KEY
```

## 启动服务

在 `backend` 目录下执行：

```bash
uvicorn app.main:app --reload
```

默认服务地址：

```text
http://127.0.0.1:8000
```

FastAPI 自动文档地址：

```text
http://127.0.0.1:8000/docs
```

## 使用 curl 测试接口

```bash
curl -X POST "http://127.0.0.1:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "你好", "session_id": "user-a"}'
```

正常返回格式：

```json
{
  "reply": "你好，我是你的个人助手。",
  "debug": {
    "used_tool": false,
    "tool_name": null,
    "tool_result": null,
    "tool_success": true,
    "tool_error": null,
    "tool_metadata": null,
    "session_id": "user-a",
    "recent_messages_count": 0,
    "long_term_facts_count": 0,
    "extracted_facts_count": 0,
    "extracted_facts": [],
    "prompt_messages_count": 2,
    "has_tool_context": false,
    "reflection_status": "success",
    "reflection_reason": null,
    "should_replan": false
  }
}
```

实际回复内容由 DeepSeek 模型生成，可能和示例略有不同。

## 测试短期记忆和天气工具

天气类问题会触发 WeatherTool，并通过 HFWeatherProvider 请求和风天气。

指定城市查询：

```bash
curl -X POST "http://127.0.0.1:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "北京气温多少", "session_id": "user-a"}'
```

模型会优先参考工具结果生成回复，例如：

```json
{
  "reply": "北京当前晴，气温 30℃，体感 32℃，湿度 45%，南风 2 级。",
  "debug": {
    "used_tool": true,
    "tool_name": "weather",
    "tool_result": "北京当前晴，气温 30℃，体感 32℃，湿度 45%，南风 2 级。",
    "tool_success": true,
    "tool_error": null,
    "tool_metadata": {
      "city": "北京",
      "provider": "hfweather"
    },
    "session_id": "user-a",
    "recent_messages_count": 0,
    "long_term_facts_count": 0,
    "extracted_facts_count": 0,
    "extracted_facts": [],
    "prompt_messages_count": 2,
    "has_tool_context": true,
    "reflection_status": "success",
    "reflection_reason": null,
    "should_replan": false
  }
}
```

默认城市查询：

```bash
curl -X POST "http://127.0.0.1:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "今天天气怎么样", "session_id": "user-a"}'
```

如果 `HFWEATHER_DEFAULT_CITY=杭州`，则 `debug.tool_result` 应体现杭州天气。

然后可以通过本地调试接口查看当前进程内的记忆快照：

```bash
curl http://127.0.0.1:8000/debug/memory
```

`GET /debug/memory` 默认查看 `"default"` session。

查看指定 session：

```bash
curl http://127.0.0.1:8000/debug/memory/user-a
```

返回示例：

```json
{
  "session_id": "user-a",
  "recent_messages": [
    {
      "role": "user",
      "content": "杭州今天天气怎么样？"
    },
    {
      "role": "assistant",
      "content": "杭州今天多云，气温 25-31℃，傍晚可能有暴雨。"
    }
  ],
  "long_term_facts": [
    {
      "key": "name",
      "value": "Zita",
      "reason": "用户明确说明自己的名字"
    }
  ]
}
```

清空指定 session 的短期记忆和长期事实：

```bash
curl -X DELETE http://127.0.0.1:8000/debug/memory/user-a
```

返回示例：

```json
{
  "session_id": "user-a",
  "cleared": true
}
```

所有 `/debug/*` 接口仅用于本地开发调试，生产环境不应暴露。

## 使用 Swagger 验证 Chat Debug

启动服务后打开：

```text
http://127.0.0.1:8000/docs
```

在 `POST /chat` 中先测试普通消息：

```json
{
  "message": "你好",
  "session_id": "user-a"
}
```

如果没有触发工具，`debug.used_tool` 应为 `false`：

```json
{
  "reply": "...",
  "debug": {
    "used_tool": false,
    "tool_name": null,
    "tool_result": null,
    "tool_success": true,
    "tool_error": null,
    "tool_metadata": null,
    "session_id": "user-a",
    "recent_messages_count": 0,
    "long_term_facts_count": 0,
    "extracted_facts_count": 0,
    "extracted_facts": [],
    "prompt_messages_count": 2,
    "has_tool_context": false,
    "reflection_status": "success",
    "reflection_reason": null,
    "should_replan": false
  }
}
```

再测试天气消息：

```json
{
  "message": "北京气温多少",
  "session_id": "user-a"
}
```

如果触发天气工具，`debug.used_tool` 应为 `true`，`debug.tool_name` 应为 `weather`：

```json
{
  "reply": "...",
  "debug": {
    "used_tool": true,
    "tool_name": "weather",
    "tool_result": "北京当前晴，气温 30℃，体感 32℃，湿度 45%，南风 2 级。",
    "tool_success": true,
    "tool_error": null,
    "tool_metadata": {
      "city": "北京",
      "provider": "hfweather"
    },
    "session_id": "user-a",
    "recent_messages_count": 2,
    "long_term_facts_count": 0,
    "extracted_facts_count": 0,
    "extracted_facts": [],
    "prompt_messages_count": 4,
    "has_tool_context": true,
    "reflection_status": "success",
    "reflection_reason": null,
    "should_replan": false
  }
}
```

再测试无法提取城市的天气消息：

```json
{
  "message": "今天天气怎么样",
  "session_id": "user-a"
}
```

如果 `HFWEATHER_DEFAULT_CITY=杭州`，则 `debug.tool_result` 应体现杭州天气。

## 使用 Swagger 验证 Session 隔离

先用 `user-a` 发送：

```json
{
  "message": "我叫张三",
  "session_id": "user-a"
}
```

再用 `user-b` 发送：

```json
{
  "message": "我叫李四",
  "session_id": "user-b"
}
```

然后分别追问：

```json
{
  "message": "我叫什么名字？",
  "session_id": "user-a"
}
```

```json
{
  "message": "我叫什么名字？",
  "session_id": "user-b"
}
```

预期现象：

- `user-a` 的 debug 中 `session_id` 为 `"user-a"`
- `user-b` 的 debug 中 `session_id` 为 `"user-b"`
- 两个 session 的 `recent_messages_count` 独立增长
- 模型回答时只应参考当前 session 的历史消息

如果请求不传 `session_id`，后端会使用 `"default"`：

```json
{
  "message": "你好"
}
```

## 使用 Swagger 验证 LongTermMemory V2

先发送一条包含长期事实的消息：

```json
{
  "message": "以后叫我 Zita",
  "session_id": "user-a"
}
```

这一轮会在模型回复后调用 MemoryExtractorService 自动提取长期事实，但本轮 Prompt 中还不会使用这条新事实，所以 `long_term_facts_count` 可能仍为 `0`。

如果提取成功，debug 中会出现：

```json
{
  "extracted_facts_count": 1,
  "extracted_facts": [
    {
      "key": "name",
      "value": "Zita",
      "reason": "用户明确说明自己的名字"
    }
  ]
}
```

再发送下一轮消息：

```json
{
  "message": "我叫什么名字？",
  "session_id": "user-a"
}
```

预期现象：

- debug 中 `session_id` 为 `"user-a"`
- debug 中 `long_term_facts_count` 至少为 `1`
- Prompt 会在 recent_messages 之前注入长期事实
- 模型应能参考长期事实回答用户叫 Zita

## 使用 Swagger 验证 Memory Debug

查看指定 session 的记忆快照：

```text
GET /debug/memory/user-a
```

预期返回：

```json
{
  "session_id": "user-a",
  "recent_messages": [],
  "long_term_facts": []
}
```

清空指定 session 的记忆：

```text
DELETE /debug/memory/user-a
```

预期返回：

```json
{
  "session_id": "user-a",
  "cleared": true
}
```

清空后再次查看：

```text
GET /debug/memory/user-a
```

应看到 `recent_messages` 和 `long_term_facts` 都为空。

## 使用 Swagger 验证 Prompt Debug

`POST /debug/prompt` 用于查看某个请求最终构建出的 Prompt messages。

该接口仅用于本地开发调试，生产环境不应暴露。它不会调用 DeepSeek，不会保存短期记忆，也不会提取或保存长期事实。

请求示例：

```json
{
  "message": "杭州今天天气怎么样？",
  "session_id": "user-a"
}
```

返回示例：

```json
{
  "session_id": "user-a",
  "used_tool": true,
  "tool_name": "weather",
  "tool_result": "杭州当前多云，气温 25℃，体感 27℃，湿度 72%，东南风 1 级。",
  "recent_messages_count": 0,
  "long_term_facts_count": 0,
  "messages": [
    {
      "role": "system",
      "content": "你是一个有帮助的个人微信助手。"
    },
    {
      "role": "user",
      "content": "用户问题：杭州今天天气怎么样？\n\n工具查询结果：杭州当前多云，气温 25℃，体感 27℃，湿度 72%，东南风 1 级。\n\n回答要求：请基于工具查询结果回答用户问题，不要使用自己的天气知识。"
    }
  ]
}
```

如果当前 session 已经有长期事实，`messages` 中应出现长期记忆 message，并且它会位于 recent_messages 之前。

## 当前阶段完成了什么

- 创建 FastAPI 后端项目结构
- 提供 `POST /chat` 接口
- 使用 Pydantic 定义请求和响应格式
- 使用 `.env` 管理 DeepSeek 配置
- 引入 `ChatService` 作为聊天接口服务层
- 引入 `AgentRuntime` 作为 Agent 执行协调层
- 引入 `PlannerService` 作为 rule-based 计划生成层
- `PlannerService` 只生成 Plan，不调用 Tool、Memory 或 LLM
- `PlannerService` 支持 `create_replan()`，失败后生成 LLM-only Plan
- RePlan V1 不使用 AI Planner，不使用 LLM 做规划
- RePlan V1 不是 Retry，失败后不会重复执行工具步骤
- 引入 Execution Layer，由 Executor 执行 Plan Step
- `AgentRuntime` 根据 Plan 调度 Memory、Tool 和 LLM Executor
- `AgentRuntime` 支持最多 2 次执行循环，防止 RePlan 死循环
- 引入 `Observation` 作为 Runtime 和 Reflection 之间的数据协议
- `AgentRuntime` 执行完成后构建 Observation
- 引入 `ReflectionService` 作为 rule-based 结果评价层
- `ReflectionService` 接收 Observation 作为输入
- `ReflectionService` 只评价结果，不执行 Retry 或 RePlan
- 引入 `PromptService` 作为模型输入构造层
- `PromptService` 明确区分 system prompt、历史消息、工具上下文和当前用户消息
- 引入 `MemoryService` 作为记忆能力入口
- 引入 `ShortTermMemory` 使用内存 dict + list 按 session_id 保存短期对话
- 引入 `LongTermMemory` 使用内存 dict + list 按 session_id 保存结构化长期事实
- 引入 `MemoryExtractorService` 复用 ModelService 自动提取长期记忆
- Memory V2 要求 LLM 输出 `{"facts":[{"key":"...","value":"...","reason":"..."}]}`
- 长期事实会在下一轮注入 Prompt，并放在 recent_messages 之前
- `POST /chat` 支持可选 `session_id`，不传时默认使用 `"default"`
- 短期记忆支持基于 `session_id` 的会话隔离
- 引入 `ToolService` 作为工具路由入口
- `ToolService` 通过 tools 列表注册并遍历工具
- 引入 `BaseTool` 作为所有工具的统一抽象
- 引入 `ToolMetadata` 描述工具名称、用途和触发关键词
- 引入 `ToolResult` 作为统一工具返回结构
- 引入 `ToolException` 作为工具失败时的统一异常类型
- 引入 `ToolTrace` 记录工具调用过程
- 引入 `HFWeatherProvider` 适配和风天气 API
- `WeatherTool` 依赖 HFWeatherProvider，不直接编写 HTTP 请求
- `WeatherTool` 继承 `BaseTool`，提供 `metadata`、`can_handle()` 和 `run()` 方法
- `WeatherTool` 支持从简单天气问题中提取城市名，无法提取时使用默认城市
- 天气类问题可以触发真实天气工具结果
- 工具结果会进入 Prompt，由模型生成最终回复
- `/chat` 支持可选 debug 字段，方便观察本轮 Agent 执行过程
- `/chat` debug 支持返回 `extracted_facts_count` 和 `extracted_facts`
- `/chat` debug 支持返回 `tool_success`、`tool_error` 和 `tool_metadata`
- `/chat` debug 支持返回 `reflection_status`、`reflection_reason` 和 `should_replan`
- `/debug/memory` 支持查看 default session 的记忆快照
- `/debug/memory/{session_id}` 支持查看指定 session 的短期记忆和长期事实
- `DELETE /debug/memory/{session_id}` 支持清空指定 session 的短期记忆和长期事实
- `/debug/prompt` 支持查看最终构建出的 Prompt messages，不调用 DeepSeek、不写入 Memory
- 引入 `DebugPromptRequest` 和 `DebugPromptResponse` 作为 Prompt Debug 的请求响应结构
- 增加 pytest 单元测试，覆盖 Runtime、Observation/Reflection、Memory、Tool 和 Prompt 核心模块
- 引入 `ModelService` 作为统一模型入口
- 引入 `DeepSeekProvider` 作为 DeepSeek 供应商适配层
- 保持 `POST /chat` 可用，并通过可选 debug 字段返回当前 session 信息

## 后续可以扩展什么

建议继续按分层方式逐步扩展：

- 增加更多工具，并统一继承 `BaseTool`
- 为 Calendar、Search、MCP Tool 设计各自的 Provider 层
- 后续再考虑真正的 tool calling / function calling
- 在 `ModelService` 中增加 Provider 选择机制
- 增加 OpenAI、Qwen、Claude Provider
- 增强长期记忆提取规则
- 后续再考虑用户偏好和人物画像
- 增加对话摘要能力
- 后续再考虑数据库或 Redis 存储
- 增加提示词管理
- 接入微信消息收发
- 增加日志和监控
