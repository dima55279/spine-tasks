# Context Retriever

Контракт получения контекста и программная заглушка для задания 04 направления
«Инфраструктура базы знаний и агента вопросов и ответов».

## Установка

`uv` должен быть установлен как глобальный инструмент рабочего окружения.

```bash
uv sync --dev
```

## Подготовка данных

```bash
mkdir -p data/fixtures
cp ../synthetic-data/01-knowledge-base-and-qa/retriever/fake-results.json data/fixtures/
```

## Демонстрация

```bash
uv run python -m context_retriever.demo
```

Ожидаемый смысл вывода:

```text
Найдено фрагментов: 1
Источник: travel-policy
Редакция: 11111111-1111-4111-8111-222222222222
Текст: С 1 сентября суточные для поездок по России составляют 1200 рублей в день.
```

## Проверки

```bash
uv run ruff check .
uv run pytest -q -m 'not integration and not llm'
uv run python -m compileall -q src tests
```
