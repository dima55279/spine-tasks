from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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


class Claim(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = Field(min_length=1)
    citation_ids: tuple[str, ...]


class DraftAnswer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    claims: tuple[Claim, ...]
    summary: str


class ValidatedAnswer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["answered", "abstained"]
    answer_text: str | None
    citations: tuple[ContextReference, ...]
    reasons: tuple[str, ...]
