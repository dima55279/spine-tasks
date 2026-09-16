from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

import structlog

from qa_api.schemas import (
    AskRequest,
    AskResponse,
    Citation,
    Claim,
    DraftAnswer,
    RetrievalResult,
    RetrievedChunk,
)


class AppError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class RetrieverGateway(Protocol):
    async def retrieve(self, request: AskRequest) -> RetrievalResult: ...


class AnswerComposer(Protocol):
    async def compose(
        self, question: str, chunks: tuple[RetrievedChunk, ...]
    ) -> DraftAnswer: ...


class InMemoryRequestStore:
    def __init__(self) -> None:
        self._responses: dict[tuple[str, str], AskResponse] = {}

    def get(self, workspace_id: str, request_id: str) -> AskResponse | None:
        return self._responses.get((workspace_id, request_id))

    def save(self, workspace_id: str, request_id: str, response: AskResponse) -> None:
        self._responses[(workspace_id, request_id)] = response


class Clock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class AskQuestion:
    def __init__(
        self,
        gateway: RetrieverGateway,
        composer: AnswerComposer,
        request_store: InMemoryRequestStore,
        clock: Clock,
        *,
        compose_timeout_seconds: float = 2.0,
        trace_id_factory: Callable[[], str] | None = None,
        events: list[dict] | None = None,
    ) -> None:
        self.gateway = gateway
        self.composer = composer
        self.request_store = request_store
        self.clock = clock
        self.compose_timeout_seconds = compose_timeout_seconds
        self.trace_id_factory = trace_id_factory or (lambda: uuid4().hex)
        self.events = events
        self.logger = structlog.get_logger("qa_api")

    async def execute(self, request: AskRequest) -> AskResponse:
        existing = self.request_store.get(request.workspace_id, request.request_id)
        if existing is not None:
            return existing

        trace_id = self.trace_id_factory()
        self.logger.info(
            "ask_started",
            trace_id=trace_id,
            request_id=request.request_id,
            workspace_id=request.workspace_id,
            user_id=request.user_id,
        )
        self._record("ask_started", trace_id=trace_id, request_id=request.request_id)
        retrieval = await self.gateway.retrieve(request)
        if not retrieval.chunks:
            response = self._response(
                status="abstained",
                answer=None,
                citations=(),
                index_version=retrieval.index_version,
                policy_version=retrieval.policy_version,
                trace_id=trace_id,
                reasons=("NO_CONTEXT",),
            )
            self.request_store.save(request.workspace_id, request.request_id, response)
            return response

        try:
            draft = await asyncio.wait_for(
                self.composer.compose(request.question, retrieval.chunks),
                timeout=self.compose_timeout_seconds,
            )
        except TimeoutError as error:
            self.logger.warning("ask_timeout", trace_id=trace_id, request_id=request.request_id)
            self._record("ask_timeout", trace_id=trace_id, request_id=request.request_id)
            raise AppError(
                "COMPOSER_TIMEOUT",
                "Answer composer timed out",
                retryable=True,
            ) from error

        validated = validate_answer(draft, retrieval.chunks)
        response = self._response(
            status=validated["status"],
            answer=validated["answer"],
            citations=validated["citations"],
            index_version=retrieval.index_version,
            policy_version=retrieval.policy_version,
            trace_id=trace_id,
            reasons=validated["reasons"],
        )
        self.request_store.save(request.workspace_id, request.request_id, response)
        self.logger.info("ask_finished", trace_id=trace_id, status=response.status)
        self._record("ask_finished", trace_id=trace_id, status=response.status)
        return response

    def _record(self, event: str, **payload: str) -> None:
        if self.events is not None:
            self.events.append({"event": event, **payload})

    def _response(
        self,
        *,
        status: str,
        answer: str | None,
        citations: tuple[Citation, ...],
        index_version: str,
        policy_version: str | None,
        trace_id: str,
        reasons: tuple[str, ...],
    ) -> AskResponse:
        return AskResponse(
            status=status,  # type: ignore[arg-type]
            answer=answer,
            citations=citations,
            index_version=index_version,
            policy_version=policy_version,
            trace_id=trace_id,
            as_of=self.clock.now(),
            reasons=reasons,
        )


def validate_answer(
    draft: DraftAnswer,
    available: tuple[RetrievedChunk, ...],
) -> dict:
    by_id = {chunk.reference.chunk_id: chunk for chunk in available}
    citations: dict[str, Citation] = {}
    reasons: list[str] = []
    for claim in draft.claims:
        if not claim.citation_ids:
            reasons.append("MISSING_CITATION")
            continue
        for citation_id in claim.citation_ids:
            chunk = by_id.get(citation_id)
            if chunk is None:
                reasons.append("UNKNOWN_CITATION")
                continue
            if not _supported(claim.text, chunk.text):
                reasons.append("QUOTE_NOT_FOUND")
            citations[chunk.reference.chunk_id] = Citation(
                source_id=chunk.reference.source_id,
                revision_id=chunk.reference.revision_id,
                chunk_id=chunk.reference.chunk_id,
                locator=chunk.reference.locator,
            )
    if reasons or not draft.claims:
        return {"status": "abstained", "answer": None, "citations": (), "reasons": tuple(reasons)}
    return {
        "status": "answered",
        "answer": draft.summary,
        "citations": tuple(citations.values()),
        "reasons": (),
    }


def _supported(claim_text: str, chunk_text: str) -> bool:
    claim_tokens = _tokens(claim_text)
    chunk_tokens = _tokens(chunk_text)
    return bool(claim_tokens) and claim_tokens.issubset(chunk_tokens)


def _tokens(value: str) -> set[str]:
    return {
        token.strip(".,;:!?()[]{}«»\"'").casefold()
        for token in value.split()
        if len(token.strip(".,;:!?()[]{}«»\"'")) > 2
    }


class FakeGateway:
    def __init__(self, answers: dict[str, RetrievalResult]) -> None:
        self.answers = answers

    async def retrieve(self, request: AskRequest) -> RetrievalResult:
        result = self.answers.get(request.question)
        if result is None:
            return RetrievalResult(
                chunks=(),
                strategy="fake",
                index_version="fake-v1",
                policy_version="access-policy-v1",
            )
        chunks = tuple(
            chunk
            for chunk in result.chunks
            if chunk.workspace_id == request.workspace_id
            and chunk.required_scope in request.scopes
        )
        return result.model_copy(update={"chunks": chunks, "policy_version": "access-policy-v1"})


class FakeComposer:
    async def compose(self, question: str, chunks: tuple[RetrievedChunk, ...]) -> DraftAnswer:
        claims = tuple(
            Claim(text=chunk.text, citation_ids=(chunk.reference.chunk_id,))
            for chunk in chunks
        )
        return DraftAnswer(claims=claims, summary=" ".join(claim.text for claim in claims))


class SlowComposer:
    async def compose(self, question: str, chunks: tuple[RetrievedChunk, ...]) -> DraftAnswer:
        await asyncio.sleep(10)
        return DraftAnswer(claims=(), summary="")
