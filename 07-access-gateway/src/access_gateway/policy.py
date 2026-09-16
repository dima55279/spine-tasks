from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from access_gateway.models import AccessDecision, RetrievedChunk, Subject

POLICY_VERSION = "access-policy-v1"


class ScopeAccessPolicy:
    def __init__(self, policy_version: str = POLICY_VERSION) -> None:
        self.policy_version = policy_version

    def can_read(self, subject: Subject, chunk: RetrievedChunk) -> AccessDecision:
        if not subject.user_id:
            return self._deny("MISSING_SUBJECT")
        if not subject.scopes:
            return self._deny("MISSING_SCOPE")
        if subject.workspace_id != chunk.workspace_id:
            return self._deny("WORKSPACE_MISMATCH")
        if chunk.required_scope not in subject.scopes:
            return self._deny("MISSING_REQUIRED_SCOPE")
        return AccessDecision(
            allowed=True,
            reason_code="ALLOWED",
            policy_version=self.policy_version,
        )

    def _deny(self, reason_code: str) -> AccessDecision:
        return AccessDecision(
            allowed=False,
            reason_code=reason_code,
            policy_version=self.policy_version,
        )


def load_required_scopes(path: Path) -> dict[tuple[str, str, UUID], str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    scopes: dict[tuple[str, str, UUID], str] = {}
    for source in payload["sources"]:
        scopes[
            (
                source["workspace_id"],
                source["source_id"],
                UUID(source["revision_id"]),
            )
        ] = source["required_scope"]
    return scopes
