from __future__ import annotations

from datetime import datetime
from math import atan2, cos, radians, sin, sqrt
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Cliente
from app.rotas_entrega_models import RotaEntregaParada, RotaEntregaRastreioToken
from app.services.notificacao_entrega_service import notificar_proximo_cliente
from app.tenancy.context import clear_current_tenant, set_current_tenant, tenant_context
from app.utils.tenant_safe_sql import execute_tenant_safe
from app.utils.logger import logger
from app.vendas_models import Venda


_RASTREIO_ROTA_SQL = """
    SELECT id, numero, status, entregador_id, lat_atual, lon_atual, localizacao_atualizada_em,
        distancia_total_km_real, distancia_retorno_km_real
    FROM rotas_entrega
    WHERE {tenant_filter} AND id = :rid
    LIMIT 1
    """

_RASTREIO_DISTANCIAS_SQL = """
    SELECT id, distancia_trecho_real_km, distancia_acumulada_real_km
    FROM rotas_entrega_paradas
    WHERE {tenant_filter} AND rota_id = :rid
    """


def registrar_token_rastreio(
    db: Session, *, token: str, rota_id: int, tenant_id
) -> RotaEntregaRastreioToken:
    """Mantem o indice publico sincronizado sem expor dados da rota."""
    token_normalizado = str(token or "").strip()
    if not token_normalizado:
        raise ValueError("Token de rastreio obrigatorio")

    registro = (
        db.query(RotaEntregaRastreioToken)
        .filter(RotaEntregaRastreioToken.rota_id == rota_id)
        .first()
    )
    if registro is None:
        registro = RotaEntregaRastreioToken(
            token=token_normalizado,
            rota_id=rota_id,
            tenant_id=tenant_id,
        )
        db.add(registro)
    else:
        registro.token = token_normalizado
        registro.tenant_id = tenant_id
    return registro


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula distancia entre 2 coordenadas geograficas em km."""
    raio_terra_km = 6371.0

    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    )
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

    venda = (
        db.query(Venda)
        .filter(
            Venda.id == parada.venda_id,
            Venda.tenant_id == tenant_id,
        )
        .first()
    )
    if venda:
        venda.status_entrega = "entregue"
        venda.data_entrega = entrega_em
    return venda


def _contar_paradas_nao_entregues(db: Session, rota_id: int, tenant_id) -> int:
    return (
        db.query(RotaEntregaParada)
        .filter(
            RotaEntregaParada.rota_id == rota_id,
            RotaEntregaParada.tenant_id == tenant_id,
            RotaEntregaParada.status != "entregue",
        )
        .count()
    )


def _notificar_proximo_cliente_background(
    rota_id: int, parada_ordem: int, tenant_id
) -> None:
    try:
        set_current_tenant(tenant_id)
        with SessionLocal() as db:
            notificar_proximo_cliente(db, rota_id, parada_ordem, tenant_id)
    except Exception as exc:
        logger.info(f"Erro ao notificar proximo cliente em background: {exc}")
    finally:
        clear_current_tenant()


def atualizar_localizacao_real_rota(
    db: Session,
    *,
    rota_id: int,
    tenant_id,
    lat: float,
    lon: float,
    atualizada_em: datetime | None = None,
) -> float:
    loc_anterior = db.execute(
        text(
            """
            SELECT lat_atual, lon_atual
            FROM rotas_entrega
            WHERE id = :rid AND tenant_id = :tenant
            """
        ),
        {"rid": rota_id, "tenant": tenant_id},
    ).fetchone()

    delta_km = 0.0
    if loc_anterior and loc_anterior[0] is not None and loc_anterior[1] is not None:
        delta_km = _haversine_km(
            float(loc_anterior[0]), float(loc_anterior[1]), float(lat), float(lon)
        )
        if delta_km < 0.003:
            delta_km = 0.0
        if delta_km > 5:
            delta_km = 5.0

    if delta_km > 0:
        parada_pendente = db.execute(
            text(
                """
                SELECT id, ordem
                FROM rotas_entrega_paradas
                WHERE rota_id = :rid
                  AND tenant_id = :tenant
                  AND status <> 'entregue'
                ORDER BY ordem ASC
                LIMIT 1
                """
            ),
            {"rid": rota_id, "tenant": tenant_id},
        ).fetchone()

        if parada_pendente:
            parada_id, ordem_parada = parada_pendente
            db.execute(
                text(
                    """
                    UPDATE rotas_entrega_paradas
                    SET distancia_trecho_real_km = COALESCE(distancia_trecho_real_km, 0) + :delta
                    WHERE id = :pid AND tenant_id = :tenant
                    """
                ),
                {"delta": delta_km, "pid": parada_id, "tenant": tenant_id},
            )

            acumulada_real = (
                db.execute(
                    text(
                        """
                    SELECT COALESCE(SUM(COALESCE(distancia_trecho_real_km, 0)), 0)
                    FROM rotas_entrega_paradas
                    WHERE rota_id = :rid
                      AND tenant_id = :tenant
                      AND ordem <= :ordem
                    """
                    ),
                    {"rid": rota_id, "tenant": tenant_id, "ordem": ordem_parada},
                ).scalar()
                or 0
            )

            db.execute(
                text(
                    """
                    UPDATE rotas_entrega_paradas
                    SET distancia_acumulada_real_km = :acumulada
                    WHERE id = :pid AND tenant_id = :tenant
                    """
                ),
                {"acumulada": acumulada_real, "pid": parada_id, "tenant": tenant_id},
            )
        else:
            db.execute(
                text(
                    """
                    UPDATE rotas_entrega
                    SET distancia_retorno_km_real = COALESCE(distancia_retorno_km_real, 0) + :delta
                    WHERE id = :rid AND tenant_id = :tenant
                    """
                ),
                {"delta": delta_km, "rid": rota_id, "tenant": tenant_id},
            )

    db.execute(
        text(
            """
            UPDATE rotas_entrega
            SET lat_atual = :lat,
                lon_atual = :lon,
                localizacao_atualizada_em = :agora,
                distancia_total_km_real = COALESCE(distancia_total_km_real, 0) + :delta
            WHERE id = :rid AND tenant_id = :tenant
            """
        ),
        {
            "lat": lat,
            "lon": lon,
            "agora": atualizada_em or datetime.now(),
            "delta": delta_km,
            "rid": rota_id,
            "tenant": tenant_id,
        },
    )
    return delta_km


def _buscar_indice_rastreio(db: Session, token: str) -> RotaEntregaRastreioToken:
    token_normalizado = str(token or "").strip()
    if not token_normalizado or len(token_normalizado) > 64:
        raise HTTPException(
            status_code=404, detail="Rastreio nao encontrado ou link invalido"
        )
    registro = (
        db.query(RotaEntregaRastreioToken)
        .filter(RotaEntregaRastreioToken.token == token_normalizado)
        .first()
    )
    if registro:
        return registro
    raise HTTPException(
        status_code=404, detail="Rastreio nao encontrado ou link invalido"
    )


def _buscar_rota_rastreio(db: Session, *, rota_id: int, tenant_id):
    rota_row = execute_tenant_safe(
        db,
        _RASTREIO_ROTA_SQL,
        {"rid": rota_id},
        tenant_id=tenant_id,
    ).fetchone()
    if rota_row:
        return rota_row
    raise HTTPException(
        status_code=404, detail="Rastreio nao encontrado ou link invalido"
    )


def _buscar_entregador(db: Session, entregador_id, tenant_id):
    if not entregador_id:
        return None
    return (
        db.query(Cliente)
        .filter(Cliente.id == entregador_id, Cliente.tenant_id == tenant_id)
        .first()
    )


def _listar_paradas_rastreio(
    db: Session, rota_id: int, tenant_id
) -> list[RotaEntregaParada]:
    return (
        db.query(RotaEntregaParada)
        .filter(
            RotaEntregaParada.rota_id == rota_id,
            RotaEntregaParada.tenant_id == tenant_id,
        )
        .order_by(RotaEntregaParada.ordem)
        .all()
    )


def _distancias_por_parada(db: Session, rota_id: int, tenant_id) -> dict[int, tuple]:
    rows = execute_tenant_safe(
        db,
        _RASTREIO_DISTANCIAS_SQL,
        {"rid": rota_id},
        tenant_id=tenant_id,
    ).fetchall()
    return {row[0]: row for row in rows}


def _isoformat_or_none(value) -> str | None:
    return value.isoformat() if value else None


def _float_or_none(value) -> float | None:
    return float(value) if value is not None else None


def _montar_posicao(lat, lon, atualizada_em, fonte: str) -> dict | None:
    if lat is None or lon is None:
        return None
    return {
        "lat": float(lat),
        "lon": float(lon),
        "atualizada_em": _isoformat_or_none(atualizada_em),
        "fonte": fonte,
    }


def _coordenadas_entrega_parada(db: Session, parada_id: int, tenant_id):
    try:
        return execute_tenant_safe(
            db,
            """
            SELECT lat_entrega, lon_entrega
            FROM rotas_entrega_paradas
            WHERE {tenant_filter} AND id = :pid
            """,
            {"pid": parada_id},
            tenant_id=tenant_id,
        ).fetchone()
    except Exception:
        return None


def _ultima_posicao_por_paradas(
    db: Session, paradas: list[RotaEntregaParada], tenant_id
) -> dict | None:
    for parada in reversed(paradas):
        coordenadas = _coordenadas_entrega_parada(db, parada.id, tenant_id)
        if not coordenadas:
            continue
        posicao = _montar_posicao(
            coordenadas[0], coordenadas[1], parada.data_entrega, "ultima_parada"
        )
        if posicao:
            return posicao
    return None


def _montar_ultima_posicao(
    db: Session,
    paradas: list[RotaEntregaParada],
    lat_atual,
    lon_atual,
    localizacao_atualizada_em,
    tenant_id,
) -> dict | None:
    posicao_atual = _montar_posicao(
        lat_atual, lon_atual, localizacao_atualizada_em, "rota_atual"
    )
    if posicao_atual:
        return posicao_atual
    return _ultima_posicao_por_paradas(db, paradas, tenant_id)


def _distancia_ate_ultima_entrega(distancia_total_real, distancia_retorno_real):
    if distancia_total_real is None:
        return None
    return max(float(distancia_total_real or 0) - float(distancia_retorno_real or 0), 0)


def _valor_distancia_parada(
    dist_por_parada: dict[int, tuple], parada_id: int, index: int
):
    row = dist_por_parada.get(parada_id)
    if not row or row[index] is None:
        return None
    return float(row[index])


def _montar_parada_publica(
    parada: RotaEntregaParada, dist_por_parada: dict[int, tuple]
) -> dict:
    return {
        "ordem": parada.ordem,
        # O token e uma capacidade publica. Enderecos de outros clientes nao
        # podem aparecer para quem recebeu o link.
        "endereco": f"Entrega {parada.ordem}",
        "status": parada.status,
        "data_entrega": _isoformat_or_none(parada.data_entrega),
        "distancia_trecho_real_km": _valor_distancia_parada(
            dist_por_parada, parada.id, 1
        ),
        "distancia_acumulada_real_km": _valor_distancia_parada(
            dist_por_parada, parada.id, 2
        ),
    }


def montar_rastreio_publico(db: Session, token: str) -> dict:
    indice = _buscar_indice_rastreio(db, token)
    with tenant_context(indice.tenant_id) as tenant_id:
        return _montar_rastreio_publico_tenant(
            db,
            rota_id_indice=indice.rota_id,
            tenant_id=tenant_id,
        )


def _montar_rastreio_publico_tenant(
    db: Session, *, rota_id_indice: int, tenant_id
) -> dict:
    (
        rota_id,
        rota_numero,
        rota_status,
        entregador_id,
        lat_atual,
        lon_atual,
        localizacao_atualizada_em,
        distancia_total_real,
        distancia_retorno_real,
    ) = _buscar_rota_rastreio(
        db,
        rota_id=rota_id_indice,
        tenant_id=tenant_id,
    )

    entregador = _buscar_entregador(db, entregador_id, tenant_id)
    paradas = _listar_paradas_rastreio(db, rota_id, tenant_id)
    dist_por_parada = _distancias_por_parada(db, rota_id, tenant_id)
    ultima_posicao = _montar_ultima_posicao(
        db,
        paradas,
        lat_atual,
        lon_atual,
        localizacao_atualizada_em,
        tenant_id,
    )
    entregues = sum(1 for parada in paradas if parada.status == "entregue")
    total = len(paradas)

    return {
        "rota_numero": rota_numero,
        "status": rota_status,
        "entregador_nome": entregador.nome if entregador else "Entregador",
        "total_paradas": total,
        "entregues": entregues,
        "pendentes": total - entregues,
        "distancia_total_km_real": _float_or_none(distancia_total_real),
        "distancia_retorno_km_real": _float_or_none(distancia_retorno_real),
        "distancia_ate_ultima_entrega_km_real": _distancia_ate_ultima_entrega(
            distancia_total_real, distancia_retorno_real
        ),
        "ultima_posicao_gps": ultima_posicao,
        "paradas": [
            _montar_parada_publica(parada, dist_por_parada) for parada in paradas
        ],
    }
