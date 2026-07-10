from app.services.memory_service import MemoryService


def test_get_memory_snapshot_contains_recent_messages_and_long_term_facts() -> None:
    service = MemoryService()

    service.save_conversation("user-a", "你好", "你好，我是你的个人助手。")
    service.extract_and_save_long_term_facts("user-a", "我叫张三")

    snapshot = service.get_memory_snapshot("user-a")

    assert snapshot == {
        "session_id": "user-a",
        "recent_messages": [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好，我是你的个人助手。"},
        ],
        "long_term_facts": [
            {
                "key": "name",
                "value": "张三",
                "reason": "用户明确说明自己的名字",
            }
        ],
    }


def test_clear_session_memory_removes_recent_messages_and_long_term_facts() -> None:
    service = MemoryService()

    service.save_conversation("user-a", "你好", "你好，我是你的个人助手。")
    service.extract_and_save_long_term_facts("user-a", "我叫张三")

    service.clear_session_memory("user-a")

    assert service.get_memory_snapshot("user-a") == {
        "session_id": "user-a",
        "recent_messages": [],
        "long_term_facts": [],
    }
