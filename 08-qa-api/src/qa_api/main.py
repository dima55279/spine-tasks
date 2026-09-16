from __future__ import annotations

from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from qa_api.routes import router
from qa_api.schemas import ApiError, ErrorResponse
from qa_api.service import AppError


def create_app() -> FastAPI:
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        cache_logger_on_first_use=False,
    )
    app = FastAPI(title="QA API")
    app.include_router(router)

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, error: AppError) -> JSONResponse:
        trace_id = uuid4().hex
        status_code = 503 if error.retryable else 400
        payload = ErrorResponse(
            error=ApiError(
                code=error.code,
                message=error.message,
                trace_id=trace_id,
                retryable=error.retryable,
            )
        )
        structlog.get_logger("qa_api").warning(
            "app_error",
            trace_id=trace_id,
            code=error.code,
            retryable=error.retryable,
        )
        return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))

    return app


app = create_app()
