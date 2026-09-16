from __future__ import annotations

from answer_composer.composer import AnswerComposer
from answer_composer.models import RetrievedChunk, ValidatedAnswer
from answer_composer.validator import validate_answer


class AnswerService:
    def __init__(self, composer: AnswerComposer) -> None:
        self.composer = composer

    async def answer(
        self,
        question: str,
        chunks: tuple[RetrievedChunk, ...],
    ) -> ValidatedAnswer:
        draft = await self.composer.compose(question, chunks)
        return validate_answer(draft, chunks)
