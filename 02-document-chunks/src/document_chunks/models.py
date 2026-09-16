from __future__ import annotations

from pathlib import Path
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TextLocator(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    heading: str | None
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)

    @field_validator("char_end")
    @classmethod
    def end_must_not_precede_start(cls, value: int, info) -> int:
        start = info.data.get("char_start")
        if start is not None and value < start:
            raise ValueError("char_end must not be less than char_start")
        return value


class SourceDocument(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    workspace_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    revision_id: UUID
    path: Path
    text: str
    media_type: str = "text/markdown"


class ParsedChunk(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str
    workspace_id: str
    source_id: str
    revision_id: UUID
    ordinal: int = Field(ge=0)
    text: str = Field(min_length=1)
    locator: TextLocator


class DocumentParser(Protocol):
    def parse(self, document: SourceDocument) -> tuple[ParsedChunk, ...]: ...


class DocumentReadError(ValueError):
    pass


class EmptyDocumentError(DocumentReadError):
    def __init__(self, path: Path) -> None:
        super().__init__(f"Document is empty: {path}")
        self.path = path


class DocumentDecodeError(DocumentReadError):
    def __init__(self, path: Path, message: str) -> None:
        super().__init__(f"Could not decode UTF-8 document {path}: {message}")
        self.path = path


class ManifestReadError(ValueError):
    def __init__(self, path: Path, line_number: int, message: str) -> None:
        super().__init__(f"Could not read manifest {path} line {line_number}: {message}")
        self.path = path
        self.line_number = line_number


class ManifestVerificationError(ValueError):
    def __init__(self, chunk_id: str, start: int, end: int) -> None:
        super().__init__(f"Locator mismatch for chunk {chunk_id}: chars {start}:{end}")
        self.chunk_id = chunk_id
        self.start = start
        self.end = end
