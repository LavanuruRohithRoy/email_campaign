from __future__ import annotations

from fastapi import HTTPException, status


def value_error_to_http_exception(exc: ValueError) -> HTTPException:
    code = str(exc)
    if code == "NOT_FOUND":
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Resource not found", "code": "NOT_FOUND"},
        )
    if code == "DUPLICATE_EMAIL":
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"detail": "Email already exists", "code": "DUPLICATE_EMAIL"},
        )
    if code == "EMAIL_SUPPRESSED":
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"detail": "Email is suppressed", "code": "EMAIL_SUPPRESSED"},
        )
    if code == "INVALID_CSV":
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"detail": "Invalid CSV file", "code": "INVALID_CSV"},
        )
    if code == "FILE_TOO_LARGE":
        return HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"detail": "File too large", "code": "FILE_TOO_LARGE"},
        )
    if code == "TEMPLATE_IN_USE":
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"detail": "Template is in use", "code": "TEMPLATE_IN_USE"},
        )
    if code == "NOT_DRAFT":
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"detail": "Only draft campaigns can be modified", "code": "NOT_DRAFT"},
        )
    if code == "NOT_SCHEDULED":
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"detail": "Only scheduled campaigns can be cancelled", "code": "NOT_SCHEDULED"},
        )
    if code == "NO_TEMPLATE":
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"detail": "Attach a template before scheduling", "code": "NO_TEMPLATE"},
        )
    if code == "NO_RECIPIENTS":
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"detail": "Add at least one recipient list or segment", "code": "NO_RECIPIENTS"},
        )
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"detail": code, "code": code},
    )