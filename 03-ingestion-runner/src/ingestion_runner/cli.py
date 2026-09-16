from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from ingestion_runner.idempotency import IdempotencyStore
from ingestion_runner.logging import configure_json_logging
from ingestion_runner.models import IngestCommand
from ingestion_runner.runner import (
    IngestionRunner,
    JsonlRevisionService,
    MarkdownParser,
    receipt_json,
)

app = typer.Typer(no_args_is_help=True)

WorkspaceOption = Annotated[str, typer.Option("--workspace")]
DirectoryOption = Annotated[Path, typer.Option("--directory", exists=True, file_okay=False)]
IdempotencyOption = Annotated[str, typer.Option("--idempotency-key")]
StoreOption = Annotated[Path, typer.Option("--store")]
RevisionsOption = Annotated[Path, typer.Option("--revisions")]
ManifestDirOption = Annotated[Path, typer.Option("--manifest-dir")]


@app.callback()
def main() -> None:
    """Repeatable document ingestion commands."""


@app.command()
def ingest(
    workspace: WorkspaceOption,
    directory: DirectoryOption,
    idempotency_key: IdempotencyOption,
    continue_on_error: Annotated[bool, typer.Option("--continue-on-error")] = False,
    store: StoreOption = Path("data/runs.db"),
    revisions: RevisionsOption = Path("data/revisions.jsonl"),
    manifest_dir: ManifestDirOption = Path("data/manifests"),
) -> None:
    configure_json_logging()
    command = IngestCommand(
        workspace_id=workspace,
        directory=directory,
        idempotency_key=idempotency_key,
    )
    runner = IngestionRunner(
        revision_service=JsonlRevisionService(revisions),
        parser=MarkdownParser(),
        idempotency_store=IdempotencyStore(store),
        manifest_dir=manifest_dir,
    )
    receipt = asyncio.run(runner.run(command, continue_on_error=continue_on_error))
    typer.echo(receipt_json(receipt))


if __name__ == "__main__":
    app()
