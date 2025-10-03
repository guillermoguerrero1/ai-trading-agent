from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/debug/routes")
def list_routes(request: Request):
    items = []
    for r in request.app.router.routes:
        methods = sorted(getattr(r, "methods", []) or [])
        path = getattr(r, "path", "")
        items.append({"methods": methods, "path": path})
    return items
