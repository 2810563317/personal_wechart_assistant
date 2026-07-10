import asyncio

from app.services.memory_extractor_service import MemoryExtractorService


class FakeModelService:
    def __init__(self, reply: str) -> None:
        self.reply = reply

    async def generate_reply(self, messages: list[dict[str, str]]) -> str:
        return self.reply


def test_extract_facts_from_valid_json() -> None:
    service = MemoryExtractorService(
        FakeModelService(
            '{"facts":[{"key":"name","value":"Zita","reason":"用户明确说明自己的名字"}]}'
        )
    )

    facts = asyncio.run(service.extract_facts("以后叫我 Zita"))

    assert facts == [
        {
            "key": "name",
            "value": "Zita",
            "reason": "用户明确说明自己的名字",
        }
    ]


def test_extract_facts_returns_empty_list_when_no_fact() -> None:
    service = MemoryExtractorService(FakeModelService('{"facts":[]}'))

    facts = asyncio.run(service.extract_facts("你好"))

    assert facts == []


def test_extract_facts_returns_empty_list_for_invalid_json() -> None:
    service = MemoryExtractorService(FakeModelService("不是 JSON"))

    facts = asyncio.run(service.extract_facts("以后叫我 Zita"))

    assert facts == []


def test_extract_facts_returns_empty_list_when_facts_is_not_list() -> None:
    service = MemoryExtractorService(FakeModelService('{"facts":{}}'))

    facts = asyncio.run(service.extract_facts("以后叫我 Zita"))

    assert facts == []


def test_extract_facts_filters_incomplete_fact() -> None:
    service = MemoryExtractorService(
        FakeModelService(
            '{"facts":[{"key":"name","value":"Zita","reason":"用户明确说明自己的名字"},{"key":"city","value":"杭州"}]}'
        )
    )

    facts = asyncio.run(service.extract_facts("以后叫我 Zita，我住在杭州"))

    assert facts == [
        {
            "key": "name",
            "value": "Zita",
            "reason": "用户明确说明自己的名字",
        }
    ]
