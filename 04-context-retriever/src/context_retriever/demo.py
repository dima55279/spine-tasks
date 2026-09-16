from __future__ import annotations

import asyncio
import json
from pathlib import Path

from context_retriever.fake_retriever import FakeRetriever
from context_retriever.models import ContextProviderError, RetrievalQuery, result_from_payload


def build_demo_retriever(path: Path | None = None) -> FakeRetriever:
    data_path = path or Path("data/fixtures/fake-results.json")
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    answers = {
        question: result_from_payload(chunks, index_version=payload["index_version"])
        for question, chunks in payload["answers"].items()
    }
    errors = {
        question: ContextProviderError(code)
        for question, code in payload.get("errors", {}).items()
    }
    return FakeRetriever(answers=answers, errors=errors)


async def run_demo() -> None:
    retriever = build_demo_retriever()
    result = await retriever.retrieve(
        RetrievalQuery(
            workspace_id="alpha",
            user_id="demo-user",
            scopes=frozenset({"all-employees"}),
            text="Какой размер суточных?",
        )
    )
    print(f"Найдено фрагментов: {len(result.chunks)}")
    for chunk in result.chunks:
        print(f"Источник: {chunk.reference.source_id}")
        print(f"Редакция: {chunk.reference.revision_id}")
        print(f"Текст: {chunk.text}")


def main() -> None:
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
