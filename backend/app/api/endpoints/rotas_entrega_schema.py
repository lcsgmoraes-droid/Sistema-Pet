from __future__ import annotations

from threading import Lock

from sqlalchemy import text
from sqlalchemy.orm import Session


_rotas_schema_checked = False
_rotas_schema_lock = Lock()

_REQUIRED_COLUMNS = {
    "rotas_entrega": {
        "km_inicial",
        "km_final",
        "token_rastreio",
        "lat_atual",
        "lon_atual",
        "localizacao_atualizada_em",
        "distancia_total_km_real",
        "distancia_retorno_km_real",
    },
    "rotas_entrega_paradas": {
        "observacoes",
        "km_entrega",
        "lat_entrega",
        "lon_entrega",
        "distancia_trecho_real_km",
        "distancia_acumulada_real_km",
    },
}


def _schema_is_current(db: Session) -> bool:
    rows = db.execute(
        text(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name IN ('rotas_entrega', 'rotas_entrega_paradas')
            """
        )
    ).fetchall()
    found = {table_name: set() for table_name in _REQUIRED_COLUMNS}
    for table_name, column_name in rows:
        if table_name in found:
            found[table_name].add(column_name)
    return all(
        required.issubset(found[table_name])
        for table_name, required in _REQUIRED_COLUMNS.items()
    )


def ensure_rotas_entrega_schema(db: Session) -> None:
    """Compatibilidade de schema para rotas/paradas em ambientes legados."""
    global _rotas_schema_checked
    if _rotas_schema_checked:
        return

    with _rotas_schema_lock:
        if _rotas_schema_checked:
            return

        # Ambientes atuais ja receberam essas colunas por migration. Consultar o
        # catalogo evita obter locks exclusivos com ALTER TABLE a cada worker.
        if _schema_is_current(db):
            _rotas_schema_checked = True
            return

        # Instancias legadas ainda podem precisar do fallback. O advisory lock
        # serializa workers/processos para que apenas um deles execute o DDL.
        db.execute(text("SELECT pg_advisory_xact_lock(739204817)"))
        if _schema_is_current(db):
            db.commit()
            _rotas_schema_checked = True
            return

        statements = [
            "ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS km_inicial NUMERIC(10,2)",
            "ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS km_final NUMERIC(10,2)",
            "ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS token_rastreio VARCHAR(64)",
            "ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS lat_atual NUMERIC(10,6)",
            "ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS lon_atual NUMERIC(10,6)",
            "ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS localizacao_atualizada_em TIMESTAMP",
            "ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS distancia_total_km_real NUMERIC(10,3)",
            "ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS distancia_retorno_km_real NUMERIC(10,3)",
            "ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS observacoes TEXT",
            "ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS km_entrega NUMERIC(10,2)",
            "ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS lat_entrega NUMERIC(10,6)",
            "ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS lon_entrega NUMERIC(10,6)",
            "ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS distancia_trecho_real_km NUMERIC(10,3)",
            "ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS distancia_acumulada_real_km NUMERIC(10,3)",
        ]
        for statement in statements:
            db.execute(text(statement))
        db.commit()
        _rotas_schema_checked = True
