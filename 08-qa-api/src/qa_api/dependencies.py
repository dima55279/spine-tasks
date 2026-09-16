from __future__ import annotations

import json
from pathlib import Path

from qa_api.schemas import ContextReference, RetrievalResult, RetrievedChunk
from qa_api.service import AskQuestion, Clock, FakeComposer, FakeGateway, InMemoryRequestStore

_request_store = InMemoryRequestStore()


def build_fake_gateway(path: Path = Path("data/fixtures/fake-results.json")) -> FakeGateway:
    payload = json.loads(path.read_text(encoding="utf-8"))
    answers: dict[str, RetrievalResult] = {}
    for question, chunks in payload["answers"].items():
        parsed = tuple(
            RetrievedChunk(
                workspace_id=item["workspace_id"],
                required_scope=item["required_scope"],
                text=item["text"],
                reference=ContextReference.model_validate(item["reference"]),
            )
            for item in chunks
        )
        answers[question] = RetrievalResult(
            chunks=parsed,
            strategy="configured-fake",
            index_version=payload["index_version"],
            policy_version="access-policy-v1",
        )
    return FakeGateway(answers)


async def get_ask_service() -> AskQuestion:
    return AskQuestion(
        gateway=build_fake_gateway(),
        composer=FakeComposer(),
        request_store=_request_store,
        clock=Clock(),
    )
