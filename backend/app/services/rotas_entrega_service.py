from datetime import datetime
from math import atan2, cos, radians, sin, sqrt
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.rotas_entrega_models import RotaEntregaParada
from app.services.notificacao_entrega_service import notificar_proximo_cliente
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.utils.logger import logger
from app.vendas_models import Venda


_rotas_schema_checked = False


def ensure_rotas_entrega_schema(db: Session) -> None:
    """Compatibilidade de schema para rotas/paradas em ambientes legados."""
    global _rotas_schema_checked
    if _rotas_schema_checked:
        return

    db.execute(text("ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS km_inicial NUMERIC(10,2)"))
    db.execute(text("ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS km_final NUMERIC(10,2)"))
    db.execute(text("ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS token_rastreio VARCHAR(64)"))
    db.execute(text("ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS lat_atual NUMERIC(10,6)"))
    db.execute(text("ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS lon_atual NUMERIC(10,6)"))
    db.execute(text("ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS localizacao_atualizada_em TIMESTAMP"))
    db.execute(text("ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS distancia_total_km_real NUMERIC(10,3)"))
    db.execute(text("ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS distancia_retorno_km_real NUMERIC(10,3)"))
    db.execute(text("ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS observacoes TEXT"))
    db.execute(text("ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS km_entrega NUMERIC(10,2)"))
    db.execute(text("ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS lat_entrega NUMERIC(10,6)"))
    db.execute(text("ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS lon_entrega NUMERIC(10,6)"))
    db.execute(text("ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS distancia_trecho_real_km NUMERIC(10,3)"))
    db.execute(text("ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS distancia_acumulada_real_km NUMERIC(10,3)"))
    db.commit()
    _rotas_schema_checked = True


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula distancia entre 2 coordenadas geograficas em km."""
    raio_terra_km = 6371.0

    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return raio_terra_km * c


def _sincronizar_venda_entregue_por_parada(
    db: Session,
    parada: RotaEntregaParada,
    tenant_id,
    data_entrega: Optional[datetime] = None,
) -> Optional[Venda]:
    """Mantem Venda e parada alinhadas para o PDV/lista de entregas abertas."""
    entrega_em = data_entrega or parada.data_entrega or datetime.now()
    parada.status = "entregue"
    parada.data_entrega = entrega_em

    venda = db.query(Venda).filter(
        Venda.id == parada.venda_id,
        Venda.tenant_id == tenant_id,
    ).first()
    if venda:
        venda.status_entrega = "entregue"
        venda.data_entrega = entrega_em
    return venda


def _contar_paradas_nao_entregues(db: Session, rota_id: int, tenant_id) -> int:
    return db.query(RotaEntregaParada).filter(
        RotaEntregaParada.rota_id == rota_id,
        RotaEntregaParada.tenant_id == tenant_id,
        RotaEntregaParada.status != "entregue",
    ).count()


def _notificar_proximo_cliente_background(rota_id: int, parada_ordem: int, tenant_id) -> None:
    try:
        set_current_tenant(tenant_id)
        with SessionLocal() as db:
            notificar_proximo_cliente(db, rota_id, parada_ordem, tenant_id)
    except Exception as exc:
        logger.info(f"Erro ao notificar proximo cliente em background: {exc}")
    finally:
        clear_current_tenant()
