from __future__ import annotations

from pathlib import Path

import pytest

from ingestion_runner.idempotency import IdempotencyStore
from ingestion_runner.logging import configure_json_logging
from ingestion_runner.models import IngestCommand, SourceDocument
from ingestion_runner.runner import (
    IngestionRunner,
    JsonlRevisionService,
    MarkdownParser,
    UnsafePathError,
)


class FailingParser(MarkdownParser):
    def parse(self, document: SourceDocument):
        if document.path.name == "broken.md":
            raise ValueError("synthetic parser failure")
        return super().parse(document)


def write_documents(directory: Path, count: int = 3) -> None:
    directory.mkdir()
    for index in range(count):
        (directory / f"doc-{index}.md").write_text(
            f"# Document {index}\n\nParagraph {index}.",
            encoding="utf-8",
        )


def make_runner(tmp_path: Path, parser: MarkdownParser | None = None) -> IngestionRunner:
    return IngestionRunner(
        revision_service=JsonlRevisionService(tmp_path / "revisions.jsonl"),
        parser=parser or MarkdownParser(),
        idempotency_store=IdempotencyStore(tmp_path / "runs.db"),
        manifest_dir=tmp_path / "manifests",
    )


@pytest.mark.asyncio
async def test_three_valid_files_create_three_receipt_items(tmp_path: Path) -> None:
    directory = tmp_path / "docs"
    write_documents(directory)
    runner = make_runner(tmp_path)

    receipt = await runner.run(
        IngestCommand(workspace_id="alpha", directory=directory, idempotency_key="run-1")
    )

    assert len(receipt.items) == 3
    assert [item.status for item in receipt.items] == ["indexed", "indexed", "indexed"]
    assert all(item.chunk_count == 1 for item in receipt.items)
    assert len(list((tmp_path / "manifests").glob("*.jsonl"))) == 3


@pytest.mark.asyncio
async def test_broken_file_continue_mode_keeps_two_successes(tmp_path: Path) -> None:
    directory = tmp_path / "docs"
    directory.mkdir()
    (directory / "a.md").write_text("# A\n\nAlpha.", encoding="utf-8")
    (directory / "broken.md").write_text("# Broken\n\nBoom.", encoding="utf-8")
    (directory / "c.md").write_text("# C\n\nCharlie.", encoding="utf-8")
    runner = make_runner(tmp_path, FailingParser())

    receipt = await runner.run(
        IngestCommand(workspace_id="alpha", directory=directory, idempotency_key="run-1"),
        continue_on_error=True,
    )

    assert [(item.source_id, item.status) for item in receipt.items] == [
        ("a", "indexed"),
        ("broken", "failed"),
        ("c", "indexed"),
    ]
    assert receipt.items[1].error_code == "ValueError"
    assert len(list((tmp_path / "manifests").glob("*.jsonl"))) == 2


@pytest.mark.asyncio
async def test_repeated_idempotency_key_returns_same_run_id(tmp_path: Path) -> None:
    directory = tmp_path / "docs"
    write_documents(directory)
    runner = make_runner(tmp_path)
    command = IngestCommand(workspace_id="alpha", directory=directory, idempotency_key="same-key")

    first = await runner.run(command)
    second = await runner.run(command)

    assert second.run_id == first.run_id
    assert second.items == first.items


@pytest.mark.asyncio
async def test_new_key_and_unchanged_files_report_unchanged(tmp_path: Path) -> None:
    directory = tmp_path / "docs"
    write_documents(directory)
    runner = make_runner(tmp_path)

    first = await runner.run(
        IngestCommand(workspace_id="alpha", directory=directory, idempotency_key="run-1")
    )
    second = await runner.run(
        IngestCommand(workspace_id="alpha", directory=directory, idempotency_key="run-2")
    )

    assert first.run_id != second.run_id
    assert [item.status for item in second.items] == ["unchanged", "unchanged", "unchanged"]


@pytest.mark.asyncio
async def test_symlink_escaping_directory_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path / "outside.md"
    outside.write_text("# Outside\n\nSecret.", encoding="utf-8")
    directory = tmp_path / "docs"
    directory.mkdir()
    (directory / "outside.md").symlink_to(outside)
    runner = make_runner(tmp_path)

    with pytest.raises(UnsafePathError):
        await runner.run(
            IngestCommand(workspace_id="alpha", directory=directory, idempotency_key="run-1")
        )


@pytest.mark.asyncio
async def test_manifest_ready_event_is_not_emitted_before_successful_parse(tmp_path: Path) -> None:
    events: list[dict] = []
    configure_json_logging(events)
    directory = tmp_path / "docs"
    directory.mkdir()
    (directory / "broken.md").write_text("# Broken\n\nBoom.", encoding="utf-8")
    runner = make_runner(tmp_path, FailingParser())

    receipt = await runner.run(
        IngestCommand(workspace_id="alpha", directory=directory, idempotency_key="run-1"),
        continue_on_error=True,
    )

    assert receipt.items[0].status == "failed"
    assert not list((tmp_path / "manifests").glob("*.jsonl"))
    assert all(event.get("stage") != "manifest_ready" for event in events)
