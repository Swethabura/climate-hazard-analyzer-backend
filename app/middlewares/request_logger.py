import logging
import uuid
import time

from fastapi import Request

logger = logging.getLogger("app.requests")

async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    started_at = time.perf_counter()
    
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "Request failed",
            extra={"request_id": request_id}
        )
        raise
    
    duration_ms = round(
        (time.perf_counter() - started_at) * 1000, 2
    )
    
    response.headers["X-Request-ID"] = request_id
    
    logger.info(
        "%s %s status=%s duration_ms=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        extra={"request_id": request_id},
    )
    
    return response
    