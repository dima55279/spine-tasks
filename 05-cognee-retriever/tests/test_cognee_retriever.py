from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from factories import build_command, engineering_metadata, query, travel_metadata

from cognee_retriever.cognee_retriever import CogneeRetriever
from cognee_retriever.fake_retriever import FakeCogneeClient, FakeRetriever
from cognee_retriever.models import RetrievalResult
from cognee_retriever.service import ProjectionService
from cognee_retriever.storage import ProjectionStore


@pytest.mark.asyncio
async def test_adapter_maps_fake_cognee_payload(tmp_path: Path) -> None:
    store = ProjectionStore(tmp_path / "projections.db")
    service = ProjectionService(FakeCogneeClient(), store)
    version = await service.build_index(build_command(tmp_path, travel_metadata("c1")))
    client = FakeCogneeClient([{"id": "c1", "text": "1200 рублей", "chunk_index": 0}])

    result = await CogneeRetriever(client, store).retrieve(query())

    assert result.index_version == version.dataset_name
    assert result.chunks[0].reference.chunk_id == "c1"
    assert result.chunks[0].reference.source_id == "travel-policy"


@pytest.mark.asyncio
async def test_unit_checks_can_use_programmatic_fake_retriever() -> None:
    expected = RetrievalResult(chunks=(), strategy="configured-fake", index_version="fake-v1")
    retriever = FakeRetriever({"unknown": expected})

    assert await retriever.retrieve(query("unknown")) == expected


def test_application_does_not_import_cognee_directly() -> None:
    source_root = Path("src/cognee_retriever")
    offenders: list[str] = []
    for path in source_root.glob("*.py"):
        if path.name == "cognee_client.py":
            continue
        if "import cognee" in path.read_text(encoding="utf-8"):
            offenders.append(str(path))

    assert offenders == []


@pytest.mark.asyncio
async def test_failed_rebuild_does_not_change_active_version(tmp_path: Path) -> None:
    store = ProjectionStore(tmp_path / "projections.db")
    command = build_command(tmp_path, travel_metadata("c1"))
    initial = await ProjectionService(FakeCogneeClient(), store).build_index(command)

    with pytest.raises(RuntimeError):
        await ProjectionService(FakeCogneeClient(fail_remember=True), store).rebuild(command)

    assert store.active_version("alpha") == initial


@pytest.mark.asyncio
async def test_rebuild_does_not_change_manifests_or_revision_ids(tmp_path: Path) -> None:
    store = ProjectionStore(tmp_path / "projections.db")
    command = build_command(tmp_path, travel_metadata("c1"))
    before = {path: path.read_bytes() for path in command.manifest_paths}

    first = await ProjectionService(FakeCogneeClient(), store).build_index(command)
    second = await ProjectionService(FakeCogneeClient(), store).rebuild(command)

    after = {path: path.read_bytes() for path in command.manifest_paths}
    assert after == before
    assert second.revision_ids == first.revision_ids


@pytest.mark.asyncio
async def test_forbidden_scope_is_filtered_from_results(tmp_path: Path) -> None:
    store = ProjectionStore(tmp_path / "projections.db")
    service = ProjectionService(FakeCogneeClient(), store)
    command = build_command(tmp_path, travel_metadata("c1"), engineering_metadata())
    await service.build_index(command)
    client = FakeCogneeClient(
        [
            {"id": "engineering-name", "text": "Aurora", "chunk_index": 0},
            {"id": "c1", "text": "1200 рублей", "chunk_index": 1},
        ]
    )

    result = await CogneeRetriever(client, store).retrieve(query())

    assert [chunk.reference.source_id for chunk in result.chunks] == ["travel-policy"]


def test_cognee_paths_are_configured_before_real_import(tmp_path: Path) -> None:
    script = (
        "from pathlib import Path\n"
        "from cognee_retriever.cognee_client import configure_local_cognee_paths\n"
        f"local = configure_local_cognee_paths(Path({str(tmp_path)!r}))\n"
        "import os, sys\n"
        "assert 'cognee' not in sys.modules\n"
        "assert os.environ['SYSTEM_ROOT_DIRECTORY'] == str(local / 'system')\n"
        "print(os.environ['DATA_ROOT_DIRECTORY'])\n"
    )

    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        text=True,
        capture_output=True,
        cwd=Path.cwd(),
    )

    assert str(tmp_path / "data") in completed.stdout


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("LLM_API_KEY"), reason="LLM_API_KEY is not configured")
async def test_real_cognee_returns_expected_chunk(tmp_path: Path) -> None:
    from cognee_retriever.cognee_client import RealCogneeClient

    store = ProjectionStore(tmp_path / "projections.db")
    service = ProjectionService(RealCogneeClient(tmp_path / ".local"), store)
    await service.build_index(build_command(tmp_path, travel_metadata("c1")))
    result = await CogneeRetriever(RealCogneeClient(tmp_path / ".local"), store).retrieve(query())

    assert result.chunks
