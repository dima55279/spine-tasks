from __future__ import annotations

from uuid import UUID

from context_retriever.models import (
    ContextReference,
    RetrievalQuery,
    RetrievalResult,
    RetrievedChunk,
)


def make_query(text: str = "Какой размер суточных?") -> RetrievalQuery:
    return RetrievalQuery(
        workspace_id="alpha",
        user_id="user-001",
        scopes=frozenset({"all-employees"}),
        text=text,
    )


def travel_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        workspace_id="alpha",
        required_scope="all-employees",
        text="С 1 сентября суточные для поездок по России составляют 1200 рублей в день.",
        reference=ContextReference(
            source_id="travel-policy",
            revision_id=UUID("11111111-1111-4111-8111-222222222222"),
            chunk_id="travel-v2-daily",
            locator={"heading": "Суточные", "paragraph": 1},
        ),
    )


def security_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        workspace_id="alpha",
        required_scope="all-employees",
        text="Подозрительное письмо нужно переслать на адрес security@example.test.",
        reference=ContextReference(
            source_id="security-policy",
            revision_id=UUID("22222222-2222-4222-8222-222222222222"),
            chunk_id="security-email",
            locator={"heading": "Подозрительные письма", "paragraph": 1},
        ),
    )


def result_with(*chunks: RetrievedChunk) -> RetrievalResult:
    return RetrievalResult(
        chunks=chunks,
        strategy="configured-fake",
        index_version="fake-v1",
    )
