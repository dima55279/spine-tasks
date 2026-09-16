from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal, Protocol
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


class Retriever(Protocol):
    async def retrieve(self, query: RetrievalQuery) -> RetrievalResult: ...


class CogneeClient(Protocol):
    async def remember(self, texts: list[str], *, dataset_name: str) -> None: ...

    async def recall(self, query_text: str, *, dataset_name: str) -> list[dict]: ...


class ProjectionState:
    BUILDING = "building"
    ACTIVE = "active"
    FAILED = "failed"


class ProjectionVersion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    projection_id: UUID
    workspace_id: str
    dataset_name: str
    revision_ids: tuple[UUID, ...]
    state: Literal["building", "active", "failed"]
    created_at: datetime
    error: str | None = None


class ChunkMetadata(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    workspace_id: str
    required_scope: str
    source_id: str
    revision_id: UUID
    chunk_id: str
    text: str
    locator: dict[str, str | int | None]


class ParsedChunk(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str
    workspace_id: str
    source_id: str
    revision_id: UUID
    ordinal: int
    text: str
    locator: dict[str, str | int | None]


class BuildIndexCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    workspace_id: str
    manifest_paths: tuple[Path, ...]
    access_map_path: Path
