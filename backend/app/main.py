from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as api_router
from app.core.config import settings
from app.core.exception_handlers import (
    app_exception_handler,
    generic_exception_handler,
)
from app.core.exceptions import AppException
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(
    title="Applications Tracker API",
    description="REST API for tracking job applications.",
    version="0.1.0",
)

app.include_router(api_router, prefix="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(
    AppException,
    app_exception_handler,
)

app.add_exception_handler(
    Exception,
    generic_exception_handler,
)
