# Source Revisions

Хранилище неизменяемых редакций источников для задания 01 направления
«Инфраструктура базы знаний и агента вопросов и ответов».

## Установка

`uv` должен быть установлен как глобальный инструмент рабочего окружения.
Он не является зависимостью пакета `source-revisions`.

```bash
uv sync --extra dev
```

Если проект создаётся заново по правилам общей программы:

```bash
uv init --package --name source-revisions --python 3.11
uv add 'pydantic>=2.8,<3' 'typer>=0.12,<1'
uv add --dev 'pytest>=8,<9' 'pytest-asyncio>=0.23,<2' 'ruff>=0.6,<1'
```

## Подготовка данных

```bash
mkdir -p data/fixtures
cp ../synthetic-data/01-knowledge-base-and-qa/documents/alpha/travel-policy-v1.md data/fixtures/
cp ../synthetic-data/01-knowledge-base-and-qa/documents/alpha/travel-policy-v2.md data/fixtures/
```

## Демонстрация

```bash
uv run python -m source_revisions.cli register \
  --workspace alpha --source travel-policy --file data/fixtures/travel-policy-v1.md

uv run python -m source_revisions.cli register \
  --workspace alpha --source travel-policy --file data/fixtures/travel-policy-v1.md

uv run python -m source_revisions.cli register \
  --workspace alpha --source travel-policy --file data/fixtures/travel-policy-v2.md

uv run python -m source_revisions.cli tombstone \
  --workspace alpha --source travel-policy

uv run python -m source_revisions.cli history \
  --workspace alpha --source travel-policy
```

Первый запуск создаёт редакцию, повтор с тем же файлом возвращает `unchanged`,
регистрация второй версии создаёт новую редакцию, а `tombstone` добавляет отметку
об удалении без удаления прежних записей.

## Проверки

```bash
uv run ruff check .
uv run pytest -q -m 'not integration and not llm'
uv run python -m compileall -q src tests
```
