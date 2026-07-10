"""
AgentRuntime

负责协调一轮 Agent 的完整执行过程。

Runtime 位于 ChatService 之下、Planner/Executor 之上。
它存在的原因是把“Agent 如何运行”的流程从接口服务中拆出来，
并按 Planner 生成的 Plan 调度 Executor，避免 Runtime 直接承担
不同 Step 的执行细节。执行完成后，Runtime 会调用 ReflectionService
评价 Observation。如果结果失败，Runtime 会请求 Planner 生成 RePlan，
但 Runtime 不自己制定新计划。
"""

from app.executors.base_executor import BaseExecutor, ExecutionContext
from app.executors import llm_executor as llm_executor_module
from app.executors import memory_executor as memory_executor_module
from app.executors import tool_executor as tool_executor_module
from app.executors.llm_executor import llm_executor
from app.executors.memory_executor import memory_executor
from app.executors.tool_executor import tool_executor
from app.services.memory_extractor_service import memory_extractor_service
from app.services.memory_service import memory_service
from app.services.model_service import model_service
from app.services.observation_service import Observation
from app.services.planner_service import PlanStepType, planner_service
from app.services.prompt_service import prompt_service
from app.services.reflection_service import reflection_service
from app.services.tool_service import tool_service
from app.tools.tool_trace import ToolTrace


