"""Ajustes locais para consultas interativas de busca."""

from sqlalchemy import text
from sqlalchemy.orm import Session


def desativar_jit_busca(db: Session, termo_busca: str | None) -> None:
    """Evita compilar JIT em buscas curtas, somente na transacao atual."""
    if not (termo_busca or "").strip():
        return

    if db.get_bind().dialect.name == "postgresql":
        # Os filtros de grupo/parceria superestimam o custo da consulta e podem
        # gastar segundos compilando JIT para uma execucao de milissegundos.
        # SET LOCAL nao altera outras sessoes nem persiste apos commit/rollback.
        db.execute(text("SET LOCAL jit = off"))
