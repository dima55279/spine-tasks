# Document Chunks

Разборщик Markdown/TXT и JSONL-manifest со стабильными ссылками на фрагменты
для задания 02 направления «Инфраструктура базы знаний и агента вопросов и
ответов».

## Установка

`uv` должен быть установлен как глобальный инструмент рабочего окружения.

```bash
uv sync --dev
```

## Подготовка данных

```bash
mkdir -p data/fixtures
cp ../synthetic-data/01-knowledge-base-and-qa/documents/alpha/travel-policy-v2.md data/fixtures/
cp ../synthetic-data/01-knowledge-base-and-qa/documents/alpha/remote-work.md data/fixtures/
cp ../synthetic-data/01-knowledge-base-and-qa/invalid/empty.txt data/fixtures/
```

## Демонстрация

```bash
uv run python -m document_chunks.cli parse \
  --workspace alpha \
  --source travel-policy \
  --revision 11111111-1111-4111-8111-111111111111 \
  --file data/fixtures/travel-policy-v2.md

uv run python -m document_chunks.cli verify-manifest \
  --file data/fixtures/travel-policy-v2.md \
  --manifest data/manifests/11111111-1111-4111-8111-111111111111.jsonl
```

Команда `parse` создаёт `data/manifests/<revision_id>.jsonl`. Каждая строка
содержит текст фрагмента и locator с `char_start`/`char_end`. Команда
`verify-manifest` перечитывает исходный файл и проверяет, что каждый диапазон
точно возвращает сохранённый текст.

## Проверки

```bash
uv run ruff check .
uv run pytest -q
uv run python -m compileall -q src tests
```
