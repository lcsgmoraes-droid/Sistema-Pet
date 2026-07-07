"""Helpers compartilhados para saneamentos financeiros historicos."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session


def _run_saneamento_transacional(
    db: Session,
    *,
    actions: list[dict[str, Any]],
    apply_changes: bool,
    apply_actions: Callable[
        [Session, list[dict[str, Any]]], list[dict[str, Any]]
    ],
) -> list[dict[str, Any]]:
    applied: list[dict[str, Any]] = []
    try:
        if apply_changes:
            applied = apply_actions(db, actions)
            db.commit()
        else:
            db.rollback()
    except Exception:
        db.rollback()
        raise
    return applied
