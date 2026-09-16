from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from document_chunks.markdown_parser import MarkdownParser, read_source_document
from document_chunks.models import EmptyDocumentError, SourceDocument

REVISION_ID = UUID("11111111-1111-4111-8111-111111111111")


def make_document(text: str, media_type: str = "text/markdown") -> SourceDocument:
    return SourceDocument(
        workspace_id="alpha",
        source_id="policy",
        revision_id=REVISION_ID,
        path=Path("policy.md"),
        text=text,
        media_type=media_type,
    )


def test_each_locator_returns_exact_text() -> None:
    text = "# Title\n\nFirst paragraph.\nStill first.\n\n## Details\n\nSecond paragraph."

    chunks = MarkdownParser(max_chars=600).parse(make_document(text))

    assert [chunk.locator.heading for chunk in chunks] == ["Title", "Details"]
    for chunk in chunks:
        assert text[chunk.locator.char_start : chunk.locator.char_end] == chunk.text


def test_repeated_parse_creates_same_chunk_ids() -> None:
    text = "# Title\n\nSame text.\n\nMore text."
    parser = MarkdownParser(max_chars=600)

    first = parser.parse(make_document(text))
    second = parser.parse(make_document(text))

    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]


def test_same_paragraph_in_different_places_has_different_ordinal_and_locator() -> None:
    text = "# Title\n\nRepeated paragraph.\n\nRepeated paragraph."

    chunks = MarkdownParser(max_chars=600).parse(make_document(text))

    assert len(chunks) == 2
    assert chunks[0].text == chunks[1].text
    assert chunks[0].ordinal != chunks[1].ordinal
    assert chunks[0].locator != chunks[1].locator
    assert chunks[0].chunk_id != chunks[1].chunk_id


def test_unicode_and_newlines_do_not_break_positions() -> None:
    text = "# Политика\n\nСтрока с emoji ☕ и кириллицей.\nВторая строка абзаца.\n\n終わり."

    chunks = MarkdownParser(max_chars=32).parse(make_document(text))

    assert chunks
    for chunk in chunks:
        assert text[chunk.locator.char_start : chunk.locator.char_end] == chunk.text


def test_chunk_does_not_exceed_limit_except_single_unsplittable_word() -> None:
    text = "one two three four five six seven eight"

    chunks = MarkdownParser(max_chars=10).parse(make_document(text))

    assert chunks
    assert all(len(chunk.text) <= 10 for chunk in chunks)

    long_word = "x" * 25
    long_word_chunks = MarkdownParser(max_chars=10).parse(make_document(long_word))
    assert [chunk.text for chunk in long_word_chunks] == [long_word]


def test_empty_file_raises_typed_error(tmp_path: Path) -> None:
    path = tmp_path / "empty.txt"
    path.write_text("", encoding="utf-8")

    with pytest.raises(EmptyDocumentError):
        read_source_document(path, "alpha", "empty", REVISION_ID, "text/plain")


@settings(max_examples=100)
@given(st.text(min_size=1).filter(lambda value: "\x00" not in value))
def test_locator_round_trip(text: str) -> None:
    chunks = MarkdownParser(max_chars=80).parse(make_document(text))
    for chunk in chunks:
        assert text[chunk.locator.char_start : chunk.locator.char_end] == chunk.text
