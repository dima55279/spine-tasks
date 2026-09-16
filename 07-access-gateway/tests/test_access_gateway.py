from __future__ import annotations

import json

import pytest
from factories import (
    beta_chunk,
    beta_user,
    employee,
    engineer,
    engineering_chunk,
    no_scope_user,
    travel_chunk,
)
from pydantic import ValidationError

from access_gateway.audit import InMemoryAuditSink, JsonlAuditSink
from access_gateway.authorized_retriever import (
    AuthorizedRetriever,
    LeakyRetriever,
    StaticRetriever,
)
from access_gateway.models import Subject
from access_gateway.policy import POLICY_VERSION, ScopeAccessPolicy


def gateway(chunks, audit=None) -> AuthorizedRetriever:
    return AuthorizedRetriever(
        inner=StaticRetriever(tuple(chunks)),
        policy=ScopeAccessPolicy(),
        audit=audit or InMemoryAuditSink(),
    )


@pytest.mark.asyncio
async def test_all_employees_user_does_not_see_engineering() -> None:
    audit = InMemoryAuditSink()
    result = await gateway([travel_chunk(), engineering_chunk()], audit).retrieve(
        employee(),
        "Какое кодовое имя?",
    )

    assert [chunk.reference.source_id for chunk in result.chunks] == ["travel-policy"]
    assert audit.events[0].source_id == "engineering-only"
    assert audit.events[0].reason_code == "MISSING_REQUIRED_SCOPE"


@pytest.mark.asyncio
async def test_engineer_sees_both_access_groups() -> None:
    result = await gateway([travel_chunk(), engineering_chunk()]).retrieve(
        engineer(),
        "Что доступно?",
    )

    assert [chunk.reference.source_id for chunk in result.chunks] == [
        "travel-policy",
        "engineering-only",
    ]
    assert result.policy_version == POLICY_VERSION


@pytest.mark.asyncio
async def test_beta_user_does_not_see_alpha_chunks() -> None:
    audit = InMemoryAuditSink()
    result = await gateway([travel_chunk()], audit).retrieve(beta_user(), "Суточные?")

    assert result.chunks == ()
    assert audit.events[0].reason_code == "WORKSPACE_MISMATCH"


@pytest.mark.asyncio
async def test_leaky_retriever_does_not_leak_closed_chunk() -> None:
    audit = InMemoryAuditSink()
    gateway = AuthorizedRetriever(
        inner=LeakyRetriever((engineering_chunk(),)),
        policy=ScopeAccessPolicy(),
        audit=audit,
    )

    result = await gateway.retrieve(employee(), "Как называется закрытый прототип?")

    assert result.chunks == ()
    assert audit.events[0].chunk_id == "engineering-name"


@pytest.mark.asyncio
async def test_missing_user_or_groups_do_not_mean_full_access() -> None:
    with pytest.raises(ValidationError):
        Subject(user_id="", workspace_id="alpha", scopes=frozenset({"all-employees"}))

    audit = InMemoryAuditSink()
    result = await gateway([travel_chunk()], audit).retrieve(no_scope_user(), "Суточные?")

    assert result.chunks == ()
    assert audit.events[0].reason_code == "MISSING_SCOPE"


@pytest.mark.asyncio
async def test_security_event_does_not_contain_closed_text(tmp_path) -> None:
    path = tmp_path / "security-events.jsonl"
    audit = JsonlAuditSink(path)
    gateway = AuthorizedRetriever(
        inner=LeakyRetriever((engineering_chunk(),)),
        policy=ScopeAccessPolicy(),
        audit=audit,
    )

    result = await gateway.retrieve(employee(), "Закрытый прототип?")

    assert result.chunks == ()
    raw = path.read_text(encoding="utf-8")
    event = json.loads(raw)
    assert "Aurora" not in raw
    assert event["source_id"] == "engineering-only"
    assert event["reason_code"] == "MISSING_REQUIRED_SCOPE"


@pytest.mark.asyncio
async def test_gateway_builds_query_from_subject() -> None:
    inner = StaticRetriever((beta_chunk(),))
    gateway = AuthorizedRetriever(inner, ScopeAccessPolicy(), InMemoryAuditSink())

    await gateway.retrieve(beta_user(), "Security?")

    assert inner.received_queries[0].workspace_id == "beta"
    assert inner.received_queries[0].user_id == "beta-001"
    assert inner.received_queries[0].scopes == frozenset({"all-employees"})
