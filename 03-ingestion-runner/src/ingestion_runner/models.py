from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IngestCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    workspace_id: str = Field(min_length=1)
    directory: Path
    idempotency_key: str = Field(min_length=1)


class ItemReceipt(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str
    status: Literal["indexed", "unchanged", "failed"]
    revision_id: UUID | None
    chunk_count: int = Field(ge=0)
    error_code: str | None


class IngestionReceipt(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: UUID
    workspace_id: str
    items: tuple[ItemReceipt, ...]


class SourceRevision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    revision_id: UUID
    workspace_id: str
    source_id: str
    checksum_sha256: str
    media_type: str
    original_path: str
    observed_at: datetime


class RegisterResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["created", "unchanged"]
    revision: SourceRevision


class TextLocator(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    heading: str | None
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)


class ParsedChunk(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str
    workspace_id: str
    source_id: str
    revision_id: UUID
    ordinal: int = Field(ge=0)
    text: str = Field(min_length=1)
    locator: TextLocator


class SourceDocument(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    workspace_id: str
    source_id: str
    revision_id: UUID
    path: Path
    text: str
    media_type: str


class RevisionService(Protocol):
    def register_file(
        self, workspace_id: str, source_id: str, path: Path, media_type: str
    ) -> RegisterResult: ...


class DocumentParser(Protocol):
    def parse(self, document: SourceDocument) -> tuple[ParsedChunk, ...]: ...
