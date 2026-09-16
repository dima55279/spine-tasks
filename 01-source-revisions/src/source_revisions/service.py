from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from source_revisions.checksum import file_sha256
from source_revisions.models import (
    TOMBSTONE_CHECKSUM,
    RegisterResult,
    RevisionRepository,
    SourceRevision,
)


class RevisionService:
    def __init__(self, repository: RevisionRepository) -> None:
        self._repository = repository

    def register_file(
        self,
        workspace_id: str,
        source_id: str,
        path: Path,
        media_type: str,
    ) -> RegisterResult:
        checksum = file_sha256(path)
        existing = self._repository.find_by_checksum(workspace_id, source_id, checksum)
        if existing is not None:
            return RegisterResult(status="unchanged", revision=existing)

        revision = SourceRevision(
            revision_id=uuid4(),
            workspace_id=workspace_id,
            source_id=source_id,
            checksum_sha256=checksum,
            media_type=media_type,
            original_path=str(path),
            observed_at=datetime.now(UTC),
        )
        self._repository.save(revision)
        return RegisterResult(status="created", revision=revision)

    def tombstone(
        self,
        workspace_id: str,
        source_id: str,
        original_path: str = "<tombstone>",
        media_type: str = "application/x-tombstone",
    ) -> SourceRevision:
        revision = SourceRevision(
            revision_id=uuid4(),
            workspace_id=workspace_id,
            source_id=source_id,
            checksum_sha256=TOMBSTONE_CHECKSUM,
            media_type=media_type,
            original_path=original_path,
            observed_at=datetime.now(UTC),
            is_tombstone=True,
        )
        self._repository.save(revision)
        return revision

    def history(self, workspace_id: str, source_id: str) -> list[SourceRevision]:
        return self._repository.history(workspace_id, source_id)
