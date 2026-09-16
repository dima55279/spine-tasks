from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from qa_api.dependencies import get_ask_service
from qa_api.main import create_app
from qa_api.schemas import ContextReference, RetrievalResult, RetrievedChunk
from qa_api.service import (
    AskQuestion,
    Clock,
    FakeComposer,
    FakeGateway,
    InMemoryRequestStore,
    SlowComposer,
)


def valid_request(**overrides) -> dict:
    payload = {
        "workspace_id": "alpha",
        "user_id": "u-1",
        "scopes": ["all-employees"],
        "question": "Какой размер суточных?",
        "request_id": "r-1",
    }
    payload.update(overrides)
    return payload


def travel_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        workspace_id="alpha",
        required_scope="all-employees",
        text="С 1 сентября суточные для поездок по России составляют 1200 рублей в день.",
        reference=ContextReference(
            source_id="travel-policy",
            revision_id="11111111-1111-4111-8111-222222222222",
            chunk_id="travel-v2-daily",
            locator={"heading": "Суточные", "paragraph": 1},
        ),
    )


def engineering_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        workspace_id="alpha",
        required_scope="engineering",
        text="Кодовое имя прототипа — Aurora.",
        reference=ContextReference(
            source_id="engineering-only",
            revision_id="33333333-3333-4333-8333-333333333333",
            chunk_id="engineering-name",
            locator={"heading": "Кодовое имя", "paragraph": 1},
        ),
    )


def service_with(
    *,
    gateway: FakeGateway | None = None,
    composer=None,
    events: list[dict] | None = None,
    timeout: float = 2.0,
) -> AskQuestion:
    gateway = gateway or FakeGateway(
        {
            "Какой размер суточных?": RetrievalResult(
                chunks=(travel_chunk(),),
                strategy="fake",
                index_version="fake-v1",
                policy_version="access-policy-v1",
            ),
            "Как называется закрытый прототип?": RetrievalResult(
                chunks=(engineering_chunk(),),
                strategy="fake",
                index_version="fake-v1",
                policy_version="access-policy-v1",
            ),
        }
    )
    return AskQuestion(
        gateway=gateway,
        composer=composer or FakeComposer(),
        request_store=InMemoryRequestStore(),
        clock=Clock(),
        compose_timeout_seconds=timeout,
        trace_id_factory=lambda: "trace-test",
        events=events,
    )


@pytest.fixture
def app() -> FastAPI:
    app = create_app()

    async def override_service() -> AskQuestion:
        return service_with()

    app.dependency_overrides[get_ask_service] = override_service
    return app


async def post(app: FastAPI, payload: dict):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post("/api/v1/ask", json=payload)


@pytest.mark.asyncio
async def test_ask_returns_citation(app: FastAPI) -> None:
    response = await post(app, valid_request())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["citations"][0]["source_id"] == "travel-policy"
    assert body["citations"][0]["locator"] == {"heading": "Суточные", "paragraph": 1}
    assert body["trace_id"] == "trace-test"


@pytest.mark.asyncio
async def test_unknown_field_returns_422(app: FastAPI) -> None:
    response = await post(app, valid_request(unexpected="value"))

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_empty_question_returns_422(app: FastAPI) -> None:
    response = await post(app, valid_request(question=""))

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_repeated_request_id_returns_same_logical_response(app: FastAPI) -> None:
    first = await post(app, valid_request(request_id="repeat-1"))
    second = await post(app, valid_request(request_id="repeat-1"))

    assert first.status_code == 200
    assert second.status_code == 200
    first_body = first.json()
    second_body = second.json()
    assert first_body["trace_id"] == second_body["trace_id"]
    assert first_body["citations"] == second_body["citations"]
    assert first_body["answer"] == second_body["answer"]


@pytest.mark.asyncio
async def test_foreign_workspace_does_not_return_data(app: FastAPI) -> None:
    response = await post(
        app,
        valid_request(
            workspace_id="beta",
            question="Какой размер суточных?",
            request_id="beta-1",
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "abstained"
    assert body["citations"] == []
    assert "NO_CONTEXT" in body["reasons"]


@pytest.mark.asyncio
async def test_composer_timeout_returns_503() -> None:
    app = create_app()

    async def override_service() -> AskQuestion:
        return service_with(composer=SlowComposer(), timeout=0.01)

    app.dependency_overrides[get_ask_service] = override_service

    response = await post(app, valid_request(request_id="timeout-1"))

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "COMPOSER_TIMEOUT"
    assert body["error"]["trace_id"]
    assert body["error"]["retryable"] is True


@pytest.mark.asyncio
async def test_trace_id_is_present_in_response_and_logs() -> None:
    events: list[dict] = []
    app = create_app()

    async def override_service() -> AskQuestion:
        return service_with(events=events)

    app.dependency_overrides[get_ask_service] = override_service

    response = await post(app, valid_request(request_id="trace-1"))

    assert response.status_code == 200
    assert response.json()["trace_id"] == "trace-test"
    assert any(event["trace_id"] == "trace-test" for event in events)


@pytest.mark.asyncio
async def test_health_endpoints(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        live = await client.get("/health/live")
        ready = await client.get("/health/ready")

    assert live.json() == {"status": "ok"}
    assert ready.json() == {"status": "ready"}
