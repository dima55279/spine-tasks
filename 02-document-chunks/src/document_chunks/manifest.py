from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError

from document_chunks.models import (
    ManifestReadError,
    ManifestVerificationError,
    ParsedChunk,
)


def manifest_path(directory: Path, revision_id: UUID) -> Path:
    return directory / f"{revision_id}.jsonl"


def write_manifest(path: Path, chunks: tuple[ParsedChunk, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for chunk in chunks:
            stream.write(chunk.model_dump_json())
            stream.write("\n")


def read_manifest(path: Path) -> tuple[ParsedChunk, ...]:
    chunks: list[ParsedChunk] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                chunks.append(ParsedChunk.model_validate(json.loads(stripped)))
            except JSONDecodeError as error:
                raise ManifestReadError(path, line_number, error.msg) from error
            except ValidationError as error:
                raise ManifestReadError(path, line_number, str(error)) from error
    return tuple(chunks)


def verify_manifest(document_text: str, chunks: tuple[ParsedChunk, ...]) -> None:
    for chunk in chunks:
        start = chunk.locator.char_start
        end = chunk.locator.char_end
        if document_text[start:end] != chunk.text:
            raise ManifestVerificationError(chunk.chunk_id, start, end)
