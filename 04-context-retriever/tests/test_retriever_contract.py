from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from factories import make_query, result_with, security_chunk, travel_chunk
from pydantic import ValidationError

from context_retriever.contracts import Retriever
from context_retriever.demo import build_demo_retriever
from context_retriever.fake_retriever import FakeRetriever
from context_retriever.models import ContextProviderError, RetrievalQuery, RetrievalResult


async def retrieve_with_contract(retriever: Retriever, query: RetrievalQuery) -> RetrievalResult:
    return await retriever.retrieve(query)


@pytest.mark.asyncio
async def test_configured_question_returns_chunk() -> None:
    expected = result_with(travel_chunk())
    retriever = FakeRetriever({"Какой размер суточных?": expected})

    actual = await retrieve_with_contract(retriever, make_query("Какой размер суточных?"))

    assert actual == expected
    assert retriever.received_queries[0].workspace_id == "alpha"


@pytest.mark.asyncio
async def test_unknown_question_returns_empty_result() -> None:
    retriever = FakeRetriever({"Какой размер суточных?": result_with(travel_chunk())})

    actual = await retriever.retrieve(make_query("Что неизвестно?"))

    assert actual == RetrievalResult(
        chunks=(),
        strategy="configured-fake",
        index_version="fake-v1",
    )


@pytest.mark.asyncio
async def test_configured_error_is_raised() -> None:
    error = ContextProviderError("CONTEXT_PROVIDER_UNAVAILABLE")
    retriever = FakeRetriever(answers={}, errors={"Проверка недоступности Cognee": error})

    with pytest.raises(ContextProviderError, match="CONTEXT_PROVIDER_UNAVAILABLE"):
        await retriever.retrieve(make_query("Проверка недоступности Cognee"))


@pytest.mark.asyncio
async def test_fake_retriever_stores_received_queries() -> None:
    retriever = FakeRetriever({})
    query = make_query("Что неизвестно?")

    await retriever.retrieve(query)

    assert retriever.received_queries == [query]


def test_each_chunk_has_workspace_and_context_reference() -> None:
    result = result_with(travel_chunk(), security_chunk())

    for chunk in result.chunks:
        assert chunk.workspace_id == "alpha"
        assert chunk.reference.source_id
        assert chunk.reference.revision_id
        assert chunk.reference.chunk_id
        assert chunk.reference.locator


def test_empty_question_and_unknown_field_are_rejected() -> None:
    with pytest.raises(ValidationError):
        RetrievalQuery(
            workspace_id="alpha",
            user_id="user-001",
            scopes=frozenset({"all-employees"}),
            text="",
        )

    with pytest.raises(ValidationError):
        RetrievalQuery.model_validate(
            {
                "workspace_id": "alpha",
                "user_id": "user-001",
                "scopes": ["all-employees"],
                "text": "Вопрос",
                "unexpected": "value",
            }
        )


def test_result_models_are_immutable() -> None:
    result = result_with(travel_chunk())

    with pytest.raises(ValidationError):
        result.chunks = ()

    with pytest.raises(ValidationError):
        result.chunks[0].reference.chunk_id = "other"


def test_application_contract_does_not_import_cognee() -> None:
    source = Path("src/context_retriever/contracts.py").read_text(encoding="utf-8")

    assert "cognee" not in source.lower()
    assert importlib.import_module("context_retriever.contracts").Retriever is Retriever


@pytest.mark.asyncio
async def test_demo_fixture_builds_configured_retriever() -> None:
    retriever = build_demo_retriever(Path("data/fixtures/fake-results.json"))

    actual = await retriever.retrieve(make_query("Куда отправить подозрительное письмо?"))

    assert actual == result_with(security_chunk())
