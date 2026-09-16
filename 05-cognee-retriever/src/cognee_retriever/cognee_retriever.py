from __future__ import annotations

from cognee_retriever.models import (
    CogneeClient,
    ContextReference,
    RetrievalQuery,
    RetrievalResult,
    RetrievedChunk,
)
from cognee_retriever.storage import ProjectionStore


class CogneeRetriever:
    def __init__(self, client: CogneeClient, store: ProjectionStore) -> None:
        self.client = client
        self.store = store

    async def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        active = self.store.active_version(query.workspace_id)
        if active is None:
            return RetrievalResult(chunks=(), strategy="cognee-chunks", index_version="none")

        payloads = await self.client.recall(query.text, dataset_name=active.dataset_name)
        metadata_by_id = self.store.chunks_for(active.projection_id)
        chunks: list[RetrievedChunk] = []
        for payload in payloads:
            chunk_id = str(payload.get("id"))
            metadata = metadata_by_id.get(chunk_id)
            if metadata is None:
                continue
            if metadata.workspace_id != query.workspace_id:
                continue
            if metadata.required_scope not in query.scopes:
                continue
            chunks.append(
                RetrievedChunk(
                    workspace_id=metadata.workspace_id,
                    required_scope=metadata.required_scope,
                    text=str(payload.get("text") or metadata.text),
                    reference=ContextReference(
                        source_id=metadata.source_id,
                        revision_id=metadata.revision_id,
                        chunk_id=metadata.chunk_id,
                        locator=metadata.locator,
                    ),
                )
            )
        return RetrievalResult(
            chunks=tuple(chunks),
            strategy="cognee-chunks",
            index_version=active.dataset_name,
        )
