from __future__ import annotations

import re
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from document_chunks.models import (
    DocumentDecodeError,
    EmptyDocumentError,
    ParsedChunk,
    SourceDocument,
    TextLocator,
)

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def read_source_document(
    path: Path,
    workspace_id: str,
    source_id: str,
    revision_id: UUID,
    media_type: str = "text/markdown",
) -> SourceDocument:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise DocumentDecodeError(path, str(error)) from error

    if text == "":
        raise EmptyDocumentError(path)

    return SourceDocument(
        workspace_id=workspace_id,
        source_id=source_id,
        revision_id=revision_id,
        path=path,
        text=text,
        media_type=media_type,
    )


def make_chunk_id(revision_id: UUID, ordinal: int, text: str) -> str:
    digest = sha256()
    digest.update(str(revision_id).encode("utf-8"))
    digest.update(b"\0")
    digest.update(str(ordinal).encode("ascii"))
    digest.update(b"\0")
    digest.update(text.encode("utf-8"))
    return digest.hexdigest()


class MarkdownParser:
    def __init__(self, max_chars: int = 600) -> None:
        if max_chars < 1:
            raise ValueError("max_chars must be positive")
        self.max_chars = max_chars

    def parse(self, document: SourceDocument) -> tuple[ParsedChunk, ...]:
        chunks: list[ParsedChunk] = []
        original = document.text
        ordinal = 0
        heading: str | None = None
        paragraph_start: int | None = None
        paragraph_parts: list[str] = []

        def flush_paragraph() -> None:
            nonlocal ordinal, paragraph_start, paragraph_parts
            if paragraph_start is None:
                return

            paragraph = "".join(paragraph_parts).rstrip("\r\n")
            for start, end in self._split_span(original, paragraph_start, paragraph):
                text = original[start:end]
                locator = TextLocator(heading=heading, char_start=start, char_end=end)
                chunk = ParsedChunk(
                    chunk_id=make_chunk_id(document.revision_id, ordinal, text),
                    workspace_id=document.workspace_id,
                    source_id=document.source_id,
                    revision_id=document.revision_id,
                    ordinal=ordinal,
                    text=text,
                    locator=locator,
                )
                assert original[locator.char_start : locator.char_end] == chunk.text
                chunks.append(chunk)
                ordinal += 1

            paragraph_start = None
            paragraph_parts = []

        position = 0
        for line in original.splitlines(keepends=True):
            line_start = position
            line_end = line_start + len(line)
            position = line_end
            without_newline = line.rstrip("\r\n")

            match = HEADING_PATTERN.match(without_newline)
            if document.media_type == "text/markdown" and match:
                flush_paragraph()
                heading = match.group(2).strip()
                continue

            if not without_newline.strip():
                flush_paragraph()
                continue

            if paragraph_start is None:
                paragraph_start = line_start
            paragraph_parts.append(line)

        flush_paragraph()
        return tuple(chunks)

    def _split_span(self, original: str, start: int, text: str) -> list[tuple[int, int]]:
        spans: list[tuple[int, int]] = []
        offset = 0
        length = len(text)

        while offset < length:
            remaining = length - offset
            if remaining <= self.max_chars:
                spans.append((start + offset, start + length))
                break

            limit = offset + self.max_chars
            split = self._find_split(text, offset, limit)
            spans.append((start + offset, start + split))
            offset = split
            while offset < length and text[offset].isspace():
                offset += 1

        return [
            (span_start, span_end)
            for span_start, span_end in spans
            if original[span_start:span_end]
        ]

    @staticmethod
    def _find_split(text: str, offset: int, limit: int) -> int:
        for index in range(limit, offset, -1):
            if text[index - 1].isspace():
                return index - 1

        next_space = limit
        while next_space < len(text) and not text[next_space].isspace():
            next_space += 1
        if next_space < len(text):
            return next_space
        return len(text)
