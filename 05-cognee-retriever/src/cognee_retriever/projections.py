from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from cognee_retriever.models import ChunkMetadata, ParsedChunk


def load_access_scopes(path: Path) -> dict[tuple[str, str, UUID], str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    scopes: dict[tuple[str, str, UUID], str] = {}
    for source in payload["sources"]:
        scopes[
            (
                source["workspace_id"],
                source["source_id"],
                UUID(source["revision_id"]),
            )
        ] = source["required_scope"]
    return scopes


def load_chunk_metadata(
    manifest_paths: tuple[Path, ...],
    access_map_path: Path,
) -> tuple[ChunkMetadata, ...]:
    scopes = load_access_scopes(access_map_path)
    metadata: list[ChunkMetadata] = []
    for path in sorted(manifest_paths):
        with path.open("r", encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                chunk = ParsedChunk.model_validate_json(line)
                scope = scopes.get(
                    (chunk.workspace_id, chunk.source_id, chunk.revision_id),
                    "all-employees",
                )
                metadata.append(
                    ChunkMetadata(
                        workspace_id=chunk.workspace_id,
                        required_scope=scope,
                        source_id=chunk.source_id,
                        revision_id=chunk.revision_id,
                        chunk_id=chunk.chunk_id,
                        text=chunk.text,
                        locator=chunk.locator,
                    )
                )
    return tuple(metadata)


def revision_ids_for(chunks: tuple[ChunkMetadata, ...]) -> tuple[UUID, ...]:
    return tuple(sorted({chunk.revision_id for chunk in chunks}, key=str))
