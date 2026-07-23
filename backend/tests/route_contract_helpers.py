"""Helpers para inspecionar rotas FastAPI em diferentes versoes."""

from collections.abc import Iterator
from typing import Any


def _join_path(prefix: str, path: str) -> str:
    if not prefix:
        return path
    if path == prefix or path.startswith(f"{prefix}/"):
        return path
    return f"{prefix.rstrip('/')}/{path.lstrip('/')}"


def iter_routes(router: Any, prefix: str = "") -> Iterator[tuple[str, set[str]]]:
    """Expande rotas diretas e inclusoes lazy introduzidas pelo FastAPI."""

    for route in router.routes:
        included_router = getattr(route, "original_router", None)
        if included_router is not None:
            include_context = getattr(route, "include_context", None)
            context_prefix = getattr(include_context, "prefix", "") or ""
            nested_prefix = context_prefix or _join_path(
                prefix,
                getattr(included_router, "prefix", "") or "",
            )
            yield from iter_routes(included_router, nested_prefix)
            continue

        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if path and methods:
            yield _join_path(prefix, path), set(methods)


def method_routes(router: Any) -> list[tuple[str, str]]:
    return [
        (path, method) for path, methods in iter_routes(router) for method in methods
    ]


def route_paths(router: Any) -> list[str]:
    return [path for path, _methods in iter_routes(router)]
