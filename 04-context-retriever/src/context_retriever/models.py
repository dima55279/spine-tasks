from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RetrievalQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    user_id: str
    scopes: frozenset[str]
    text: str = Field(min_length=1, max_length=2000)


class ContextReference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str
    revision_id: UUID
    chunk_id: str
    locator: dict[str, str | int | None]


class RetrievedChunk(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    workspace_id: str
    required_scope: str
    text: str
    reference: ContextReference


class RetrievalResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    chunks: tuple[RetrievedChunk, ...]
    strategy: str
    index_version: str


class ContextProviderError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def result_from_payload(
    chunks: list[dict[str, Any]],
    *,
    strategy: str = "configured-fake",
    index_version: str = "fake-v1",
) -> RetrievalResult:
    return RetrievalResult(
        chunks=tuple(RetrievedChunk.model_validate(chunk) for chunk in chunks),
        strategy=strategy,
        index_version=index_version,
    )
