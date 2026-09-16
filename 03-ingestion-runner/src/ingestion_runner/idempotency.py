from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import UUID

from ingestion_runner.models import IngestionReceipt


class IdempotencyStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    async def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS command_results (
                  workspace_id TEXT NOT NULL,
                  idempotency_key TEXT NOT NULL,
                  receipt_json TEXT NOT NULL,
                  PRIMARY KEY (workspace_id, idempotency_key)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS run_reports (
                  run_id TEXT PRIMARY KEY,
                  workspace_id TEXT NOT NULL,
                  receipt_json TEXT NOT NULL
                )
                """
            )

    async def get(self, workspace_id: str, idempotency_key: str) -> IngestionReceipt | None:
        await self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT receipt_json FROM command_results
                WHERE workspace_id = ? AND idempotency_key = ?
                """,
                (workspace_id, idempotency_key),
            ).fetchone()
        if row is None:
            return None
        return IngestionReceipt.model_validate_json(row[0])

    async def save_progress(self, receipt: IngestionReceipt) -> None:
        await self.initialize()
        with self._connect() as connection:
            self._upsert_report(connection, receipt)

    async def save_final(
        self, workspace_id: str, idempotency_key: str, receipt: IngestionReceipt
    ) -> None:
        await self.initialize()
        with self._connect() as connection:
            self._upsert_report(connection, receipt)
            connection.execute(
                """
                INSERT INTO command_results (workspace_id, idempotency_key, receipt_json)
                VALUES (?, ?, ?)
                """,
                (workspace_id, idempotency_key, receipt.model_dump_json()),
            )

    async def latest_report(self, run_id: UUID) -> IngestionReceipt | None:
        await self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT receipt_json FROM run_reports WHERE run_id = ?",
                (str(run_id),),
            ).fetchone()
        if row is None:
            return None
        return IngestionReceipt.model_validate_json(row[0])

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    @staticmethod
    def _upsert_report(connection: sqlite3.Connection, receipt: IngestionReceipt) -> None:
        connection.execute(
            """
            INSERT INTO run_reports (run_id, workspace_id, receipt_json)
            VALUES (?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET receipt_json = excluded.receipt_json
            """,
            (str(receipt.run_id), receipt.workspace_id, receipt.model_dump_json()),
        )
