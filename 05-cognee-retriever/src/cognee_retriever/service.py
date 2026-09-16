from __future__ import annotations

from cognee_retriever.models import BuildIndexCommand, CogneeClient, ProjectionVersion
from cognee_retriever.projections import load_chunk_metadata, revision_ids_for
from cognee_retriever.storage import ProjectionStore


class ProjectionService:
    def __init__(self, client: CogneeClient, store: ProjectionStore) -> None:
        self.client = client
        self.store = store

    async def build_index(self, command: BuildIndexCommand) -> ProjectionVersion:
        chunks = load_chunk_metadata(command.manifest_paths, command.access_map_path)
        revision_ids = revision_ids_for(chunks)
        version = self.store.create_building(command.workspace_id, revision_ids)
        self.store.save_chunks(version.projection_id, chunks)
        try:
            await self.client.remember(
                [chunk.text for chunk in chunks if chunk.workspace_id == command.workspace_id],
                dataset_name=version.dataset_name,
            )
        except Exception as error:
            self.store.mark_failed(version.projection_id, error.__class__.__name__)
            raise
        return self.store.mark_active(version.projection_id)

    async def rebuild(self, command: BuildIndexCommand) -> ProjectionVersion:
        return await self.build_index(command)

    def activate_index(self, workspace_id: str, projection_id) -> ProjectionVersion:
        return self.store.activate(workspace_id, projection_id)
