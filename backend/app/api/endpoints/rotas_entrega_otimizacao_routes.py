from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import ConfiguracaoEntrega
from app.utils.logger import logger
from app.vendas_models import Venda

router = APIRouter()


@router.post("/vendas-pendentes/otimizar")
def otimizar_vendas_pendentes(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Otimiza ordem de entrega das vendas pendentes usando Google Maps.
    Salva a ordem no banco para evitar chamadas futuras à API.

    Esta é a ÚNICA vez que chama o Google Maps - depois só lê do banco!
    """
    from app.services.google_maps_service import calcular_rota_otimizada

    user, tenant_id = user_and_tenant

    # Buscar configuração para ponto inicial
    config = (
        db.query(ConfiguracaoEntrega)
        .filter(ConfiguracaoEntrega.tenant_id == tenant_id)
        .first()
    )

    if not config or not config.logradouro:
        raise HTTPException(
            status_code=400,
            detail="Configure o endereço da loja em Configurações > Entregas primeiro",
        )

    # Montar endereço completo
    origem = ", ".join(
        filter(
            None,
            [
                config.logradouro,
                config.numero,
                config.bairro,
                config.cidade,
                config.estado,
                config.cep,
            ],
        )
    )

    logger.info(f"📍 Ponto de origem: {origem}")

    # Buscar TODAS as vendas pendentes (incluindo as já otimizadas - RE-otimizar)
    # CRITÉRIO: tem_entrega = true E status_entrega NÃO é 'entregue' ou 'cancelada'
    vendas = (
        db.query(Venda)
        .filter(
            Venda.tenant_id == tenant_id,
            Venda.tem_entrega.is_(True),
            ~Venda.status_entrega.in_(["entregue", "cancelada"]),
            Venda.endereco_entrega.isnot(None),
        )
        .order_by(Venda.created_at.asc())
        .all()
    )

    if not vendas:
        raise HTTPException(
            status_code=404, detail="Nenhuma venda pendente para otimizar"
        )

    logger.info(f"📦 Encontradas {len(vendas)} vendas para otimizar")

    if len(vendas) == 1:
        # Se só tem 1, não precisa otimizar
        vendas[0].ordem_entrega_otimizada = 1
        db.commit()
        logger.info("✅ Apenas 1 venda, ordem definida como 1")
        return {
            "message": "Apenas 1 venda, ordem definida como 1",
            "total_otimizado": 1,
        }

    try:
        # Extrair endereços
        destinos = [v.endereco_entrega for v in vendas]

        logger.info(f"🗺️ Chamando Google Maps para otimizar {len(destinos)} entregas...")
        logger.info(f"📍 Origem: {origem}")
        for i, dest in enumerate(destinos, 1):
            logger.info(f"   {i}. {dest}")

        # Chamar Google Maps UMA VEZ
        ordem_indices, legs = calcular_rota_otimizada(origem, destinos)

        logger.info(f"🎯 Google Maps retornou ordem: {ordem_indices}")

        # Salvar ordem otimizada no banco
        for posicao, indice_original in enumerate(ordem_indices, start=1):
            if indice_original < len(vendas):
                venda = vendas[indice_original]
                venda.ordem_entrega_otimizada = posicao
                logger.info(
                    f"   Posição {posicao}: Venda {venda.numero_venda} (índice {indice_original})"
                )

        db.commit()

        logger.info(f"✅ Ordem salva! {len(ordem_indices)} vendas otimizadas")

        # Retornar ordem legível
        ordem_vendas = [vendas[i].numero_venda for i in ordem_indices]
        logger.info(f"📋 Ordem final: {ordem_vendas}")

        return {
            "message": "Rotas otimizadas com sucesso! Ordem salva no banco.",
            "total_otimizado": len(ordem_indices),
            "ordem": ordem_vendas,
        }

    except Exception as e:
        logger.error(f"❌ Erro ao otimizar rotas: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao otimizar rotas: {str(e)}")


class OtimizarSelecionadasRequest(BaseModel):
    venda_ids: List[int]


@router.post("/vendas-pendentes/otimizar-selecionadas")
def otimizar_vendas_selecionadas(
    payload: OtimizarSelecionadasRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Otimiza a ordem de entrega apenas das vendas selecionadas (por IDs).
    """
    from app.services.google_maps_service import calcular_rota_otimizada

    user, tenant_id = user_and_tenant

    if not payload.venda_ids:
        raise HTTPException(status_code=400, detail="Nenhuma venda selecionada")

    config = (
        db.query(ConfiguracaoEntrega)
        .filter(ConfiguracaoEntrega.tenant_id == tenant_id)
        .first()
    )

    if not config or not config.logradouro:
        raise HTTPException(
            status_code=400,
            detail="Configure o endereço da loja em Configurações > Entregas primeiro",
        )

    origem = ", ".join(
        filter(
            None,
            [
                config.logradouro,
                config.numero,
                config.bairro,
                config.cidade,
                config.estado,
                config.cep,
            ],
        )
    )

    vendas = (
        db.query(Venda)
        .filter(
            Venda.tenant_id == tenant_id,
            Venda.id.in_(payload.venda_ids),
            Venda.tem_entrega.is_(True),
            Venda.endereco_entrega.isnot(None),
        )
        .order_by(Venda.created_at.asc())
        .all()
    )

    if not vendas:
        raise HTTPException(
            status_code=404, detail="Nenhuma venda encontrada com os IDs fornecidos"
        )

    if len(vendas) == 1:
        vendas[0].ordem_entrega_otimizada = 1
        db.commit()
        return {
            "message": "Apenas 1 venda, ordem definida como 1",
            "total_otimizado": 1,
        }

    try:
        destinos = [v.endereco_entrega for v in vendas]
        ordem_indices, legs = calcular_rota_otimizada(origem, destinos)

        for posicao, indice_original in enumerate(ordem_indices, start=1):
            if indice_original < len(vendas):
                vendas[indice_original].ordem_entrega_otimizada = posicao

        db.commit()

        ordem_vendas = [vendas[i].numero_venda for i in ordem_indices]
        return {
            "message": f"Rotas otimizadas com sucesso! {len(ordem_indices)} entregas reordenadas.",
            "total_otimizado": len(ordem_indices),
            "ordem": ordem_vendas,
        }

    except Exception as e:
        logger.error(f"❌ Erro ao otimizar rotas selecionadas: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao otimizar rotas: {str(e)}")
