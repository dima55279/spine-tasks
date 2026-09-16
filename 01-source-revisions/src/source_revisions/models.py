from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceRevision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    revision_id: UUID
    workspace_id: str
    source_id: str
    checksum_sha256: str
    media_type: str
    original_path: str
    observed_at: datetime
    is_tombstone: bool = False

    @field_validator("workspace_id", "source_id", "media_type", "original_path")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("checksum_sha256")
    @classmethod
    def checksum_must_be_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError("must be a lowercase SHA-256 hex digest")
        return value

    @field_validator("observed_at")
    @classmethod
    def observed_at_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("must include timezone")
        return value


class RegisterResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["created", "unchanged"]
    revision: SourceRevision


class RevisionRepository(Protocol):
    def find_by_checksum(
        self, workspace_id: str, source_id: str, checksum: str
    ) -> SourceRevision | None: ...

    def save(self, revision: SourceRevision) -> None: ...

    def history(self, workspace_id: str, source_id: str) -> list[SourceRevision]: ...


class RevisionReadError(ValueError):
    def __init__(self, path: str, line_number: int, message: str) -> None:
        super().__init__(f"Could not read {path} line {line_number}: {message}")
        self.path = path
        self.line_number = line_number
        self.message = message


TOMBSTONE_CHECKSUM = "0" * 64


class TombstoneRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    workspace_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    original_path: str = Field(min_length=1)
