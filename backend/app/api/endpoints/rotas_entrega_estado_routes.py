from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.endpoints.rotas_entrega_auth import (
    DeliveryActor,
    _activate_delivery_actor_tenant,
    _rota_filters_for_actor,
    get_delivery_actor_and_tenant,
)
from app.api.endpoints.rotas_entrega_core_routes import obter_rota
from app.api.endpoints.rotas_entrega_schema import ensure_rotas_entrega_schema
from app.api.endpoints.rotas_entrega_tracking import (
    _sincronizar_venda_entregue_por_parada,
)
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import Cliente
from app.models_configuracao_custo_moto import ConfiguracaoCustoMoto
from app.rotas_entrega_models import RotaEntrega, RotaEntregaParada
from app.schemas.rota_entrega import RotaEntregaResponse, RotaEntregaUpdate
from app.services.custo_moto_service import calcular_custo_moto
from app.services.custo_operacional_entrega_service import (
    consolidar_custos_por_entrega,
    registrar_snapshot_custo_paradas,
)
from app.services.notificacao_entrega_service import notificar_inicio_rota
from app.utils.logger import logger
from app.vendas_models import Venda

router = APIRouter()


@router.post("/{rota_id}/fechar", response_model=RotaEntregaResponse)
def fechar_rota(
    rota_id: str,
    payload: RotaEntregaUpdate,
    db: Session = Depends(get_session),
    actor: DeliveryActor = Depends(get_delivery_actor_and_tenant),
):
    """
    Fecha uma rota de entrega, calculando o custo real.

    Se km_inicial e km_final forem informados, calcula distancia_real automaticamente.
    """
    tenant_id = _activate_delivery_actor_tenant(actor)
    ensure_rotas_entrega_schema(db)

    rota = (
        db.query(RotaEntrega).filter(*_rota_filters_for_actor(actor, rota_id)).first()
    )

    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    if rota.status == "concluida":
        return obter_rota(rota_id=rota.id, db=db, actor=actor)

    entregador = (
        db.query(Cliente)
        .filter(Cliente.id == rota.entregador_id, Cliente.tenant_id == tenant_id)
        .first()
    )

    paradas = (
        db.query(RotaEntregaParada)
        .filter(
            RotaEntregaParada.rota_id == rota.id,
            RotaEntregaParada.tenant_id == tenant_id,
        )
        .order_by(RotaEntregaParada.ordem)
        .all()
    )

    # Compatibilidade com rotas simples antigas, criadas sem uma parada propria.
    if not paradas and rota.venda_id:
        venda_legada = (
            db.query(Venda)
            .filter(Venda.id == rota.venda_id, Venda.tenant_id == tenant_id)
            .first()
        )
        if venda_legada:
            parada_legada = RotaEntregaParada(
                tenant_id=tenant_id,
                rota_id=rota.id,
                venda_id=venda_legada.id,
                ordem=1,
                endereco=venda_legada.endereco_entrega or rota.endereco_destino or "Entrega",
                status="entregue",
                data_entrega=venda_legada.data_entrega or datetime.now(),
            )
            db.add(parada_legada)
            db.flush()
            paradas = [parada_legada]

    paradas_abertas = [p for p in paradas if p.status != "entregue"]
    if paradas_abertas:
        raise HTTPException(
            status_code=400,
            detail=(
                "Marque todas as paradas como entregues antes de fechar a rota. "
                f"Em aberto: {len(paradas_abertas)}."
            ),
        )

    quantidade_entregas = len(paradas) if paradas else (1 if rota.venda_id else 0)
    if quantidade_entregas == 0:
        raise HTTPException(
            status_code=400,
            detail="A rota nao possui entregas para finalizar.",
        )

    # Atualizar campos
    if payload.km_final is not None:
        rota.km_final = payload.km_final
        logger.info(f"KM final da rota: {payload.km_final}")

        # Se tem km_inicial e km_final, calcular distancia_real automaticamente
        if rota.km_inicial is not None:
            distancia_calculada = payload.km_final - rota.km_inicial
            if distancia_calculada > 0:
                rota.distancia_real = distancia_calculada
                logger.info(f"Distância calculada: {distancia_calculada} km")
            else:
                logger.warning(
                    f"KM final ({payload.km_final}) menor que inicial ({rota.km_inicial})"
                )

    # Se não calculou automaticamente, usar valor informado
    if payload.distancia_real is not None and rota.distancia_real is None:
        rota.distancia_real = payload.distancia_real

    if rota.distancia_real is None:
        dist_real_gps = db.execute(
            text(
                """
                SELECT distancia_total_km_real
                FROM rotas_entrega
                WHERE id = :rid AND tenant_id = :tenant
                """
            ),
            {"rid": rota.id, "tenant": tenant_id},
        ).scalar()
        if dist_real_gps is not None:
            rota.distancia_real = Decimal(str(dist_real_gps))

    conclusao_em = datetime.now()

    for parada in paradas:
        if parada.status == "entregue":
            _sincronizar_venda_entregue_por_parada(
                db,
                parada,
                tenant_id,
                parada.data_entrega or conclusao_em,
            )

    if not paradas and rota.venda_id:
        venda = (
            db.query(Venda)
            .filter(
                Venda.id == rota.venda_id,
                Venda.tenant_id == tenant_id,
            )
            .first()
        )
        if venda:
            venda.status_entrega = "entregue"
            venda.data_entrega = venda.data_entrega or conclusao_em

    rota.tentativas = max(int(rota.tentativas or 1), int(payload.tentativas or 1))
    rota.observacoes = payload.observacoes
    rota.status = "concluida"
    rota.data_conclusao = conclusao_em

    km_para_custo = rota.distancia_real or payload.distancia_real or Decimal("0")
    custo_moto_total = Decimal("0")
    if rota.moto_da_loja and km_para_custo:
        config_moto = (
            db.query(ConfiguracaoCustoMoto)
            .filter(ConfiguracaoCustoMoto.tenant_id == tenant_id)
            .first()
        )
        if config_moto:
            custo_moto_total = calcular_custo_moto(
                config=config_moto, km=km_para_custo
            )

    custos = consolidar_custos_por_entrega(
        paradas,
        entregador,
        distancia_total_km=km_para_custo,
        custo_moto_total=custo_moto_total,
        calculado_em=conclusao_em,
    )
    rota.custo_moto = custos.custo_moto
    rota.custo_real = custos.custo_total

    db.commit()
    db.refresh(rota)

    # 🔔 FINANCEIRO (STUB)
    # - Se terceirizado → gerar contas a pagar
    # - Registrar custo no DRE (incluindo custo da moto)
    # (entrará na ETAPA 5)

    return obter_rota(rota_id=rota.id, db=db, actor=actor)


