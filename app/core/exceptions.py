from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class BadRequestException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

class UnauthorizedException(HTTPException):
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )

class ForbiddenException(HTTPException):
    def __init__(self, detail: str = "You don't have permission to perform this action"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )

class NotFoundException(HTTPException):
    def __init__(self, entity: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity} not found"
        )

class AlreadyExistsException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )

class ModerationException(HTTPException):
    """
    Raised when Claude flags post content.
    Carries extra fields (reason, category) beyond standard error shape.
    The global handler unpacks these into the response.
    """
    def __init__(self, reason: str, category: str):
        self.moderation_reason   = reason
        self.moderation_category = category
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Your post was not published because it violates our community guidelines."
        )

class InternalException(HTTPException):
    def __init__(self, detail: str = "Something went wrong. Please try again."):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


def success(message: str, data: dict | list = None) -> dict:
    """
    Standard success envelope.
 
    Usage in routes:
        return success("Connected successfully")
        return success("Job created", data=job_dict)
        return success("Suggestions loaded", data={"suggestions": [...], "total": 5})
    """
    response = {"success": True, "message": message}
    if data is not None:
        response["data"] = data
    return response
 
 
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handles all HTTPException subclasses including our custom ones.
    ModerationException gets extra fields in the response.
    """
    if isinstance(exc, ModerationException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success":  False,
                "status":   exc.status_code,
                "error":    exc.detail,
                "reason":   exc.moderation_reason,
                "category": exc.moderation_category,
            }
        )
 
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "status":  exc.status_code,
            "error":   exc.detail,
        }
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handles Pydantic validation errors (missing fields, wrong types).
    Formats them into the same envelope as other errors.
    """
    errors = []
    for error in exc.errors():
        field = " → ".join(str(loc) for loc in error["loc"] if loc != "body")
        errors.append({
            "field":   field,
            "message": error["msg"],
            "type":    error["type"],
        })
 
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "status":  422,
            "error":   "Validation failed",
            "errors":  errors,
        }
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all for any unhandled Python exception.
    Prevents raw tracebacks leaking to the client.
    """
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "status":  500,
            "error":   "An unexpected error occurred. Please try again.",
        }
    )