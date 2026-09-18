from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info('Application startup initialized', extra={'service': settings.app_name})
    yield
    logger.info('Application shutdown complete', extra={'service': settings.app_name})
