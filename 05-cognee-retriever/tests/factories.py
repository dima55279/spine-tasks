from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from cognee_retriever.models import (
    BuildIndexCommand,
    ChunkMetadata,
    RetrievalQuery,
)

TRAVEL_REVISION = UUID("11111111-1111-4111-8111-222222222222")
SECURITY_REVISION = UUID("22222222-2222-4222-8222-222222222222")
ENGINEERING_REVISION = UUID("33333333-3333-4333-8333-333333333333")


def query(text: str = "Какой размер суточных?") -> RetrievalQuery:
    return RetrievalQuery(
        workspace_id="alpha",
        user_id="user-001",
        scopes=frozenset({"all-employees"}),
        text=text,
    )


def travel_metadata(chunk_id: str = "travel-v2-daily") -> ChunkMetadata:
    return ChunkMetadata(
        workspace_id="alpha",
        required_scope="all-employees",
        source_id="travel-policy",
        revision_id=TRAVEL_REVISION,
        chunk_id=chunk_id,
        text="С 1 сентября суточные для поездок по России составляют 1200 рублей в день.",
        locator={"heading": "Суточные", "paragraph": 1},
    )


def engineering_metadata() -> ChunkMetadata:
    return ChunkMetadata(
        workspace_id="alpha",
        required_scope="engineering",
        source_id="engineering-only",
        revision_id=ENGINEERING_REVISION,
        chunk_id="engineering-name",
        text="Кодовое имя прототипа — Aurora.",
        locator={"heading": "Кодовое имя", "paragraph": 1},
    )


def write_manifest(directory: Path, *chunks: ChunkMetadata) -> tuple[Path, ...]:
    directory.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index, chunk in enumerate(chunks):
        path = directory / f"manifest-{index}.jsonl"
        path.write_text(
            _manifest_line(chunk) + "\n",
            encoding="utf-8",
        )
        paths.append(path)
    return tuple(paths)


def write_access_map(path: Path) -> Path:
    payload = {
        "schema_version": "1.0",
        "sources": [
            {
                "workspace_id": "alpha",
                "source_id": "travel-policy",
                "file": "travel.md",
                "revision_id": str(TRAVEL_REVISION),
                "required_scope": "all-employees",
                "current": True,
            },
            {
                "workspace_id": "alpha",
                "source_id": "engineering-only",
                "file": "engineering.md",
                "revision_id": str(ENGINEERING_REVISION),
                "required_scope": "engineering",
                "current": True,
            },
        ],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def build_command(tmp_path: Path, *chunks: ChunkMetadata) -> BuildIndexCommand:
    manifest_paths = write_manifest(tmp_path / "manifests", *chunks)
    access_map = write_access_map(tmp_path / "access-map.json")
    return BuildIndexCommand(
        workspace_id="alpha",
        manifest_paths=manifest_paths,
        access_map_path=access_map,
    )


def _manifest_line(chunk: ChunkMetadata) -> str:
    return (
        "{"
        f'"chunk_id":"{chunk.chunk_id}",'
        f'"workspace_id":"{chunk.workspace_id}",'
        f'"source_id":"{chunk.source_id}",'
        f'"revision_id":"{chunk.revision_id}",'
        '"ordinal":0,'
        f'"text":"{chunk.text}",'
        f'"locator":{{"heading":"{chunk.locator["heading"]}","paragraph":1}}'
        "}"
    )
