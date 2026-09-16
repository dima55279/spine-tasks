from __future__ import annotations

from access_gateway.audit import AuditSink, denied_event
from access_gateway.models import (
    AccessPolicy,
    RetrievalQuery,
    RetrievalResult,
    RetrievedChunk,
    Retriever,
    Subject,
)


class AuthorizedRetriever:
    def __init__(self, inner: Retriever, policy: AccessPolicy, audit: AuditSink) -> None:
        self.inner = inner
        self.policy = policy
        self.audit = audit

    async def retrieve(self, subject: Subject, text: str) -> RetrievalResult:
        raw = await self.inner.retrieve(to_query(subject, text))
        allowed: list[RetrievedChunk] = []
        policy_versions: set[str] = set()
        for chunk in raw.chunks:
            decision = self.policy.can_read(subject, chunk)
            policy_versions.add(decision.policy_version)
            if decision.allowed:
                allowed.append(chunk)
            else:
                self.audit.record(denied_event(subject, chunk, decision))
        policy_version = ",".join(sorted(policy_versions)) if policy_versions else None
        return raw.model_copy(
            update={
                "chunks": tuple(allowed),
                "policy_version": policy_version,
            }
        )


def to_query(subject: Subject, text: str) -> RetrievalQuery:
    return RetrievalQuery(
        workspace_id=subject.workspace_id,
        user_id=subject.user_id,
        scopes=subject.scopes,
        text=text,
    )


class StaticRetriever:
    def __init__(self, chunks: tuple[RetrievedChunk, ...]) -> None:
        self.chunks = chunks
        self.received_queries: list[RetrievalQuery] = []

    async def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        self.received_queries.append(query)
        return RetrievalResult(
            chunks=self.chunks,
            strategy="static",
            index_version="test-index",
        )


class LeakyRetriever(StaticRetriever):
    pass
