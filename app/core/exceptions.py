# app/core/exceptions.py

from fastapi import HTTPException, status


# ── 400 Bad Request ───────────────────────────────────────────
class BadRequestException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


# ── 401 Unauthorized ──────────────────────────────────────────
class UnauthorizedException(HTTPException):
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


# ── 403 Forbidden ─────────────────────────────────────────────
class ForbiddenException(HTTPException):
    def __init__(self, detail: str = "You don't have permission to perform this action"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


# ── 404 Not Found ─────────────────────────────────────────────
class NotFoundException(HTTPException):
    def __init__(self, entity: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity} not found"
        )


# ── 409 Conflict ──────────────────────────────────────────────
class AlreadyExistsException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )


# ── 422 Unprocessable ─────────────────────────────────────────
class ModerationException(HTTPException):
    def __init__(self, reason: str, category: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Your post was not published because it violates our community guidelines.",
                "reason": reason,
                "category": category
            }
        )


# ── 500 Internal ──────────────────────────────────────────────
class InternalException(HTTPException):
    def __init__(self, detail: str = "Something went wrong. Please try again."):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )