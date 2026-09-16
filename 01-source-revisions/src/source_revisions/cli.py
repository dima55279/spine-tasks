from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from source_revisions.repository import JsonlRevisionRepository
from source_revisions.service import RevisionService

app = typer.Typer(no_args_is_help=True)
WorkspaceOption = Annotated[str, typer.Option("--workspace")]
SourceOption = Annotated[str, typer.Option("--source")]
StoreOption = Annotated[Path, typer.Option("--store")]
MediaTypeOption = Annotated[str, typer.Option("--media-type")]
OriginalPathOption = Annotated[str, typer.Option("--original-path")]
FileOption = Annotated[Path, typer.Option("--file", exists=True, dir_okay=False, readable=True)]


def build_service(store: Path) -> RevisionService:
    return RevisionService(JsonlRevisionRepository(store))


@app.command()
def register(
    workspace: WorkspaceOption,
    source: SourceOption,
    file: FileOption,
    media_type: MediaTypeOption = "text/markdown",
    store: StoreOption = Path("data/revisions.jsonl"),
) -> None:
    result = build_service(store).register_file(workspace, source, file, media_type)
    typer.echo(result.model_dump_json(indent=2))


@app.command()
def history(
    workspace: WorkspaceOption,
    source: SourceOption,
    store: StoreOption = Path("data/revisions.jsonl"),
) -> None:
    revisions = build_service(store).history(workspace, source)
    for revision in revisions:
        typer.echo(revision.model_dump_json())


@app.command()
def tombstone(
    workspace: WorkspaceOption,
    source: SourceOption,
    original_path: OriginalPathOption = "<tombstone>",
    store: StoreOption = Path("data/revisions.jsonl"),
) -> None:
    revision = build_service(store).tombstone(workspace, source, original_path)
    typer.echo(revision.model_dump_json(indent=2))


if __name__ == "__main__":
    app()
