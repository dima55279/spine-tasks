from __future__ import annotations

from cognee_retriever.models import RetrievalQuery, RetrievalResult


class FakeRetriever:
    def __init__(
        self,
        answers: dict[str, RetrievalResult],
        errors: dict[str, Exception] | None = None,
    ) -> None:
        self.answers = answers
        self.errors = errors or {}
        self.received_queries: list[RetrievalQuery] = []

    async def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        self.received_queries.append(query)
        if query.text in self.errors:
            raise self.errors[query.text]
        return self.answers.get(
            query.text,
            RetrievalResult(chunks=(), strategy="configured-fake", index_version="fake-v1"),
        )


class FakeCogneeClient:
    def __init__(self, chunks: list[dict] | None = None, fail_remember: bool = False) -> None:
        self.chunks = chunks or []
        self.fail_remember = fail_remember
        self.remembered: list[tuple[str, list[str]]] = []
        self.recalled: list[tuple[str, str]] = []

    async def remember(self, texts: list[str], *, dataset_name: str) -> None:
        if self.fail_remember:
            raise RuntimeError("fake cognee build failure")
        self.remembered.append((dataset_name, list(texts)))

    async def recall(self, query_text: str, *, dataset_name: str) -> list[dict]:
        self.recalled.append((dataset_name, query_text))
        return list(self.chunks)
