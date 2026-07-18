import secrets
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.endpoints.rotas_entrega_auth import (
    DeliveryActor,
    _activate_delivery_actor_tenant,
    get_delivery_actor_and_tenant,
)
from app.api.endpoints.rotas_entrega_core_routes import obter_rota
from app.api.endpoints.rotas_entrega_tracking import registrar_token_rastreio
from app.db import get_session
from app.models import Cliente, ConfiguracaoEntrega
from app.rotas_entrega_models import RotaEntrega, RotaEntregaParada
from app.schemas.rota_entrega import RotaEntregaCreate, RotaEntregaResponse
from app.services.google_maps_service import (
    calcular_distancia_km,
    calcular_rota_otimizada,
)
from app.services.order_push_notifications import notify_sale_order_event
from app.utils.logger import logger
from app.vendas_models import Venda

router = APIRouter()


@router.post("/", response_model=RotaEntregaResponse)
def criar_rota(
    payload: RotaEntregaCreate,
    db: Session = Depends(get_session),
    actor: DeliveryActor = Depends(get_delivery_actor_and_tenant),
):
    """
    Cria uma nova rota de entrega.

    ETAPA 7.1: Copia valores de repasse da venda (snapshot).
    ETAPA 9.2: Calcula distância prevista automaticamente usando Google Maps.
    ETAPA 9.3: Suporta múltiplas vendas com ordem otimizada pelo Google Directions API.

    Modos de uso:
    1. Rota simples (1 venda): Informar venda_id
    2. Rota múltipla (N vendas): Informar vendas_ids (lista)
    """
    user = actor.user
    tenant_id = _activate_delivery_actor_tenant(actor)
    entregador_id = (
        actor.entregador.id if actor.entregador is not None else payload.entregador_id
    )
    vendas_ids = payload.vendas_ids or payload.venda_ids

    # Validar entregador
    if not entregador_id:
        raise HTTPException(status_code=400, detail="Entregador invalido")

    entregador = (
        db.query(Cliente)
        .filter(
            Cliente.id == entregador_id,
            Cliente.tenant_id == tenant_id,
            Cliente.is_entregador.is_(True),
            Cliente.entregador_ativo.is_(True),
        )
        .first()
    )

    if not entregador:
        raise HTTPException(status_code=400, detail="Entregador inválido")

    # Buscar configuração de entrega para obter ponto inicial
    config_entrega = (
        db.query(ConfiguracaoEntrega)
        .filter(ConfiguracaoEntrega.tenant_id == tenant_id)
        .first()
    )

    # ETAPA 9.3: Modo rota múltipla (várias vendas)
    if vendas_ids and len(vendas_ids) > 0:
        # Buscar vendas
        vendas_query = db.query(Venda).filter(
            Venda.id.in_(vendas_ids), Venda.tenant_id == tenant_id
        )
        if actor.entregador is not None:
            vendas_query = vendas_query.filter(
                Venda.tem_entrega.is_(True),
                or_(
                    Venda.status_entrega.in_(["pendente", "pronto"]),
                    Venda.status_entrega.is_(None),
                ),
                Venda.endereco_entrega.isnot(None),
                or_(
                    Venda.entregador_id == actor.entregador.id,
                    Venda.entregador_id.is_(None),
                ),
            )
        vendas = vendas_query.all()

        if len(vendas) != len(vendas_ids):
            raise HTTPException(
                status_code=404, detail="Uma ou mais vendas não encontradas"
            )

        # Validar que todas têm endereço
        if not all(v.endereco_entrega for v in vendas):
            raise HTTPException(
                status_code=400, detail="Todas as vendas devem ter endereço de entrega"
            )

        # Criar rota principal (sem venda_id específica, pois são várias)
        rota = RotaEntrega(
            tenant_id=tenant_id,
            entregador_id=entregador_id,
            moto_da_loja=payload.moto_da_loja,
            status="pendente",
            created_by=user.id,
        )
        rota.numero = f"ROTA-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        rota.token_rastreio = secrets.token_urlsafe(32)

        # Somar taxas de entrega de todas as vendas
        taxa_total = sum(v.taxa_entrega for v in vendas if v.taxa_entrega)
        repasse_total = sum(
            v.valor_taxa_entregador for v in vendas if v.valor_taxa_entregador
        )

        rota.taxa_entrega_cliente = taxa_total if taxa_total > 0 else None
        rota.valor_repasse_entregador = repasse_total if repasse_total > 0 else None

        # Definir pontos inicial e final
        # Montar endereço completo do ponto inicial a partir da configuração
        if config_entrega:
            ponto_inicial = (
                payload.ponto_inicial_rota
                or (
                    f"{config_entrega.logradouro or ''}"
                    f"{', ' + config_entrega.numero if config_entrega.numero else ''}"
                    f"{' - ' + config_entrega.complemento if config_entrega.complemento else ''}"
                    f"{' - ' + config_entrega.bairro if config_entrega.bairro else ''}"
                    f"{' - ' + config_entrega.cidade if config_entrega.cidade else ''}"
                    f"/{config_entrega.estado if config_entrega.estado else ''}"
                ).strip()
            )
        else:
            ponto_inicial = payload.ponto_inicial_rota

        rota.ponto_inicial_rota = ponto_inicial

        # Ponto final: por padrão é o mesmo do inicial (retorna à origem)
        if payload.retorna_origem is False:
            # Não retorna: ponto final é a última entrega
            rota.ponto_final_rota = (
                payload.ponto_final_rota or vendas[-1].endereco_entrega
            )
            rota.retorna_origem = False
        else:
            # Retorna à origem (padrão)
            rota.ponto_final_rota = ponto_inicial
            rota.retorna_origem = True

        db.add(rota)
        db.flush()  # Obter ID da rota
        registrar_token_rastreio(
            db,
            token=rota.token_rastreio,
            rota_id=rota.id,
            tenant_id=tenant_id,
        )

        # Calcular rota otimizada com Google Directions API
        if config_entrega and ponto_inicial:
            try:
                origem = ponto_inicial
                destinos = [v.endereco_entrega for v in vendas]

                # Chamar Google para otimizar
                ordem, legs = calcular_rota_otimizada(origem, destinos)

                # Criar paradas na ordem otimizada
                distancia_total = Decimal(0)
                tempo_total = 0

                for idx, ordem_google in enumerate(ordem):
                    venda = vendas[ordem_google]
                    leg = legs[idx]

                    # Acumular distância e tempo
                    distancia_total += Decimal(leg["distance"]["value"]) / Decimal(1000)
                    tempo_total += leg["duration"]["value"]

                    parada = RotaEntregaParada(
                        tenant_id=tenant_id,
                        rota_id=rota.id,
                        venda_id=venda.id,
                        ordem=idx + 1,
                        endereco=venda.endereco_entrega,
                        distancia_acumulada=distancia_total.quantize(Decimal("0.01")),
                        tempo_acumulado=tempo_total,
                    )
                    db.add(parada)

                # Atualizar distância prevista da rota
                rota.distancia_prevista = distancia_total.quantize(Decimal("0.01"))

            except Exception as e:
                # Se falhar otimização, criar paradas na ordem fornecida
                logger.info(f"[AVISO] Erro ao otimizar rota: {str(e)}")
                for idx, venda in enumerate(vendas):
                    parada = RotaEntregaParada(
                        tenant_id=tenant_id,
                        rota_id=rota.id,
                        venda_id=venda.id,
                        ordem=idx + 1,
                        endereco=venda.endereco_entrega,
                    )
                    db.add(parada)
        else:
            # Sem config, criar paradas na ordem fornecida
            for idx, venda in enumerate(vendas):
                parada = RotaEntregaParada(
                    tenant_id=tenant_id,
                    rota_id=rota.id,
                    venda_id=venda.id,
                    ordem=idx + 1,
                    endereco=venda.endereco_entrega,
                )
                db.add(parada)

        # Marcar vendas como "em_rota"
        for venda in vendas:
            venda.entregador_id = entregador_id
            venda.status_entrega = "em_rota"

        db.commit()
        for venda in vendas:
            notify_sale_order_event(db, venda=venda, event="out_for_delivery")
        db.refresh(rota)

        return obter_rota(rota_id=rota.id, db=db, actor=actor)

    # Modo tradicional: rota com 1 venda apenas
    # Buscar venda para obter endereço de destino
    venda_query = db.query(Venda).filter(
        Venda.id == payload.venda_id, Venda.tenant_id == tenant_id
    )
    if actor.entregador is not None:
        venda_query = venda_query.filter(
            Venda.tem_entrega.is_(True),
            or_(
                Venda.status_entrega.in_(["pendente", "pronto"]),
                Venda.status_entrega.is_(None),
            ),
            Venda.endereco_entrega.isnot(None),
            or_(
                Venda.entregador_id == actor.entregador.id,
                Venda.entregador_id.is_(None),
            ),
        )
    venda = venda_query.first()

    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")

    # ETAPA 9.2: Calcular distância prevista automaticamente
    distancia_prevista = payload.distancia_prevista  # Valor default do payload

    if config_entrega and config_entrega.ponto_inicial_rota and venda.endereco_entrega:
        try:
            # Calcular distância usando Google Maps
            origem = config_entrega.ponto_inicial_rota
            destino = venda.endereco_entrega

            distancia_prevista = calcular_distancia_km(origem, destino)

        except Exception as e:
            # Se falhar, logar erro mas não bloquear criação da rota
            logger.info(f"[AVISO] Erro ao calcular distância prevista: {str(e)}")
            # Usar distância fornecida no payload como fallback
            distancia_prevista = payload.distancia_prevista

    rota = RotaEntrega(
        tenant_id=tenant_id,
        venda_id=payload.venda_id,
        entregador_id=entregador_id,
        endereco_destino=payload.endereco_destino,
        distancia_prevista=distancia_prevista,  # Calculado automaticamente
        custo_previsto=payload.custo_previsto,
        moto_da_loja=payload.moto_da_loja,
        status="pendente",
        created_by=user.id,
        # ETAPA 7.1: Snapshot dos valores de repasse (se fornecidos)
        taxa_entrega_cliente=(
            payload.taxa_entrega_cliente
            if payload.taxa_entrega_cliente is not None
            else venda.taxa_entrega
        ),
        valor_repasse_entregador=(
            payload.valor_repasse_entregador
            if payload.valor_repasse_entregador is not None
            else venda.valor_taxa_entregador
        ),
    )

    # Número da rota (simples por enquanto)
    rota.numero = f"ROTA-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    rota.token_rastreio = secrets.token_urlsafe(32)

    db.add(rota)
    db.flush()
    registrar_token_rastreio(
        db,
        token=rota.token_rastreio,
        rota_id=rota.id,
        tenant_id=tenant_id,
    )
    db.add(
        RotaEntregaParada(
            tenant_id=tenant_id,
            rota_id=rota.id,
            venda_id=venda.id,
            ordem=1,
            endereco=venda.endereco_entrega or payload.endereco_destino,
            status="pendente",
        )
    )

    # Marcar venda como "em_rota"
    venda.entregador_id = entregador_id
    venda.status_entrega = "em_rota"

    db.commit()
    notify_sale_order_event(db, venda=venda, event="out_for_delivery")
    db.refresh(rota)

    return obter_rota(rota_id=rota.id, db=db, actor=actor)
