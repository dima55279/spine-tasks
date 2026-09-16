# QA API

HTTP-служба вопросов на FastAPI для задания 08 направления «Инфраструктура базы
знаний и агента вопросов и ответов».

## Установка

`uv` должен быть установлен как глобальный инструмент рабочего окружения.

```bash
uv sync --dev
```

## Запуск

```bash
uv run uvicorn qa_api.main:app --reload --port 8080
```

Проверка:

```bash
curl -s http://127.0.0.1:8080/health/ready

curl -s -X POST http://127.0.0.1:8080/api/v1/ask \
  -H 'Content-Type: application/json' \
  -d '{"workspace_id":"alpha","user_id":"u-1","scopes":["all-employees"],"question":"Какой размер суточных?","request_id":"r-1"}'
```

## Архитектура

- `routes.py` содержит HTTP-методы.
- `dependencies.py` собирает службу с программными заглушками.
- `service.py` содержит `AskQuestion` без зависимости от FastAPI.
- `main.py` создаёт приложение и обработчик прикладных ошибок.

## Проверки

```bash
uv run ruff check .
uv run pytest -q -m 'not integration and not llm'
uv run python -m compileall -q src tests
```
