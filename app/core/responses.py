from typing import Any


def success_response(
    message: str, data: Any = None, meta: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {"success": True, "message": message, "data": data, "meta": meta or {}}
