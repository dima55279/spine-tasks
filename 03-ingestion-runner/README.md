# Ingestion Runner

Повторяемая загрузка каталога документов для задания 03 направления
«Инфраструктура базы знаний и агента вопросов и ответов».

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
cp ../synthetic-data/01-knowledge-base-and-qa/documents/alpha/security-policy.md data/fixtures/
```

## Демонстрация

```bash
uv run python -m ingestion_runner.cli ingest \
  --workspace alpha \
  --directory data/fixtures \
  --idempotency-key demo-001 \
  --continue-on-error
```

Команда обрабатывает только `.md` и `.txt`, сортирует пути, регистрирует редакции,
создаёт manifest-файлы в `data/manifests/` и сохраняет защиту от повторного запуска
в `data/runs.db`. Повтор с тем же `--idempotency-key` возвращает прежний receipt.

## Проверки

```bash
uv run ruff check .
uv run pytest -q -m 'not integration and not llm'
uv run python -m compileall -q src tests
```
