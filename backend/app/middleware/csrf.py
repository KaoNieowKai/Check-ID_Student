"""CSRF defense-in-depth: Origin/Referer validation for state-changing requests.

This middleware validates that POST/PUT/DELETE/PATCH requests originate from
the same host as the application.  It is layered on top of SameSite=Lax
cookies for defense-in-depth.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from urllib.parse import urlparse

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


async def csrf_origin_check(request: Request, call_next):
    """Validate Origin/Referer header for state-changing requests.

    Rejects POST/PUT/DELETE/PATCH requests where the Origin (or Referer)
    does not match the application's host.
    """
    if request.method in SAFE_METHODS:
        return await call_next(request)

    origin = request.headers.get("origin")
    referer = request.headers.get("referer")

    request_host = request.headers.get("host", "")

    if origin:
        origin_host = urlparse(origin).netloc
        if origin_host != request_host:
            return JSONResponse(
                status_code=403,
                content={"detail": "Cross-origin request rejected"}
            )
    elif referer:
        referer_host = urlparse(referer).netloc
        if referer_host != request_host:
            return JSONResponse(
                status_code=403,
                content={"detail": "Cross-origin request rejected"}
            )
    # If neither Origin nor Referer is present, allow the request.
    # Same-origin form submits from some browsers may omit both headers.

    return await call_next(request)
