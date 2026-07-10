from app.services.prompt_service import PromptService

NAME_FACT = {
    "key": "name",
    "value": "张三",
    "reason": "用户明确说明自己的名字",
}

LEARNING_FACT = {
    "key": "learning",
    "value": "FastAPI",
    "reason": "用户明确说明自己正在学习的内容",
}


def test_build_messages_without_tool_result() -> None:
    service = PromptService()
    recent_messages = [
        {"role": "user", "content": "我叫张三"},
        {"role": "assistant", "content": "好的，我记住了。"},
    ]

    messages = service.build_messages("我叫什么名字？", recent_messages)

    assert messages == [
        {
            "role": "system",
            "content": "你是一个有帮助的个人微信助手。",
        },
        *recent_messages,
        {
            "role": "user",
            "content": "我叫什么名字？",
        },
    ]


def test_build_messages_with_tool_result_contains_tool_context() -> None:
    service = PromptService()

    messages = service.build_messages(
        "杭州今天天气怎么样？",
        tool_result="杭州今天多云，气温 25-31℃，傍晚可能有小雨。",
    )

    user_message = messages[-1]
    assert user_message["role"] == "user"
    assert "用户问题：杭州今天天气怎么样？" in user_message["content"]
    assert "工具查询结果：杭州今天多云，气温 25-31℃，傍晚可能有小雨。" in user_message["content"]
    assert "回答要求：请基于工具查询结果回答用户问题，不要使用自己的天气知识。" in user_message["content"]


def test_tool_result_is_not_inserted_as_independent_user_message() -> None:
    service = PromptService()

    messages = service.build_messages(
        "杭州今天天气怎么样？",
        tool_result="杭州今天多云，气温 25-31℃，傍晚可能有小雨。",
    )

    user_messages = [message for message in messages if message["role"] == "user"]

    assert len(user_messages) == 1
    assert user_messages[0] == messages[-1]


def test_build_messages_with_long_term_facts_contains_memory_context() -> None:
    service = PromptService()

    messages = service.build_messages(
        "我叫什么名字？",
        long_term_facts=[NAME_FACT, LEARNING_FACT],
    )

    assert messages[1] == {
        "role": "system",
        "content": (
            "长期记忆：\n"
            "- name: 张三（用户明确说明自己的名字）\n"
            "- learning: FastAPI（用户明确说明自己正在学习的内容）"
        ),
    }


def test_long_term_facts_are_inserted_before_recent_messages() -> None:
    service = PromptService()
    recent_messages = [
        {"role": "user", "content": "上一轮用户消息"},
        {"role": "assistant", "content": "上一轮助手回复"},
    ]

    messages = service.build_messages(
        "当前问题",
        recent_messages=recent_messages,
        long_term_facts=[NAME_FACT],
    )

    assert messages[1]["content"] == "长期记忆：\n- name: 张三（用户明确说明自己的名字）"
    assert messages[2] == recent_messages[0]
    assert messages[3] == recent_messages[1]


def test_empty_long_term_facts_do_not_add_memory_message() -> None:
    service = PromptService()

    messages = service.build_messages("你好", long_term_facts=[])

    assert messages == [
        {
            "role": "system",
            "content": "你是一个有帮助的个人微信助手。",
        },
        {
            "role": "user",
            "content": "你好",
        },
    ]
