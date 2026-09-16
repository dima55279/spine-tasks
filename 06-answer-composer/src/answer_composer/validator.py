from __future__ import annotations

from collections import OrderedDict

from answer_composer.models import ContextReference, DraftAnswer, RetrievedChunk, ValidatedAnswer

UNKNOWN_CITATION = "UNKNOWN_CITATION"
MISSING_CITATION = "MISSING_CITATION"
STALE_CITATION = "STALE_CITATION"
QUOTE_NOT_FOUND = "QUOTE_NOT_FOUND"
NO_SUPPORTED_CLAIMS = "NO_SUPPORTED_CLAIMS"


def validate_answer(
    draft: DraftAnswer,
    available: tuple[RetrievedChunk, ...],
) -> ValidatedAnswer:
    by_id = {item.reference.chunk_id: item for item in available}
    newest_by_source = _newest_revision_by_source(available)
    reasons: list[str] = []
    citations: OrderedDict[str, ContextReference] = OrderedDict()

    if not available:
        return _abstain(NO_SUPPORTED_CLAIMS)

    supported_claims: list[str] = []
    for claim in draft.claims:
        claim_reasons = _validate_claim(claim_text=claim.text, citation_ids=claim.citation_ids,
                                        by_id=by_id, newest_by_source=newest_by_source)
        if claim_reasons:
            reasons.extend(claim_reasons)
            continue

        supported_claims.append(claim.text)
        for citation_id in claim.citation_ids:
            chunk = by_id[citation_id]
            citations[chunk.reference.chunk_id] = chunk.reference

    if not supported_claims:
        if not reasons:
            reasons.append(NO_SUPPORTED_CLAIMS)
        return ValidatedAnswer(
            status="abstained",
            answer_text=None,
            citations=(),
            reasons=tuple(_unique(reasons)),
        )

    if reasons:
        return ValidatedAnswer(
            status="abstained",
            answer_text=None,
            citations=tuple(citations.values()),
            reasons=tuple(_unique(reasons)),
        )

    answer_text = draft.summary.strip() or "\n".join(supported_claims)
    return ValidatedAnswer(
        status="answered",
        answer_text=answer_text,
        citations=tuple(citations.values()),
        reasons=(),
    )


def _validate_claim(
    *,
    claim_text: str,
    citation_ids: tuple[str, ...],
    by_id: dict[str, RetrievedChunk],
    newest_by_source: dict[str, str],
) -> list[str]:
    reasons: list[str] = []
    if not citation_ids:
        return [MISSING_CITATION]

    cited_chunks: list[RetrievedChunk] = []
    for citation_id in citation_ids:
        chunk = by_id.get(citation_id)
        if chunk is None:
            reasons.append(UNKNOWN_CITATION)
            continue
        cited_chunks.append(chunk)
        newest_revision = newest_by_source[chunk.reference.source_id]
        if str(chunk.reference.revision_id) != newest_revision:
            reasons.append(STALE_CITATION)
    if cited_chunks and not _claim_is_supported_by_chunks(claim_text, tuple(cited_chunks)):
        reasons.append(QUOTE_NOT_FOUND)
    return reasons


def _newest_revision_by_source(available: tuple[RetrievedChunk, ...]) -> dict[str, str]:
    newest: dict[str, str] = {}
    for chunk in available:
        source_id = chunk.reference.source_id
        revision_id = str(chunk.reference.revision_id)
        newest[source_id] = max(newest.get(source_id, revision_id), revision_id)
    return newest


def _claim_is_supported_by_chunks(
    claim_text: str,
    chunks: tuple[RetrievedChunk, ...],
) -> bool:
    normalized_claim = _normalize(claim_text)
    normalized_text = _normalize(" ".join(chunk.text for chunk in chunks))
    if normalized_claim in normalized_text:
        return True
    claim_tokens = _tokens(normalized_claim)
    chunk_tokens = _tokens(normalized_text)
    return bool(claim_tokens) and claim_tokens.issubset(chunk_tokens)


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def _tokens(value: str) -> set[str]:
    return {
        token.strip(".,;:!?()[]{}«»\"'")
        for token in value.split()
        if len(token.strip(".,;:!?()[]{}«»\"'")) > 2
    }


def _abstain(reason: str) -> ValidatedAnswer:
    return ValidatedAnswer(status="abstained", answer_text=None, citations=(), reasons=(reason,))


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
