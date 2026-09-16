from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path

from pydantic import ValidationError

from source_revisions.models import RevisionReadError, SourceRevision


class InMemoryRevisionRepository:
    def __init__(self) -> None:
        self._revisions: list[SourceRevision] = []

    def find_by_checksum(
        self, workspace_id: str, source_id: str, checksum: str
    ) -> SourceRevision | None:
        for revision in self._revisions:
            if (
                revision.workspace_id == workspace_id
                and revision.source_id == source_id
                and revision.checksum_sha256 == checksum
            ):
                return revision
        return None

    def save(self, revision: SourceRevision) -> None:
        self._revisions.append(revision)

    def history(self, workspace_id: str, source_id: str) -> list[SourceRevision]:
        return [
            revision
            for revision in self._revisions
            if revision.workspace_id == workspace_id and revision.source_id == source_id
        ]


class JsonlRevisionRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    def find_by_checksum(
        self, workspace_id: str, source_id: str, checksum: str
    ) -> SourceRevision | None:
        for revision in self._read_all():
            if (
                revision.workspace_id == workspace_id
                and revision.source_id == source_id
                and revision.checksum_sha256 == checksum
            ):
                return revision
        return None

    def save(self, revision: SourceRevision) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as stream:
            stream.write(revision.model_dump_json())
            stream.write("\n")

    def history(self, workspace_id: str, source_id: str) -> list[SourceRevision]:
        return [
            revision
            for revision in self._read_all()
            if revision.workspace_id == workspace_id and revision.source_id == source_id
        ]

    def _read_all(self) -> list[SourceRevision]:
        if not self._path.exists():
            return []

        revisions: list[SourceRevision] = []
        with self._path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                    revisions.append(SourceRevision.model_validate(payload))
                except JSONDecodeError as error:
                    raise RevisionReadError(str(self._path), line_number, error.msg) from error
                except ValidationError as error:
                    raise RevisionReadError(str(self._path), line_number, str(error)) from error
        return revisions