class AgentRuntime:
    """
    Agent 执行协调者。

    职责：
    - 调用 PlannerService 生成执行计划
    - 按 Plan 调度对应 Executor
    - 维护一轮执行的 ExecutionContext
    - 构建本轮 Observation
    - 调用 ReflectionService 评价本轮结果
    - 在最大次数内执行 RePlan
    - 保存短期记忆
    - 提取并保存长期记忆
    - 返回回复和本轮 debug 信息

    不负责：
    - HTTP 请求处理
    - API 请求响应结构定义
    - 制定执行计划
    - 直接执行 Memory、Tool、LLM Step
    - 编写 Reflection 评价规则
    - 决定 RePlan 内容
    - 具体 Memory 存储实现
    - 具体 Tool 执行细节
    - 具体模型 Provider 调用细节
    """

    def __init__(self) -> None:
        self.max_iterations = 2
        self.executors: dict[str, BaseExecutor] = {
            PlanStepType.MEMORY: memory_executor,
            PlanStepType.TOOL: tool_executor,
            PlanStepType.LLM: llm_executor,
        }

    async def run(
        self,
        message: str,
        session_id: str = "default",
    ) -> tuple[str, dict[str, object]]:
        """
        执行一轮 Agent 对话。

        Args:
            message: 用户本轮输入。
            session_id: 会话标识，用于隔离不同用户或不同会话的记忆。

        Returns:
            助手回复内容和本轮 Agent 执行调试信息。
        """
        plan = planner_service.plan(message)
        self._sync_executor_dependencies()

        context: ExecutionContext | None = None
        tool_trace: ToolTrace | None = None
        observation: Observation | None = None
        reflection_result = None

        for iteration in range(self.max_iterations):
            context = self._create_context(message, session_id, context)
            context, tool_trace, observation, reflection_result = await self._execute_plan(
                plan,
                context,
                message,
            )

            if reflection_result.status == "success":
                break

            if (
                reflection_result.should_replan
                and iteration < self.max_iterations - 1
                and hasattr(planner_service, "create_replan")
            ):
                plan = planner_service.create_replan(reflection_result)
                continue

            break

        if context is None or tool_trace is None or observation is None or reflection_result is None:
            context = ExecutionContext(message=message, session_id=session_id)
            tool_trace = self._default_tool_trace(message)
            observation = self._build_observation(context, tool_trace)
            reflection_result = reflection_service.reflect(observation)

        debug = {
            "used_tool": tool_trace.used_tool,
            "tool_name": tool_trace.tool_name,
            "tool_result": context.tool_result,
            "tool_success": tool_trace.success,
            "tool_error": tool_trace.error,
            "tool_metadata": tool_trace.metadata,
            "session_id": session_id,
            "recent_messages_count": len(context.recent_messages),
            "long_term_facts_count": len(context.long_term_facts),
            "prompt_messages_count": observation.prompt_messages_count,
            "has_tool_context": context.tool_result is not None,
            "reflection_status": reflection_result.status,
            "reflection_reason": reflection_result.reason,
            "should_replan": reflection_result.should_replan,
        }
        memory_service.save_conversation(session_id, message, context.reply)
        extracted_facts = await memory_extractor_service.extract_facts(message)
        memory_service.save_long_term_facts(session_id, extracted_facts)
        debug["extracted_facts_count"] = len(extracted_facts)
        debug["extracted_facts"] = extracted_facts
        return context.reply, debug

    async def _execute_plan(
        self,
        plan,
        context: ExecutionContext,
        message: str,
    ) -> tuple[ExecutionContext, ToolTrace, Observation, object]:
        """
        执行一个 Plan，并返回执行后的观察和评价。

        Args:
            plan: Planner 生成的执行计划。
            context: 本轮执行上下文。
            message: 用户本轮输入。

        Returns:
            执行上下文、工具轨迹、观察结果和评价结果。
        """
        # Runtime 只调度 Step，具体执行细节交给对应 Executor。
        for step in plan.steps:
            executor = self.executors.get(step.step_type)
            if executor is not None:
                await executor.execute(step, context)

        tool_trace = context.tool_trace or self._default_tool_trace(message)
        observation = self._build_observation(context, tool_trace)
        reflection_result = reflection_service.reflect(observation)
        return context, tool_trace, observation, reflection_result

    def _create_context(
        self,
        message: str,
        session_id: str,
        previous_context: ExecutionContext | None,
    ) -> ExecutionContext:
        """
        创建一次 Plan 执行使用的上下文。

        Args:
            message: 用户本轮输入。
            session_id: 会话标识。
            previous_context: 上一次执行留下的上下文。

        Returns:
            新的执行上下文。
        """
        context = ExecutionContext(message=message, session_id=session_id)
        if previous_context is None:
            return context

        context.recent_messages = previous_context.recent_messages
        context.long_term_facts = previous_context.long_term_facts
        context.tool_result = previous_context.tool_result
        return context

    def _default_tool_trace(self, message: str) -> ToolTrace:
        """
        构建未使用工具时的默认 ToolTrace。

        Args:
            message: 用户本轮输入。

        Returns:
            表示未使用工具的 ToolTrace。
        """
        return ToolTrace(
            used_tool=False,
            tool_name=None,
            success=True,
            input=message,
            output=None,
            error=None,
        )

    def _build_observation(
        self,
        context: ExecutionContext,
        tool_trace: ToolTrace,
    ) -> Observation:
        """
        根据执行上下文构建 Observation。

        Args:
            context: 本轮 Agent 执行共享上下文。
            tool_trace: 本轮工具调用轨迹，没有工具时使用默认 trace。

        Returns:
            本轮执行完成后的观察结果。
        """
        tool_results = []
        execution_errors = []

        if context.tool_result is not None:
            tool_results.append(
                {
                    "tool_name": tool_trace.tool_name,
                    "content": context.tool_result,
                    "success": tool_trace.success,
                }
            )

        if tool_trace.error is not None:
            execution_errors.append(tool_trace.error)

        return Observation(
            final_reply=context.reply,
            tool_results=tool_results,
            execution_errors=execution_errors,
            prompt_messages_count=len(context.messages),
            memory_used=bool(context.recent_messages or context.long_term_facts),
        )

    def _sync_executor_dependencies(self) -> None:
        """
        同步 Executor 使用的服务依赖。

        当前项目仍使用模块级 service 实例。Runtime 测试会替换这些模块级依赖，
        因此这里在调度 Executor 前同步一次，保证职责拆分后仍然容易测试。
        """
        memory_executor_module.memory_service = memory_service
        tool_executor_module.tool_service = tool_service
        llm_executor_module.prompt_service = prompt_service
        llm_executor_module.model_service = model_service


agent_runtime = AgentRuntime()
