from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    scopes: frozenset[str] = Field(min_length=1, max_length=8)
    question: str = Field(min_length=1, max_length=2000)
    request_id: str = Field(min_length=1, max_length=128)


class ContextReference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str
    revision_id: UUID
    chunk_id: str
    locator: dict[str, str | int | None]


class Citation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str
    revision_id: UUID
    chunk_id: str
    locator: dict[str, str | int | None]


class AskResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["answered", "abstained"]
    answer: str | None
    citations: tuple[Citation, ...]
    index_version: str
    policy_version: str | None
    trace_id: str
    as_of: datetime
    reasons: tuple[str, ...]


class ApiError(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    message: str
    trace_id: str
    retryable: bool


class ErrorResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    error: ApiError


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
    policy_version: str | None = None


class Claim(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    citation_ids: tuple[str, ...]


class DraftAnswer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    claims: tuple[Claim, ...]
    summary: str