@router.post("/{rota_id}/iniciar", response_model=RotaEntregaResponse)
def iniciar_rota(
    rota_id: str,
    km_inicial: Optional[float] = None,
    lat_inicio: Optional[float] = None,
    lon_inicio: Optional[float] = None,
    db: Session = Depends(get_session),
    actor: DeliveryActor = Depends(get_delivery_actor_and_tenant),
):
    """
    ETAPA 9.4 - Inicia navegação da rota

    - Marca status como em_rota
    - Registra data_inicio
    - Registra KM inicial da moto (opcional)
    - Dispara eventos de mensagens
    """
    tenant_id = _activate_delivery_actor_tenant(actor)
    ensure_rotas_entrega_schema(db)

    # Validar rota
    rota = (
        db.query(RotaEntrega).filter(*_rota_filters_for_actor(actor, rota_id)).first()
    )

    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    if rota.status != "pendente":
        raise HTTPException(
            status_code=400,
            detail=f"Rota não pode ser iniciada. Status atual: {rota.status}",
        )

    # Verificar se tem paradas
    paradas_rota = (
        db.query(RotaEntregaParada)
        .filter(
            RotaEntregaParada.rota_id == rota.id,
            RotaEntregaParada.tenant_id == tenant_id,
        )
        .order_by(RotaEntregaParada.ordem)
        .all()
    )

    # Compatibilidade com rotas simples antigas, criadas antes de toda venda
    # possuir uma parada propria para custo e rastreabilidade.
    if not paradas_rota and rota.venda_id:
        venda_legada = (
            db.query(Venda)
            .filter(Venda.id == rota.venda_id, Venda.tenant_id == tenant_id)
            .first()
        )
        if venda_legada:
            parada_legada = RotaEntregaParada(
                tenant_id=tenant_id,
                rota_id=rota.id,
                venda_id=venda_legada.id,
                ordem=1,
                endereco=venda_legada.endereco_entrega or rota.endereco_destino or "Entrega",
                status="pendente",
            )
            db.add(parada_legada)
            db.flush()
            paradas_rota = [parada_legada]

    if not paradas_rota:
        raise HTTPException(
            status_code=400, detail="Rota não possui paradas cadastradas"
        )

    entregador = (
        db.query(Cliente)
        .filter(Cliente.id == rota.entregador_id, Cliente.tenant_id == tenant_id)
        .first()
    )
    registrar_snapshot_custo_paradas(
        paradas_rota,
        entregador,
        registrado_em=datetime.now(),
    )

    # Iniciar rota
    rota.status = "em_rota"
    rota.data_inicio = datetime.now()

    # Zerar métricas reais de GPS no início da rota.
    # Se o app enviou a posição de partida, gravá-la já como ponto inicial
    # para que o primeiro ping de GPS calcule distância corretamente.
    db.execute(
        text(
            """
            UPDATE rotas_entrega
            SET lat_atual = :lat,
                lon_atual = :lon,
                localizacao_atualizada_em = CASE WHEN :lat IS NOT NULL THEN NOW() ELSE NULL END,
                distancia_total_km_real = 0,
                distancia_retorno_km_real = 0
            WHERE id = :rid AND tenant_id = :tenant
            """
        ),
        {"lat": lat_inicio, "lon": lon_inicio, "rid": rota.id, "tenant": tenant_id},
    )
    db.execute(
        text(
            """
            UPDATE rotas_entrega_paradas
            SET distancia_trecho_real_km = 0,
                distancia_acumulada_real_km = 0
            WHERE rota_id = :rid AND tenant_id = :tenant
            """
        ),
        {"rid": rota.id, "tenant": tenant_id},
    )

    # Registrar KM inicial (opcional)
    if km_inicial is not None:
        rota.km_inicial = Decimal(str(km_inicial))
        logger.info(f"KM inicial da rota: {km_inicial}")

    db.commit()
    db.refresh(rota)

    # ETAPA 9.4: Disparar mensagens automáticas para todos os clientes
    try:
        mensagens_enviadas = notificar_inicio_rota(db, rota.id, tenant_id)
        if mensagens_enviadas > 0:
            db.commit()  # Commit das mensagens
    except Exception as e:
        # Log do erro mas não falha a operação
        logger.info(f"Erro ao enviar notificações de início: {e}")

    return obter_rota(rota_id=rota.id, db=db, actor=actor)


