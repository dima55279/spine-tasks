# Cognee Retriever

Подключение Cognee и перестраиваемая проекция для задания 05 направления
«Инфраструктура базы знаний и агента вопросов и ответов».

## Установка

`uv` должен быть установлен как глобальный инструмент рабочего окружения.

```bash
uv sync --dev
```

Секреты храните в `.env`; в Git добавлен только пример [.env.example](.env.example).

## Локальные каталоги Cognee

`RealCogneeClient` перед первым `import cognee` направляет системные каталоги в
`.local/` текущего решения:

```text
.local/system
.local/data
.local/cache
.local/logs
```

## Данные

Для быстрых проверок используются prepared manifests в `data/fixtures/manifests/`
и `data/fixtures/access-map.json`. Индекс Cognee можно удалить и пересобрать из
manifest-файлов.

## Команды

```bash
uv run python -m cognee_retriever.cli build-index \
  --workspace alpha \
  --manifest-dir data/fixtures/manifests \
  --access-map data/fixtures/access-map.json

uv run python -m cognee_retriever.cli retrieve-context \
  --workspace alpha \
  --question "Какой размер суточных по действующим правилам?"

uv run python -m cognee_retriever.cli rebuild \
  --workspace alpha \
  --manifest-dir data/fixtures/manifests \
  --access-map data/fixtures/access-map.json
```

## Проверки

```bash
uv run ruff check .
uv run pytest -q -m 'not integration and not llm'
uv run python -m compileall -q src tests
```

Интеграционная проверка настоящего Cognee запускается отдельно и пропускается без
`LLM_API_KEY`:

```bash
uv run pytest -q -m integration
```
