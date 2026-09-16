from __future__ import annotations

from uuid import UUID

from access_gateway.models import ContextReference, RetrievedChunk, Subject


def employee() -> Subject:
    return Subject(
        user_id="employee-001",
        workspace_id="alpha",
        scopes=frozenset({"all-employees"}),
    )


def engineer() -> Subject:
    return Subject(
        user_id="engineer-001",
        workspace_id="alpha",
        scopes=frozenset({"all-employees", "engineering"}),
    )


def beta_user() -> Subject:
    return Subject(
        user_id="beta-001",
        workspace_id="beta",
        scopes=frozenset({"all-employees"}),
    )


def no_scope_user() -> Subject:
    return Subject(user_id="u-001", workspace_id="alpha", scopes=frozenset())


def travel_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        workspace_id="alpha",
        required_scope="all-employees",
        text="С 1 сентября суточные для поездок по России составляют 1200 рублей в день.",
        reference=ContextReference(
            source_id="travel-policy",
            revision_id=UUID("11111111-1111-4111-8111-222222222222"),
            chunk_id="travel-v2-daily",
            locator={"heading": "Суточные", "paragraph": 1},
        ),
    )


def engineering_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        workspace_id="alpha",
        required_scope="engineering",
        text="Кодовое имя прототипа — Aurora.",
        reference=ContextReference(
            source_id="engineering-only",
            revision_id=UUID("33333333-3333-4333-8333-333333333333"),
            chunk_id="engineering-name",
            locator={"heading": "Кодовое имя", "paragraph": 1},
        ),
    )


def beta_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        workspace_id="beta",
        required_scope="all-employees",
        text="Beta security policy text.",
        reference=ContextReference(
            source_id="security-policy",
            revision_id=UUID("66666666-6666-4666-8666-666666666666"),
            chunk_id="beta-security",
            locator={"heading": "Security", "paragraph": 1},
        ),
    )
