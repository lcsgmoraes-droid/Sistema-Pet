from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


_rotas_schema_checked = False


def ensure_rotas_entrega_schema(db: Session) -> None:
    """Compatibilidade de schema para rotas/paradas em ambientes legados."""
    global _rotas_schema_checked
    if _rotas_schema_checked:
        return

    db.execute(
        text(
            "ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS km_inicial NUMERIC(10,2)"
        )
    )
    db.execute(
        text(
            "ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS km_final NUMERIC(10,2)"
        )
    )
    db.execute(
        text(
            "ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS token_rastreio VARCHAR(64)"
        )
    )
    db.execute(
        text(
            "ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS lat_atual NUMERIC(10,6)"
        )
    )
    db.execute(
        text(
            "ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS lon_atual NUMERIC(10,6)"
        )
    )
    db.execute(
        text(
            "ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS localizacao_atualizada_em TIMESTAMP"
        )
    )
    db.execute(
        text(
            "ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS distancia_total_km_real NUMERIC(10,3)"
        )
    )
    db.execute(
        text(
            "ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS distancia_retorno_km_real NUMERIC(10,3)"
        )
    )
    db.execute(
        text(
            "ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS observacoes TEXT"
        )
    )
    db.execute(
        text(
            "ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS km_entrega NUMERIC(10,2)"
        )
    )
    db.execute(
        text(
            "ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS lat_entrega NUMERIC(10,6)"
        )
    )
    db.execute(
        text(
            "ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS lon_entrega NUMERIC(10,6)"
        )
    )
    db.execute(
        text(
            "ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS distancia_trecho_real_km NUMERIC(10,3)"
        )
    )
    db.execute(
        text(
            "ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS distancia_acumulada_real_km NUMERIC(10,3)"
        )
    )
    db.commit()
    _rotas_schema_checked = True
