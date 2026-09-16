from __future__ import annotations

import json
from typing import Protocol

from answer_composer.models import DraftAnswer, RetrievedChunk


class AnswerComposer(Protocol):
    async def compose(
        self, question: str, chunks: tuple[RetrievedChunk, ...]
    ) -> DraftAnswer: ...


class FakeAnswerComposer:
    def __init__(self, answers: dict[str, DraftAnswer]) -> None:
        self.answers = answers
        self.received: list[tuple[str, tuple[RetrievedChunk, ...]]] = []

    async def compose(
        self, question: str, chunks: tuple[RetrievedChunk, ...]
    ) -> DraftAnswer:
        self.received.append((question, chunks))
        return self.answers.get(question, DraftAnswer(claims=(), summary=""))


class OpenAIAnswerComposer:
    def __init__(self, client, model: str = "gpt-4.1-mini") -> None:
        self.client = client
        self.model = model

    async def compose(
        self, question: str, chunks: tuple[RetrievedChunk, ...]
    ) -> DraftAnswer:
        numbered_chunks = [
            {
                "id": f"C{index}",
                "chunk_id": chunk.reference.chunk_id,
                "text": chunk.text,
            }
            for index, chunk in enumerate(chunks, start=1)
        ]
        response = await self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "developer",
                    "content": (
                        "Return JSON with keys summary and claims. "
                        "Each claim must have text and citation_ids. "
                        "Use only provided chunk_id values as citation_ids."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"question": question, "chunks": numbered_chunks},
                        ensure_ascii=False,
                    ),
                },
            ],
        )
        payload = json.loads(response.output_text)
        return DraftAnswer.model_validate(payload)
