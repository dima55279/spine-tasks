from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from uuid import UUID, uuid4

from ingestion_runner.idempotency import IdempotencyStore
from ingestion_runner.logging import get_logger
from ingestion_runner.models import (
    DocumentParser,
    IngestCommand,
    IngestionReceipt,
    ItemReceipt,
    ParsedChunk,
    RegisterResult,
    RevisionService,
    SourceDocument,
    SourceRevision,
    TextLocator,
)

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


class UnsafePathError(ValueError):
    pass


class EmptyDocumentError(ValueError):
    pass


def media_type_for(path: Path) -> str:
    if path.suffix == ".md":
        return "text/markdown"
    return "text/plain"


def source_id_for(path: Path) -> str:
    return path.stem


def discover_documents(directory: Path) -> tuple[Path, ...]:
    root = directory.resolve()
    paths: list[Path] = []
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        if path.suffix not in {".md", ".txt"}:
            continue
        if path.is_symlink():
            resolved = path.resolve()
            if not resolved.is_relative_to(root):
                raise UnsafePathError(f"Symlink escapes input directory: {path}")
        if not path.is_file():
            continue
        paths.append(path)
    return tuple(paths)


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while block := stream.read(64 * 1024):
            digest.update(block)
    return digest.hexdigest()


def chunk_id(revision_id: UUID, ordinal: int, text: str) -> str:
    digest = sha256()
    digest.update(str(revision_id).encode("utf-8"))
    digest.update(b"\0")
    digest.update(str(ordinal).encode("ascii"))
    digest.update(b"\0")
    digest.update(text.encode("utf-8"))
    return digest.hexdigest()


