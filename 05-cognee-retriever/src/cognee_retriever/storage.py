from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from cognee_retriever.models import ChunkMetadata, ProjectionState, ProjectionVersion


class ProjectionStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS projection_versions (
                  projection_id TEXT PRIMARY KEY,
                  workspace_id TEXT NOT NULL,
                  dataset_name TEXT NOT NULL,
                  revision_ids_json TEXT NOT NULL,
                  state TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  error TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS active_projection (
                  workspace_id TEXT PRIMARY KEY,
                  projection_id TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chunk_metadata (
                  projection_id TEXT NOT NULL,
                  chunk_id TEXT NOT NULL,
                  metadata_json TEXT NOT NULL,
                  PRIMARY KEY (projection_id, chunk_id)
                )
                """
            )

    def create_building(
        self, workspace_id: str, revision_ids: tuple[UUID, ...]
    ) -> ProjectionVersion:
        self.initialize()
        projection_id = uuid4()
        version = ProjectionVersion(
            projection_id=projection_id,
            workspace_id=workspace_id,
            dataset_name=f"{workspace_id}_projection_{projection_id.hex}",
            revision_ids=revision_ids,
            state=ProjectionState.BUILDING,
            created_at=datetime.now(UTC),
        )
        with self._connect() as connection:
            self._insert_version(connection, version)
        return version

    def save_chunks(self, projection_id: UUID, chunks: tuple[ChunkMetadata, ...]) -> None:
        self.initialize()
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR REPLACE INTO chunk_metadata
                  (projection_id, chunk_id, metadata_json)
                VALUES (?, ?, ?)
                """,
                [
                    (str(projection_id), chunk.chunk_id, chunk.model_dump_json())
                    for chunk in chunks
                ],
            )

    def mark_active(self, projection_id: UUID) -> ProjectionVersion:
        self.initialize()
        version = self.get_version(projection_id)
        if version is None:
            raise ValueError(f"Unknown projection {projection_id}")
        active = version.model_copy(update={"state": ProjectionState.ACTIVE, "error": None})
        with self._connect() as connection:
            self._update_version(connection, active)
            connection.execute(
                """
                INSERT INTO active_projection (workspace_id, projection_id)
                VALUES (?, ?)
                ON CONFLICT(workspace_id) DO UPDATE
                SET projection_id = excluded.projection_id
                """,
                (active.workspace_id, str(active.projection_id)),
            )
        return active

    def mark_failed(self, projection_id: UUID, error: str) -> ProjectionVersion:
        self.initialize()
        version = self.get_version(projection_id)
        if version is None:
            raise ValueError(f"Unknown projection {projection_id}")
        failed = version.model_copy(update={"state": ProjectionState.FAILED, "error": error})
        with self._connect() as connection:
            self._update_version(connection, failed)
        return failed

    def activate(self, workspace_id: str, projection_id: UUID) -> ProjectionVersion:
        version = self.get_version(projection_id)
        if version is None or version.workspace_id != workspace_id:
            raise ValueError(f"Unknown projection {projection_id} for workspace {workspace_id}")
        return self.mark_active(projection_id)

    def active_version(self, workspace_id: str) -> ProjectionVersion | None:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT projection_id FROM active_projection WHERE workspace_id = ?
                """,
                (workspace_id,),
            ).fetchone()
        if row is None:
            return None
        return self.get_version(UUID(row[0]))

    def get_version(self, projection_id: UUID) -> ProjectionVersion | None:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT projection_id, workspace_id, dataset_name, revision_ids_json,
                       state, created_at, error
                FROM projection_versions
                WHERE projection_id = ?
                """,
                (str(projection_id),),
            ).fetchone()
        if row is None:
            return None
        return ProjectionVersion(
            projection_id=UUID(row[0]),
            workspace_id=row[1],
            dataset_name=row[2],
            revision_ids=tuple(UUID(value) for value in json.loads(row[3])),
            state=row[4],
            created_at=datetime.fromisoformat(row[5]),
            error=row[6],
        )

    def chunks_for(self, projection_id: UUID) -> dict[str, ChunkMetadata]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT metadata_json FROM chunk_metadata WHERE projection_id = ?
                """,
                (str(projection_id),),
            ).fetchall()
        return {
            chunk.chunk_id: chunk
            for chunk in (ChunkMetadata.model_validate_json(row[0]) for row in rows)
        }

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    @staticmethod
    def _insert_version(connection: sqlite3.Connection, version: ProjectionVersion) -> None:
        connection.execute(
            """
            INSERT INTO projection_versions
              (projection_id, workspace_id, dataset_name, revision_ids_json,
               state, created_at, error)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(version.projection_id),
                version.workspace_id,
                version.dataset_name,
                json.dumps([str(value) for value in version.revision_ids]),
                version.state,
                version.created_at.isoformat(),
                version.error,
            ),
        )

    @staticmethod
    def _update_version(connection: sqlite3.Connection, version: ProjectionVersion) -> None:
        connection.execute(
            """
            UPDATE projection_versions
            SET state = ?, error = ?
            WHERE projection_id = ?
            """,
            (version.state, version.error, str(version.projection_id)),
        )
