from __future__ import annotations

from typing import Protocol

from context_retriever.models import RetrievalQuery, RetrievalResult


class Retriever(Protocol):
    async def retrieve(self, query: RetrievalQuery) -> RetrievalResult: ...
