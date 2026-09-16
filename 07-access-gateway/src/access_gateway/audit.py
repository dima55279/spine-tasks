from __future__ import annotations

from pathlib import Path

import structlog

from access_gateway.models import AccessDecision, AuditEvent, RetrievedChunk, Subject


class AuditSink:
    def record(self, event: AuditEvent) -> None:
        raise NotImplementedError


class InMemoryAuditSink(AuditSink):
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def record(self, event: AuditEvent) -> None:
        self.events.append(event)


class JsonlAuditSink(AuditSink):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.logger = structlog.get_logger("security")

    def record(self, event: AuditEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(event.model_dump_json())
            stream.write("\n")
        self.logger.info("access_denied", **event.model_dump())


def denied_event(
    subject: Subject,
    chunk: RetrievedChunk,
    decision: AccessDecision,
) -> AuditEvent:
    return AuditEvent(
        event_type="access_denied",
        user_id=subject.user_id,
        workspace_id=subject.workspace_id,
        subject_scopes=tuple(sorted(subject.scopes)),
        source_id=chunk.reference.source_id,
        chunk_id=chunk.reference.chunk_id,
        chunk_workspace_id=chunk.workspace_id,
        required_scope=chunk.required_scope,
        reason_code=decision.reason_code,
        policy_version=decision.policy_version,
    )
