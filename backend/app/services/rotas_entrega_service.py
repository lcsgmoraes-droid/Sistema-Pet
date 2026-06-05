from datetime import datetime
from math import atan2, cos, radians, sin, sqrt
import secrets
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


def montar_origem_config_entrega(config) -> str:
    return ", ".join(filter(None, [
        config.logradouro,
        config.numero,
        config.bairro,
        config.cidade,
        config.estado,
        config.cep,
    ]))


def aplicar_ordem_otimizada_em_vendas(vendas, ordem_indices):
    for posicao, indice_original in enumerate(ordem_indices, start=1):
        if indice_original < len(vendas):
            vendas[indice_original].ordem_entrega_otimizada = posicao
    return [vendas[i].numero_venda for i in ordem_indices]


def enriquecer_rota_para_resposta(
    db: Session,
    rota,
    tenant_id,
    *,
    commit_token: bool = False,
):
    """Carrega campos legados de GPS/rastreio e ordena paradas para resposta da API."""
    loc = db.execute(
        text(
            """
            SELECT lat_atual, lon_atual, localizacao_atualizada_em, token_rastreio
                 , distancia_total_km_real, distancia_retorno_km_real
            FROM rotas_entrega
            WHERE id = :rid AND tenant_id = :tenant
            """
        ),
        {"rid": rota.id, "tenant": tenant_id},
    ).fetchone()
    if loc:
        rota.lat_atual = loc[0]
        rota.lon_atual = loc[1]
        rota.localizacao_atualizada_em = loc[2]
        token_rastreio = loc[3]
        rota.distancia_total_km_real = loc[4]
        rota.distancia_retorno_km_real = loc[5]
        if loc[4] is not None:
            total_real = float(loc[4])
            retorno_real = float(loc[5] or 0)
            rota.distancia_ate_ultima_entrega_km_real = max(total_real - retorno_real, 0)
        if not token_rastreio:
            token_rastreio = secrets.token_urlsafe(32)
            db.execute(
                text(
                    """
                    UPDATE rotas_entrega
                    SET token_rastreio = :token
                    WHERE id = :rid AND tenant_id = :tenant
                    """
                ),
                {"token": token_rastreio, "rid": rota.id, "tenant": tenant_id},
            )
            if commit_token:
                db.commit()
        rota.token_rastreio = token_rastreio

    if rota.paradas:
        dist_rows = db.execute(
            text(
                """
                SELECT id, distancia_trecho_real_km, distancia_acumulada_real_km
                FROM rotas_entrega_paradas
                WHERE rota_id = :rid AND tenant_id = :tenant
                """
            ),
            {"rid": rota.id, "tenant": tenant_id},
        ).fetchall()
        dist_por_parada = {row[0]: row for row in dist_rows}

        rota.paradas = sorted(rota.paradas, key=lambda p: p.ordem)
        for parada in rota.paradas:
            dist_row = dist_por_parada.get(parada.id)
            if dist_row:
                parada.distancia_trecho_real_km = dist_row[1]
                parada.distancia_acumulada_real_km = dist_row[2]
            if parada.venda and parada.venda.cliente:
                parada.cliente_nome = parada.venda.cliente.nome
                parada.cliente_telefone = parada.venda.cliente.telefone
                parada.cliente_celular = parada.venda.cliente.celular

    return rota
