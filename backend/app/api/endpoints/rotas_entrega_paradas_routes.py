from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.endpoints.rotas_entrega_auth import (
    DeliveryActor,
    _activate_delivery_actor_tenant,
    _rota_filters_for_actor,
    get_delivery_actor_and_tenant,
)
from app.api.endpoints.rotas_entrega_schema import ensure_rotas_entrega_schema
from app.api.endpoints.rotas_entrega_tracking import (
    _contar_paradas_nao_entregues,
    _notificar_proximo_cliente_background,
    _sincronizar_venda_entregue_por_parada,
    atualizar_localizacao_real_rota,
)
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.rotas_entrega_models import RotaEntrega, RotaEntregaParada
from app.services.notificacao_entrega_service import notificar_proximo_cliente
from app.services.order_push_notifications import notify_sale_order_event
from app.utils.logger import logger
from app.vendas_models import Venda

router = APIRouter()


class RegistrarRecebimentoPayload(BaseModel):
    forma_pagamento: str = Field(
        ..., description="pix | cartao_debito | cartao_credito"
    )
    numero_parcelas: int = Field(1, ge=1, le=12)


@router.post("/{rota_id}/paradas/{parada_id}/registrar-recebimento")
def registrar_recebimento_entregador(
    rota_id: str,
    parada_id: int,
    payload: RegistrarRecebimentoPayload,
    db: Session = Depends(get_session),
    actor: DeliveryActor = Depends(get_delivery_actor_and_tenant),
):
    """
    Pré-integração de recebimento no app do entregador.

    IMPORTANTE:
    - NÃO baixa financeiro ainda.
    - Apenas registra intenção de cobrança para ficar pronto para integração Stone/operadora.
    """
    tenant_id = _activate_delivery_actor_tenant(actor)

    forma = (payload.forma_pagamento or "").strip().lower()
    formas_validas = {"pix", "cartao_debito", "cartao_credito"}
    if forma not in formas_validas:
        raise HTTPException(status_code=400, detail="Forma de pagamento inválida")

    if forma != "cartao_credito" and payload.numero_parcelas != 1:
        raise HTTPException(
            status_code=400, detail="Parcelas só são permitidas para cartão de crédito"
        )

    rota = (
        db.query(RotaEntrega).filter(*_rota_filters_for_actor(actor, rota_id)).first()
    )
    if not rota:
        raise HTTPException(status_code=404, detail="Rota nao encontrada")

    parada = (
        db.query(RotaEntregaParada)
        .filter(
            RotaEntregaParada.id == parada_id,
            RotaEntregaParada.rota_id == rota.id,
            RotaEntregaParada.tenant_id == tenant_id,
        )
        .first()
    )
    if not parada:
        raise HTTPException(status_code=404, detail="Parada não encontrada")

    venda = (
        db.query(Venda)
        .filter(Venda.id == parada.venda_id, Venda.tenant_id == tenant_id)
        .first()
    )
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")

    parcelas_txt = f"{payload.numero_parcelas}x" if forma == "cartao_credito" else "1x"
    registro = (
        f"[RECEBIMENTO_APP] provider=stone status=pendente_integracao "
        f"forma={forma} parcelas={parcelas_txt} valor={float(venda.total or 0):.2f} "
        f"em={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    obs_atual = (parada.observacoes or "").strip()
    parada.observacoes = f"{obs_atual}\n{registro}".strip()

    venda_obs_atual = (venda.observacoes_entrega or "").strip()
    venda.observacoes_entrega = f"{venda_obs_atual}\n{registro}".strip()

    db.commit()

    return {
        "ok": True,
        "message": "Recebimento registrado no app e aguardando integração com a operadora",
        "integracao_status": "pendente_integracao",
        "provider": "stone",
        "forma_pagamento": forma,
        "numero_parcelas": payload.numero_parcelas,
        "valor": float(venda.total or 0),
    }


@router.get("/{rota_id}/paradas", response_model=List)
def listar_paradas_rota(
    rota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    ETAPA 9.3 - Lista paradas de uma rota na ordem otimizada
    """
    user, tenant_id = user_and_tenant

    # Validar que rota existe e pertence ao tenant
    rota = (
        db.query(RotaEntrega)
        .filter(RotaEntrega.id == rota_id, RotaEntrega.tenant_id == tenant_id)
        .first()
    )

    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    # Buscar paradas ordenadas
    paradas = (
        db.query(RotaEntregaParada)
        .filter(
            RotaEntregaParada.rota_id == rota_id,
            RotaEntregaParada.tenant_id == tenant_id,
        )
        .order_by(RotaEntregaParada.ordem)
        .all()
    )

    return paradas


@router.put("/{rota_id}/paradas/reordenar")
def reordenar_paradas(
    rota_id: str,
    nova_ordem=Body(...),  # Lista ou {"parada_ids": [...]} para compatibilidade com app
    db: Session = Depends(get_session),
    actor: DeliveryActor = Depends(get_delivery_actor_and_tenant),
):
    """
    ETAPA 9.3 - Reordena manualmente as paradas de uma rota

    Args:
        rota_id: ID da rota
        nova_ordem: Lista com IDs das paradas na ordem desejada [id1, id2, id3, ...]

    Exemplo:
        PUT /rotas-entrega/123/paradas/reordenar
        Body: [45, 47, 46]  # Ordem: parada 45 primeiro, depois 47, depois 46
    """
    tenant_id = _activate_delivery_actor_tenant(actor)
    if isinstance(nova_ordem, dict):
        ordem_ids = nova_ordem.get("parada_ids") or nova_ordem.get("nova_ordem")
    else:
        ordem_ids = nova_ordem
    if not isinstance(ordem_ids, list) or not all(
        isinstance(pid, int) for pid in ordem_ids
    ):
        raise HTTPException(status_code=400, detail="Lista de paradas invalida")

    # Validar que rota existe e pertence ao tenant
    rota = (
        db.query(RotaEntrega).filter(*_rota_filters_for_actor(actor, rota_id)).first()
    )

    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    if rota.status == "concluida":
        raise HTTPException(
            status_code=400, detail="Não é possível reordenar rota concluída"
        )

    # Buscar todas as paradas
    paradas = (
        db.query(RotaEntregaParada)
        .filter(
            RotaEntregaParada.rota_id == rota.id,
            RotaEntregaParada.tenant_id == tenant_id,
        )
        .all()
    )

    paradas_dict = {p.id: p for p in paradas}

    # Validar que todos os IDs fornecidos existem
    if set(ordem_ids) != set(paradas_dict.keys()):
        raise HTTPException(
            status_code=400, detail="Lista de IDs não corresponde às paradas da rota"
        )

    # Atualizar ordem
    for idx, parada_id in enumerate(ordem_ids):
        paradas_dict[parada_id].ordem = idx + 1

    db.commit()

    return {"message": "Ordem das paradas atualizada com sucesso"}


@router.post("/{rota_id}/atualizar-localizacao")
def atualizar_localizacao_rota(
    rota_id: str,
    lat: float,
    lon: float,
    db: Session = Depends(get_session),
    actor: DeliveryActor = Depends(get_delivery_actor_and_tenant),
):
    """
    Atualiza a localização atual do entregador para rastreio ao vivo.
    """
    tenant_id = _activate_delivery_actor_tenant(actor)
    ensure_rotas_entrega_schema(db)

    rota = (
        db.query(RotaEntrega).filter(*_rota_filters_for_actor(actor, rota_id)).first()
    )

    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    if rota.status not in ("em_rota", "em_andamento"):
        raise HTTPException(status_code=400, detail="Rota não está em andamento")

    atualizar_localizacao_real_rota(
        db,
        rota_id=rota.id,
        tenant_id=tenant_id,
        lat=lat,
        lon=lon,
    )
    db.commit()

    return {"ok": True}


@router.post("/{rota_id}/paradas/{parada_id}/marcar-entregue")
def marcar_parada_entregue(
    rota_id: str,
    parada_id: int,
    background_tasks: BackgroundTasks,
    tentativa: bool = False,
    km_entrega: Optional[float] = None,
    lat_entrega: Optional[float] = None,
    lon_entrega: Optional[float] = None,
    db: Session = Depends(get_session),
    actor: DeliveryActor = Depends(get_delivery_actor_and_tenant),
):
    """
    ETAPA 9.4 - Marca parada como entregue ou tentativa

    Args:
        tentativa: True se cliente ausente (não entregue)
        km_entrega: KM da moto no momento da entrega (opcional)
        lat_entrega: Latitude GPS no momento da entrega (opcional)
        lon_entrega: Longitude GPS no momento da entrega (opcional)
    """
    tenant_id = _activate_delivery_actor_tenant(actor)

    # Validar rota
    rota = (
        db.query(RotaEntrega).filter(*_rota_filters_for_actor(actor, rota_id)).first()
    )

    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    if rota.status not in ["em_rota", "em_andamento"]:
        if rota.status == "pendente":
            detail = "Para marcar a entrega, primeiro toque em Iniciar Rota."
        elif rota.status == "concluida":
            detail = "Esta rota ja foi finalizada."
        else:
            detail = f"Rota nao esta em andamento. Status atual: {rota.status}."
        raise HTTPException(status_code=400, detail=detail)

    # Validar parada
    parada = (
        db.query(RotaEntregaParada)
        .filter(
            RotaEntregaParada.id == parada_id,
            RotaEntregaParada.rota_id == rota.id,
            RotaEntregaParada.tenant_id == tenant_id,
        )
        .first()
    )

    if not parada:
        raise HTTPException(status_code=404, detail="Parada não encontrada")

    if parada.status == "entregue":
        _sincronizar_venda_entregue_por_parada(db, parada, tenant_id)
        db.commit()
        paradas_pendentes = _contar_paradas_nao_entregues(db, rota.id, tenant_id)
        mensagem = "Parada ja estava marcada como entregue."
        if paradas_pendentes == 0:
            mensagem += " Todas as paradas foram concluidas. Feche a rota."
        return {"message": mensagem, "paradas_pendentes": paradas_pendentes}

    venda_entregue = None

    # Marcar status
    if tentativa:
        parada.status = "tentativa"
        rota.tentativas += 1
        mensagem = "Tentativa registrada. Cliente ausente."
    else:
        parada.status = "entregue"
        parada.data_entrega = datetime.now()
        venda_entregue = _sincronizar_venda_entregue_por_parada(db, parada, tenant_id)

        # Registrar KM da entrega (opcional)
        if km_entrega is not None:
            parada.km_entrega = Decimal(str(km_entrega))
            logger.info(f"KM da entrega {parada_id}: {km_entrega}")

        # Registrar coordenadas GPS da entrega (opcional)
        if lat_entrega is not None and lon_entrega is not None:
            try:
                db.execute(
                    text(
                        """
                        UPDATE rotas_entrega_paradas
                        SET lat_entrega = :lat, lon_entrega = :lon
                        WHERE id = :pid AND tenant_id = :tenant
                        """
                    ),
                    {
                        "lat": lat_entrega,
                        "lon": lon_entrega,
                        "pid": parada_id,
                        "tenant": tenant_id,
                    },
                )
                logger.info(
                    f"GPS da entrega {parada_id}: lat={lat_entrega}, lon={lon_entrega}"
                )
            except Exception as e:
                logger.warning(f"Não foi possível salvar GPS da entrega: {e}")

        mensagem = "Parada marcada como entregue!"

        # ETAPA 9.4: Disparar mensagem para próximo cliente
        try:
            if background_tasks is not None:
                background_tasks.add_task(
                    _notificar_proximo_cliente_background,
                    rota.id,
                    parada.ordem,
                    tenant_id,
                )
                notificou = False
            else:
                notificou = notificar_proximo_cliente(
                    db, rota.id, parada.ordem, tenant_id
                )
            if notificou:
                mensagem += " Próximo cliente foi notificado."
        except Exception as e:
            # Log do erro mas não falha a operação
            logger.info(f"Erro ao notificar próximo cliente: {e}")

    db.commit()
    if venda_entregue is not None:
        notify_sale_order_event(db, venda=venda_entregue, event="delivered")

    # Verificar se todas as paradas foram entregues.
    # Tentativas ainda contam como abertas para impedir fechamento acidental.
    paradas_pendentes = _contar_paradas_nao_entregues(db, rota.id, tenant_id)

    if paradas_pendentes == 0:
        mensagem += " Todas as paradas foram concluídas. Feche a rota."

    return {"message": mensagem, "paradas_pendentes": paradas_pendentes}


@router.put("/{rota_id}/paradas/{parada_id}/observacao")
def adicionar_observacao_parada(
    rota_id: int,
    parada_id: int,
    observacao: str,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Adiciona ou atualiza observação sobre uma parada/entrega.
    Usado para aprendizado do sistema (ex: "Sempre entregar no vizinho").
    """
    user, tenant_id = user_and_tenant

    # Validar parada
    parada = (
        db.query(RotaEntregaParada)
        .filter(
            RotaEntregaParada.id == parada_id,
            RotaEntregaParada.rota_id == rota_id,
            RotaEntregaParada.tenant_id == tenant_id,
        )
        .first()
    )

    if not parada:
        raise HTTPException(status_code=404, detail="Parada não encontrada")

    parada.observacoes = observacao
    db.commit()

    return {"message": "Observação salva com sucesso", "observacoes": observacao}


@router.post("/{rota_id}/paradas/{parada_id}/nao-entregue")
def marcar_parada_nao_entregue(
    rota_id: str,
    parada_id: int,
    motivo: str = None,
    db: Session = Depends(get_session),
    actor: DeliveryActor = Depends(get_delivery_actor_and_tenant),
):
    """
    Marca parada como não entregue e reverte venda para status 'aberto'.
    Usada quando entrega não pode ser realizada (cliente ausente, cartão recusado, etc).
    """
    tenant_id = _activate_delivery_actor_tenant(actor)

    # Validar rota
    rota = (
        db.query(RotaEntrega).filter(*_rota_filters_for_actor(actor, rota_id)).first()
    )

    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    # Validar parada
    parada = (
        db.query(RotaEntregaParada)
        .filter(
            RotaEntregaParada.id == parada_id,
            RotaEntregaParada.rota_id == rota.id,
            RotaEntregaParada.tenant_id == tenant_id,
        )
        .first()
    )

    if not parada:
        raise HTTPException(status_code=404, detail="Parada não encontrada")

    # Salvar motivo como observação
    if motivo:
        obs_existente = parada.observacoes or ""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        parada.observacoes = (
            f"{obs_existente}\n[{timestamp}] Não entregue: {motivo}".strip()
        )

    # Reverter venda para status pendente (para aparecer na lista de entregas em aberto)
    venda = (
        db.query(Venda)
        .filter(
            Venda.id == parada.venda_id,
            Venda.tenant_id == tenant_id,
        )
        .first()
    )
    if venda:
        venda.status_entrega = "pendente"

    # Remover parada da rota
    venda_id = parada.venda_id
    db.delete(parada)
    db.flush()
    paradas_restantes = (
        db.query(RotaEntregaParada)
        .filter(
            RotaEntregaParada.rota_id == rota.id,
            RotaEntregaParada.tenant_id == tenant_id,
        )
        .count()
    )
    rota_removida = paradas_restantes == 0
    if rota_removida:
        db.delete(rota)

    db.commit()

    logger.info(
        f"Parada {parada_id} marcada como não entregue. Venda {venda_id} voltou para entregas em aberto."
    )

    return {
        "message": "Entrega marcada como não realizada. Venda voltou para entregas em aberto.",
        "venda_id": venda_id,
        "rota_removida": rota_removida,
        "paradas_restantes": paradas_restantes,
    }
