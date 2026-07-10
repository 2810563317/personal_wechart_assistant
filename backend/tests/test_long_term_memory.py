from app.memory.long_term_memory import LongTermMemory

NAME_FACT_ZHANG_SAN = {
    "key": "name",
    "value": "张三",
    "reason": "用户明确说明自己的名字",
}

NAME_FACT_LI_SI = {
    "key": "name",
    "value": "李四",
    "reason": "用户明确说明自己的名字",
}


def test_extract_name_fact_from_wo_jiao() -> None:
    memory = LongTermMemory()

    facts = memory.extract_facts("我叫张三")

    assert facts == [NAME_FACT_ZHANG_SAN]


def test_extract_identity_fact_from_wo_shi() -> None:
    memory = LongTermMemory()

    facts = memory.extract_facts("我是程序员")

    assert facts == [
        {
            "key": "identity",
            "value": "程序员",
            "reason": "用户明确说明自己的身份",
        }
    ]


def test_extract_learning_fact_from_wo_zai_xue() -> None:
    memory = LongTermMemory()

    facts = memory.extract_facts("我在学 FastAPI")

    assert facts == [
        {
            "key": "learning",
            "value": "FastAPI",
            "reason": "用户明确说明自己正在学习的内容",
        }
    ]


def test_normal_message_does_not_extract_fact() -> None:
    memory = LongTermMemory()

    facts = memory.extract_facts("你好，今天天气怎么样？")

    assert facts == []


def test_sessions_do_not_share_long_term_facts() -> None:
    memory = LongTermMemory()

    memory.extract_and_save_facts("user-a", "我叫张三")
    memory.extract_and_save_facts("user-b", "我叫李四")

    assert memory.get_facts("user-a") == [NAME_FACT_ZHANG_SAN]
    assert memory.get_facts("user-b") == [NAME_FACT_LI_SI]


def test_duplicate_fact_is_not_saved_twice() -> None:
    memory = LongTermMemory()

    memory.extract_and_save_facts("user-a", "我叫张三")
    memory.extract_and_save_facts("user-a", "我叫张三")

    assert memory.get_facts("user-a") == [NAME_FACT_ZHANG_SAN]


def test_clear_session_only_removes_target_session_facts() -> None:
    memory = LongTermMemory()

    memory.extract_and_save_facts("user-a", "我叫张三")
    memory.extract_and_save_facts("user-b", "我叫李四")

    memory.clear_session("user-a")

    assert memory.get_facts("user-a") == []
    assert memory.get_facts("user-b") == [NAME_FACT_LI_SI]
