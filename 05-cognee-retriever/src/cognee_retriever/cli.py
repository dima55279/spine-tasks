from __future__ import annotations

import asyncio
import json
from pathlib import Path
from time import perf_counter
from typing import Annotated
from uuid import UUID

import typer

from cognee_retriever.cognee_client import RealCogneeClient
from cognee_retriever.cognee_retriever import CogneeRetriever
from cognee_retriever.models import BuildIndexCommand, RetrievalQuery
from cognee_retriever.service import ProjectionService
from cognee_retriever.storage import ProjectionStore

app = typer.Typer(no_args_is_help=True)

WorkspaceOption = Annotated[str, typer.Option("--workspace")]
ManifestDirOption = Annotated[Path, typer.Option("--manifest-dir", exists=True)]
AccessMapOption = Annotated[Path, typer.Option("--access-map", exists=True, dir_okay=False)]
StoreOption = Annotated[Path, typer.Option("--store")]
QuestionOption = Annotated[str, typer.Option("--question")]
UserOption = Annotated[str, typer.Option("--user")]
ScopesOption = Annotated[list[str], typer.Option("--scope")]
ProjectionOption = Annotated[UUID, typer.Option("--projection-id")]
QuestionsOption = Annotated[Path, typer.Option("--questions", exists=True, dir_okay=False)]
OutputOption = Annotated[Path, typer.Option("--output")]


def build_command(workspace: str, manifest_dir: Path, access_map: Path) -> BuildIndexCommand:
    return BuildIndexCommand(
        workspace_id=workspace,
        manifest_paths=tuple(sorted(manifest_dir.glob("*.jsonl"))),
        access_map_path=access_map,
    )


@app.command("build-index")
def build_index(
    workspace: WorkspaceOption,
    manifest_dir: ManifestDirOption = Path("data/manifests"),
    access_map: AccessMapOption = Path("data/fixtures/access-map.json"),
    store: StoreOption = Path("data/projections.db"),
) -> None:
    service = ProjectionService(RealCogneeClient(), ProjectionStore(store))
    version = asyncio.run(service.build_index(build_command(workspace, manifest_dir, access_map)))
    typer.echo(version.model_dump_json(indent=2))


@app.command()
def rebuild(
    workspace: WorkspaceOption,
    manifest_dir: ManifestDirOption = Path("data/manifests"),
    access_map: AccessMapOption = Path("data/fixtures/access-map.json"),
    store: StoreOption = Path("data/projections.db"),
) -> None:
    service = ProjectionService(RealCogneeClient(), ProjectionStore(store))
    version = asyncio.run(service.rebuild(build_command(workspace, manifest_dir, access_map)))
    typer.echo(version.model_dump_json(indent=2))


@app.command("activate-index")
def activate_index(
    workspace: WorkspaceOption,
    projection_id: ProjectionOption,
    store: StoreOption = Path("data/projections.db"),
) -> None:
    version = ProjectionService(RealCogneeClient(), ProjectionStore(store)).activate_index(
        workspace, projection_id
    )
    typer.echo(version.model_dump_json(indent=2))


@app.command("retrieve-context")
def retrieve_context(
    workspace: WorkspaceOption,
    question: QuestionOption,
    user: UserOption = "demo-user",
    scope: ScopesOption | None = None,
    store: StoreOption = Path("data/projections.db"),
) -> None:
    scopes = scope or ["all-employees"]
    retriever = CogneeRetriever(RealCogneeClient(), ProjectionStore(store))
    result = asyncio.run(
        retriever.retrieve(
            RetrievalQuery(
                workspace_id=workspace,
                user_id=user,
                scopes=frozenset(scopes),
                text=question,
            )
        )
    )
    typer.echo(result.model_dump_json(indent=2))


@app.command("manual-check")
def manual_check(
    questions: QuestionsOption = Path("data/fixtures/questions/manual-check.jsonl"),
    output: OutputOption = Path("data/manual-check-results.jsonl"),
    store: StoreOption = Path("data/projections.db"),
) -> None:
    retriever = CogneeRetriever(RealCogneeClient(), ProjectionStore(store))
    output.parent.mkdir(parents=True, exist_ok=True)
    with questions.open("r", encoding="utf-8") as source, output.open(
        "w", encoding="utf-8"
    ) as sink:
        for line in source:
            if not line.strip():
                continue
            case = json.loads(line)
            started = perf_counter()
            result = asyncio.run(
                retriever.retrieve(
                    RetrievalQuery(
                        workspace_id=case["workspace_id"],
                        user_id="manual-check",
                        scopes=frozenset(case["scopes"]),
                        text=case["question"],
                    )
                )
            )
            source_ids = {chunk.reference.source_id for chunk in result.chunks}
            record = {
                "case_id": case["case_id"],
                "expected_source_returned": set(case["expected_source_ids"]).issubset(
                    source_ids
                ),
                "forbidden_source_absent": set(case["forbidden_source_ids"]).isdisjoint(
                    source_ids
                ),
                "duration_ms": round((perf_counter() - started) * 1000, 3),
                "references_ok": all(
                    chunk.reference.chunk_id and chunk.reference.locator
                    for chunk in result.chunks
                ),
            }
            sink.write(json.dumps(record, ensure_ascii=False))
            sink.write("\n")
    typer.echo(str(output))


if __name__ == "__main__":
    app()
