from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ApiError(Exception):
    """Base application exception for API-layer errors."""

    message: str
    code: str = 'API_ERROR'
    status_code: int = 400
    request_id: str | None = None

    def __str__(self) -> str:
        return self.message
