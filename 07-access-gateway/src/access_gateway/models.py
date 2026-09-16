from __future__ import annotations

from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Subject(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    user_id: str = Field(min_length=1)
    workspace_id: str = Field(min_length=1)
    scopes: frozenset[str]


class AccessDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    allowed: bool
    reason_code: str
    policy_version: str


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


class RetrievalQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    user_id: str
    scopes: frozenset[str]
    text: str = Field(min_length=1, max_length=2000)


class RetrievalResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    chunks: tuple[RetrievedChunk, ...]
    strategy: str
    index_version: str
    policy_version: str | None = None


class AccessPolicy(Protocol):
    def can_read(self, subject: Subject, chunk: RetrievedChunk) -> AccessDecision: ...


class Retriever(Protocol):
    async def retrieve(self, query: RetrievalQuery) -> RetrievalResult: ...


class AuditEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_type: Literal["access_denied"]
    user_id: str
    workspace_id: str
    subject_scopes: tuple[str, ...]
    source_id: str
    chunk_id: str
    chunk_workspace_id: str
    required_scope: str
    reason_code: str
    policy_version: str
