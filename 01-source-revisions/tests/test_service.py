from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from source_revisions.models import SourceRevision
from source_revisions.repository import InMemoryRevisionRepository
from source_revisions.service import RevisionService


def test_same_content_is_registered_once(tmp_path: Path) -> None:
    path = tmp_path / "policy.md"
    path.write_text("Правило", encoding="utf-8")
    repository = InMemoryRevisionRepository()
    service = RevisionService(repository)

    first = service.register_file("alpha", "policy", path, "text/markdown")
    second = service.register_file("alpha", "policy", path, "text/markdown")

    assert first.status == "created"
    assert second.status == "unchanged"
    assert second.revision.revision_id == first.revision.revision_id
    assert len(repository.history("alpha", "policy")) == 1


def test_changed_content_creates_second_revision(tmp_path: Path) -> None:
    path = tmp_path / "policy.md"
    path.write_text("Правило", encoding="utf-8")
    repository = InMemoryRevisionRepository()
    service = RevisionService(repository)

    first = service.register_file("alpha", "policy", path, "text/markdown")
    path.write_text("Правило.", encoding="utf-8")
    second = service.register_file("alpha", "policy", path, "text/markdown")

    assert first.status == "created"
    assert second.status == "created"
    assert second.revision.revision_id != first.revision.revision_id
    assert len(repository.history("alpha", "policy")) == 2


def test_same_source_in_different_workspaces_has_separate_history(tmp_path: Path) -> None:
    path = tmp_path / "policy.md"
    path.write_text("Правило", encoding="utf-8")
    repository = InMemoryRevisionRepository()
    service = RevisionService(repository)

    alpha = service.register_file("alpha", "policy", path, "text/markdown")
    beta = service.register_file("beta", "policy", path, "text/markdown")

    assert alpha.status == "created"
    assert beta.status == "created"
    assert alpha.revision.revision_id != beta.revision.revision_id
    assert len(repository.history("alpha", "policy")) == 1
    assert len(repository.history("beta", "policy")) == 1


def test_tombstone_does_not_delete_previous_revisions(tmp_path: Path) -> None:
    path = tmp_path / "policy.md"
    path.write_text("Правило", encoding="utf-8")
    repository = InMemoryRevisionRepository()
    service = RevisionService(repository)

    service.register_file("alpha", "policy", path, "text/markdown")
    tombstone = service.tombstone("alpha", "policy")

    history = repository.history("alpha", "policy")
    assert len(history) == 2
    assert history[0].is_tombstone is False
    assert history[1] == tombstone
    assert history[1].is_tombstone is True


def test_revision_is_immutable(tmp_path: Path) -> None:
    path = tmp_path / "policy.md"
    path.write_text("Правило", encoding="utf-8")
    service = RevisionService(InMemoryRevisionRepository())

    result = service.register_file("alpha", "policy", path, "text/markdown")

    with pytest.raises(ValidationError):
        result.revision.source_id = "other"


def test_revision_rejects_unknown_fields(tmp_path: Path) -> None:
    path = tmp_path / "policy.md"
    path.write_text("Правило", encoding="utf-8")
    service = RevisionService(InMemoryRevisionRepository())
    revision = service.register_file("alpha", "policy", path, "text/markdown").revision
    payload = revision.model_dump()
    payload["unexpected"] = "value"

    with pytest.raises(ValidationError):
        SourceRevision.model_validate(payload)
