from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import pytest

from document_chunks.manifest import (
    manifest_path,
    read_manifest,
    verify_manifest,
    write_manifest,
)
from document_chunks.markdown_parser import MarkdownParser, read_source_document
from document_chunks.models import ManifestVerificationError, SourceDocument

REVISION_ID = UUID("11111111-1111-4111-8111-111111111111")


def test_manifest_round_trip_and_verification(tmp_path: Path) -> None:
    document_path = tmp_path / "policy.md"
    document_path.write_text("# Title\n\nFirst paragraph.\n\nSecond paragraph.", encoding="utf-8")
    document = read_source_document(document_path, "alpha", "policy", REVISION_ID)
    chunks = MarkdownParser(max_chars=600).parse(document)
    path = manifest_path(tmp_path / "manifests", REVISION_ID)

    write_manifest(path, chunks)
    loaded = read_manifest(path)
    verify_manifest(document.text, loaded)

    assert [chunk.chunk_id for chunk in loaded] == [chunk.chunk_id for chunk in chunks]


def test_manifest_verification_fails_after_manual_locator_change(tmp_path: Path) -> None:
    document_path = tmp_path / "policy.md"
    document_path.write_text("# Title\n\nFirst paragraph.", encoding="utf-8")
    document = read_source_document(document_path, "alpha", "policy", REVISION_ID)
    chunks = MarkdownParser(max_chars=600).parse(document)
    path = tmp_path / "manifest.jsonl"
    write_manifest(path, chunks)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["locator"]["char_start"] += 1
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")

    with pytest.raises(ManifestVerificationError):
        verify_manifest(document.text, read_manifest(path))


def test_txt_uses_no_heading() -> None:
    document_path = Path("plain.txt")
    text = "Plain text\n\nAnother paragraph"

    chunks = MarkdownParser(max_chars=600).parse(
        SourceDocument(
            workspace_id="alpha",
            source_id="plain",
            revision_id=REVISION_ID,
            path=document_path,
            text=text,
            media_type="text/plain",
        )
    )

    assert [chunk.locator.heading for chunk in chunks] == [None, None]
