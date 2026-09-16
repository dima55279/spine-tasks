from __future__ import annotations

import os
from pathlib import Path


def configure_local_cognee_paths(base: Path | None = None) -> Path:
    local = (base or Path(".local")).resolve()
    os.environ["SYSTEM_ROOT_DIRECTORY"] = str(local / "system")
    os.environ["DATA_ROOT_DIRECTORY"] = str(local / "data")
    os.environ["CACHE_ROOT_DIRECTORY"] = str(local / "cache")
    os.environ["COGNEE_LOGS_DIR"] = str(local / "logs")
    return local


class RealCogneeClient:
    def __init__(self, local_root: Path | None = None) -> None:
        self.local_root = local_root

    async def remember(self, texts: list[str], *, dataset_name: str) -> None:
        configure_local_cognee_paths(self.local_root)
        import cognee

        await cognee.remember(
            texts,
            dataset_name=dataset_name,
            self_improvement=False,
        )

    async def recall(self, query_text: str, *, dataset_name: str) -> list[dict]:
        configure_local_cognee_paths(self.local_root)
        import cognee
        from cognee import SearchType

        result = await cognee.recall(
            query_text=query_text,
            query_type=SearchType.CHUNKS,
            datasets=[dataset_name],
        )
        return list(result)
