from __future__ import annotations

from pathlib import Path

import pytest

from source_revisions.models import RevisionReadError
from source_revisions.repository import JsonlRevisionRepository
from source_revisions.service import RevisionService


def test_jsonl_repository_persists_history(tmp_path: Path) -> None:
    document = tmp_path / "policy.md"
    store = tmp_path / "revisions.jsonl"
    document.write_text("Правило", encoding="utf-8")
    service = RevisionService(JsonlRevisionRepository(store))

    first = service.register_file("alpha", "policy", document, "text/markdown")
    document.write_text("Правило.", encoding="utf-8")
    second = service.register_file("alpha", "policy", document, "text/markdown")

    reopened = JsonlRevisionRepository(store)
    history = reopened.history("alpha", "policy")
    assert [revision.revision_id for revision in history] == [
        first.revision.revision_id,
        second.revision.revision_id,
    ]
    assert store.read_text(encoding="utf-8").count("\n") == 2


def test_jsonl_repository_does_not_duplicate_same_checksum(tmp_path: Path) -> None:
    document = tmp_path / "policy.md"
    store = tmp_path / "revisions.jsonl"
    document.write_text("Правило", encoding="utf-8")
    service = RevisionService(JsonlRevisionRepository(store))

    first = service.register_file("alpha", "policy", document, "text/markdown")
    second = service.register_file("alpha", "policy", document, "text/markdown")

    assert first.status == "created"
    assert second.status == "unchanged"
    assert store.read_text(encoding="utf-8").count("\n") == 1


def test_malformed_jsonl_reports_line_number(tmp_path: Path) -> None:
    store = tmp_path / "revisions.jsonl"
    store.write_text('{"not": "a revision"}\n{broken json}\n', encoding="utf-8")
    repository = JsonlRevisionRepository(store)

    with pytest.raises(RevisionReadError, match="line 1"):
        repository.history("alpha", "policy")


def test_malformed_json_reports_its_line_number(tmp_path: Path) -> None:
    document = tmp_path / "policy.md"
    store = tmp_path / "revisions.jsonl"
    document.write_text("Правило", encoding="utf-8")
    service = RevisionService(JsonlRevisionRepository(store))
    service.register_file("alpha", "policy", document, "text/markdown")
    with store.open("a", encoding="utf-8") as stream:
        stream.write("{broken json}\n")

    with pytest.raises(RevisionReadError, match="line 2"):
        JsonlRevisionRepository(store).history("alpha", "policy")


def test_synthetic_malformed_fixture_reports_line_number() -> None:
    store = Path(__file__).parents[1] / "data" / "fixtures" / "malformed-revisions.jsonl"

    with pytest.raises(RevisionReadError, match="line 1"):
        JsonlRevisionRepository(store).history("alpha", "policy")
