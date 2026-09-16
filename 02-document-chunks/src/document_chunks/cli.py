from __future__ import annotations

from pathlib import Path
from typing import Annotated
from uuid import UUID

import typer

from document_chunks.manifest import manifest_path, read_manifest, verify_manifest, write_manifest
from document_chunks.markdown_parser import MarkdownParser, read_source_document
from document_chunks.models import DocumentReadError, ManifestReadError, ManifestVerificationError

app = typer.Typer(no_args_is_help=True)

WorkspaceOption = Annotated[str, typer.Option("--workspace")]
SourceOption = Annotated[str, typer.Option("--source")]
RevisionOption = Annotated[UUID, typer.Option("--revision")]
FileOption = Annotated[Path, typer.Option("--file", exists=True, dir_okay=False, readable=True)]
ManifestOption = Annotated[Path, typer.Option("--manifest", dir_okay=False)]
ManifestDirOption = Annotated[Path, typer.Option("--manifest-dir")]
MaxCharsOption = Annotated[int, typer.Option("--max-chars", min=1)]
MediaTypeOption = Annotated[str, typer.Option("--media-type")]


@app.command()
def parse(
    workspace: WorkspaceOption,
    source: SourceOption,
    revision: RevisionOption,
    file: FileOption,
    manifest_dir: ManifestDirOption = Path("data/manifests"),
    max_chars: MaxCharsOption = 600,
    media_type: MediaTypeOption = "text/markdown",
) -> None:
    try:
        document = read_source_document(file, workspace, source, revision, media_type)
        chunks = MarkdownParser(max_chars=max_chars).parse(document)
    except DocumentReadError as error:
        raise typer.BadParameter(str(error)) from error

    path = manifest_path(manifest_dir, revision)
    write_manifest(path, chunks)
    typer.echo(f"{len(chunks)} chunks written to {path}")


@app.command("verify-manifest")
def verify_manifest_command(
    file: FileOption,
    manifest: ManifestOption,
) -> None:
    try:
        document_text = file.read_text(encoding="utf-8")
        chunks = read_manifest(manifest)
        verify_manifest(document_text, chunks)
    except UnicodeDecodeError as error:
        raise typer.BadParameter(f"Could not decode UTF-8 document {file}: {error}") from error
    except (ManifestReadError, ManifestVerificationError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error

    typer.echo(f"{len(chunks)} chunks verified")


if __name__ == "__main__":
    app()