@router.post("/{rota_id}/reverter-inicio", response_model=RotaEntregaResponse)
def reverter_inicio_rota(
    rota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Reverte o início de uma rota, voltando para status pendente.
    Só permite se nenhuma entrega foi realizada ainda.
    Útil quando inicia a rota mas precisa adicionar mais entregas antes de sair.
    """
    user, tenant_id = user_and_tenant

    # Validar rota
    rota = (
        db.query(RotaEntrega)
        .filter(RotaEntrega.id == rota_id, RotaEntrega.tenant_id == tenant_id)
        .first()
    )

    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    if rota.status != "em_rota":
        raise HTTPException(
            status_code=400,
            detail=f"Rota não pode ser revertida. Status atual: {rota.status}",
        )

    # Verificar se alguma parada já foi entregue
    paradas_entregues = (
        db.query(RotaEntregaParada)
        .filter(
            RotaEntregaParada.rota_id == rota_id, RotaEntregaParada.status == "entregue"
        )
        .count()
    )

    if paradas_entregues > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível reverter. {paradas_entregues} entrega(s) já foi(foram) realizada(s).",
        )

    # Reverter status
    rota.status = "pendente"
    rota.data_inicio = None

    db.commit()
    db.refresh(rota)

    logger.info(f"Rota #{rota_id} revertida para pendente")

    return rota


@router.delete("/{rota_id}")
def excluir_rota(
    rota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Exclui uma rota e reverte as vendas para status 'aberto' (voltam para listagem de entregas pendentes).

    IMPORTANTE:
    - Apenas rotas com status 'pendente' ou 'em_rota' podem ser excluídas
    - Rotas 'concluida' ou 'cancelada' não podem ser excluídas
    - Todas as vendas da rota voltam para status_entrega = 'aberto'
    """
    user, tenant_id = user_and_tenant

    # Buscar rota
    rota = (
        db.query(RotaEntrega)
        .filter(RotaEntrega.id == rota_id, RotaEntrega.tenant_id == tenant_id)
        .first()
    )

    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    # Validar se pode excluir
    if rota.status in ["concluida", "cancelada"]:
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível excluir rota com status '{rota.status}'",
        )

    # Buscar todas as paradas da rota
    paradas = (
        db.query(RotaEntregaParada)
        .filter(
            RotaEntregaParada.rota_id == rota_id,
            RotaEntregaParada.tenant_id == tenant_id,
        )
        .all()
    )

    # Reverter status das vendas para "pendente" (voltam para Entregas em Aberto)
    vendas_liberadas = []
    for parada in paradas:
        if parada.venda_id:
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
                vendas_liberadas.append(venda.id)

    # Deletar paradas
    for parada in paradas:
        db.delete(parada)

    # Deletar rota
    db.delete(rota)
    db.commit()

    logger.info(
        f"Rota #{rota_id} excluída. {len(vendas_liberadas)} vendas voltaram para listagem de entregas pendentes."
    )

    return {
        "message": "Rota excluída com sucesso",
        "vendas_liberadas": vendas_liberadas,
        "total_vendas": len(vendas_liberadas),
    }


# ─── CENÁRIO 4: Rastreio público (sem autenticação) ───────────────────────────
