from app.memory.short_term_memory import ShortTermMemory


def test_save_conversation_can_read_recent_messages() -> None:
    memory = ShortTermMemory()

    memory.save_conversation("user-a", "你好", "你好，我是你的个人助手。")

    assert memory.get_recent_messages("user-a") == [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好，我是你的个人助手。"},
    ]


def test_sessions_do_not_share_recent_messages() -> None:
    memory = ShortTermMemory()

    memory.save_conversation("user-a", "我叫张三", "好的，我记住了。")
    memory.save_conversation("user-b", "我叫李四", "好的，我记住了。")

    assert memory.get_recent_messages("user-a") == [
        {"role": "user", "content": "我叫张三"},
        {"role": "assistant", "content": "好的，我记住了。"},
    ]
    assert memory.get_recent_messages("user-b") == [
        {"role": "user", "content": "我叫李四"},
        {"role": "assistant", "content": "好的，我记住了。"},
    ]


def test_only_keep_recent_messages_when_exceeding_max_messages() -> None:
    memory = ShortTermMemory(max_messages=2)

    memory.save_conversation("user-a", "第一轮用户消息", "第一轮助手回复")
    memory.save_conversation("user-a", "第二轮用户消息", "第二轮助手回复")

    assert memory.get_recent_messages("user-a") == [
        {"role": "user", "content": "第二轮用户消息"},
        {"role": "assistant", "content": "第二轮助手回复"},
    ]


def test_clear_session_only_removes_target_session_messages() -> None:
    memory = ShortTermMemory()

    memory.save_conversation("user-a", "用户 A 消息", "助手 A 回复")
    memory.save_conversation("user-b", "用户 B 消息", "助手 B 回复")

    memory.clear_session("user-a")

    assert memory.get_recent_messages("user-a") == []
    assert memory.get_recent_messages("user-b") == [
        {"role": "user", "content": "用户 B 消息"},
        {"role": "assistant", "content": "助手 B 回复"},
    ]