class JsonlRevisionService:
    def __init__(self, path: Path) -> None:
        self.path = path

    def register_file(
        self, workspace_id: str, source_id: str, path: Path, media_type: str
    ) -> RegisterResult:
        checksum = file_sha256(path)
        for revision in self._read_all():
            if (
                revision.workspace_id == workspace_id
                and revision.source_id == source_id
                and revision.checksum_sha256 == checksum
            ):
                return RegisterResult(status="unchanged", revision=revision)

        revision = SourceRevision(
            revision_id=uuid4(),
            workspace_id=workspace_id,
            source_id=source_id,
            checksum_sha256=checksum,
            media_type=media_type,
            original_path=str(path),
            observed_at=datetime.now(UTC),
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(revision.model_dump_json())
            stream.write("\n")
        return RegisterResult(status="created", revision=revision)

    def _read_all(self) -> tuple[SourceRevision, ...]:
        if not self.path.exists():
            return ()
        revisions = []
        with self.path.open("r", encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    revisions.append(SourceRevision.model_validate_json(line))
        return tuple(revisions)


class MarkdownParser:
    def __init__(self, max_chars: int = 600) -> None:
        self.max_chars = max_chars

    def parse(self, document: SourceDocument) -> tuple[ParsedChunk, ...]:
        if document.text == "":
            raise EmptyDocumentError("document is empty")

        chunks: list[ParsedChunk] = []
        heading: str | None = None
        ordinal = 0
        paragraph_start: int | None = None
        parts: list[str] = []

        def flush() -> None:
            nonlocal ordinal, paragraph_start, parts
            if paragraph_start is None:
                return
            paragraph = "".join(parts).rstrip("\r\n")
            for start, end in self._split_span(document.text, paragraph_start, paragraph):
                text = document.text[start:end]
                locator = TextLocator(heading=heading, char_start=start, char_end=end)
                parsed = ParsedChunk(
                    chunk_id=chunk_id(document.revision_id, ordinal, text),
                    workspace_id=document.workspace_id,
                    source_id=document.source_id,
                    revision_id=document.revision_id,
                    ordinal=ordinal,
                    text=text,
                    locator=locator,
                )
                assert document.text[locator.char_start : locator.char_end] == parsed.text
                chunks.append(parsed)
                ordinal += 1
            paragraph_start = None
            parts = []

        position = 0
        for line in document.text.splitlines(keepends=True):
            line_start = position
            position += len(line)
            without_newline = line.rstrip("\r\n")
            match = HEADING_PATTERN.match(without_newline)
            if document.media_type == "text/markdown" and match:
                flush()
                heading = match.group(2).strip()
                continue
            if not without_newline.strip():
                flush()
                continue
            if paragraph_start is None:
                paragraph_start = line_start
            parts.append(line)
        flush()
        return tuple(chunks)

    def _split_span(self, original: str, start: int, text: str) -> tuple[tuple[int, int], ...]:
        spans: list[tuple[int, int]] = []
        offset = 0
        while offset < len(text):
            if len(text) - offset <= self.max_chars:
                spans.append((start + offset, start + len(text)))
                break
            limit = offset + self.max_chars
            split = self._find_split(text, offset, limit)
            spans.append((start + offset, start + split))
            offset = split
            while offset < len(text) and text[offset].isspace():
                offset += 1
        return tuple(span for span in spans if original[span[0] : span[1]])

    @staticmethod
    def _find_split(text: str, offset: int, limit: int) -> int:
        for index in range(limit, offset, -1):
            if text[index - 1].isspace():
                return index - 1
        index = limit
        while index < len(text) and not text[index].isspace():
            index += 1
        return index if index < len(text) else len(text)


def write_manifest(path: Path, chunks: tuple[ParsedChunk, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for chunk in chunks:
            stream.write(chunk.model_dump_json())
            stream.write("\n")


def count_manifest_chunks(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


class IngestionRunner:
    def __init__(
        self,
        revision_service: RevisionService,
        parser: DocumentParser,
        idempotency_store: IdempotencyStore,
        manifest_dir: Path,
    ) -> None:
        self.revision_service = revision_service
        self.parser = parser
        self.idempotency_store = idempotency_store
        self.manifest_dir = manifest_dir
        self.logger = get_logger()

    async def run(
        self, command: IngestCommand, *, continue_on_error: bool = False
    ) -> IngestionReceipt:
        existing = await self.idempotency_store.get(command.workspace_id, command.idempotency_key)
        if existing is not None:
            return existing

        run_id = uuid4()
        items: list[ItemReceipt] = []
        paths = discover_documents(command.directory)

        for path in paths:
            started = perf_counter()
            source_id = source_id_for(path)
            stage = "start"
            try:
                media_type = media_type_for(path)
                register_result = self.revision_service.register_file(
                    command.workspace_id, source_id, path, media_type
                )
                stage = "parse"
                text = path.read_text(encoding="utf-8")
                document = SourceDocument(
                    workspace_id=command.workspace_id,
                    source_id=source_id,
                    revision_id=register_result.revision.revision_id,
                    path=path,
                    text=text,
                    media_type=media_type,
                )
                chunks = self.parser.parse(document)
                manifest_path = self.manifest_dir / f"{register_result.revision.revision_id}.jsonl"
                write_manifest(manifest_path, chunks)
                status = "unchanged" if register_result.status == "unchanged" else "indexed"
                item = ItemReceipt(
                    source_id=source_id,
                    status=status,
                    revision_id=register_result.revision.revision_id,
                    chunk_count=len(chunks) or count_manifest_chunks(manifest_path),
                    error_code=None,
                )
                items.append(item)
                self._log(
                    run_id,
                    command.workspace_id,
                    source_id,
                    "manifest_ready",
                    started,
                    status,
                )
            except Exception as error:
                item = ItemReceipt(
                    source_id=source_id,
                    status="failed",
                    revision_id=None,
                    chunk_count=0,
                    error_code=error.__class__.__name__,
                )
                items.append(item)
                self._log(run_id, command.workspace_id, source_id, stage, started, "failed")
                if not continue_on_error:
                    receipt = IngestionReceipt(
                        run_id=run_id,
                        workspace_id=command.workspace_id,
                        items=tuple(items),
                    )
                    await self.idempotency_store.save_progress(receipt)
                    raise

            receipt = IngestionReceipt(
                run_id=run_id,
                workspace_id=command.workspace_id,
                items=tuple(items),
            )
            await self.idempotency_store.save_progress(receipt)

        receipt = IngestionReceipt(
            run_id=run_id,
            workspace_id=command.workspace_id,
            items=tuple(items),
        )
        await self.idempotency_store.save_final(
            command.workspace_id, command.idempotency_key, receipt
        )
        return receipt

    def _log(
        self,
        run_id: UUID,
        workspace_id: str,
        source_id: str,
        stage: str,
        started: float,
        status: str,
    ) -> None:
        self.logger.info(
            "ingestion_item",
            run_id=str(run_id),
            workspace_id=workspace_id,
            source_id=source_id,
            stage=stage,
            duration_ms=round((perf_counter() - started) * 1000, 3),
            status=status,
        )


def receipt_json(receipt: IngestionReceipt) -> str:
    return json.dumps(receipt.model_dump(mode="json"), ensure_ascii=False, indent=2)
