from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router as api_router
from app.config import get_settings
from app.core.exceptions.base import ApiError
from app.core.middleware.security import SecurityHeadersMiddleware
from app.lifecycle import lifespan

settings = get_settings()

app = FastAPI(
    title='The Textile Care API',
    version='0.1.0',
    description='Shared backend foundation for The Textile Care platform.',
    lifespan=lifespan,
)

allowed_origins = [origin.strip() for origin in settings.cors_allowed_origins.split(',') if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.add_middleware(SecurityHeadersMiddleware)


@app.middleware('http')
async def add_request_id(request, call_next):
    request_id = request.headers.get('x-request-id') or request.headers.get('X-Request-Id')
    if not request_id:
        request_id = 'req-' + __import__('uuid').uuid4().hex
    response = await call_next(request)
    response.headers['X-Request-Id'] = request_id
    return response


@app.exception_handler(ApiError)
async def api_error_handler(_, exc: ApiError):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=exc.status_code,
        content={
            'error': {
                'code': exc.code,
                'message': exc.message,
                'request_id': exc.request_id,
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_, exc: Exception):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=500,
        content={
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An unexpected error occurred',
                'request_id': 'unknown-request',
            }
        },
    )


app.include_router(api_router)


@app.get('/')
async def root() -> dict[str, str]:
    return {'status': 'ok', 'service': settings.app_name}
