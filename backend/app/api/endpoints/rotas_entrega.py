from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import secrets

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.rotas_entrega_models import RotaEntrega, RotaEntregaParada
from app.models import Cliente, ConfiguracaoEntrega
from app.vendas_models import Venda
from app.schemas.rota_entrega import (
    RotaEntregaCreate,
    RotaEntregaUpdate,
    RotaEntregaResponse,
)
from app.services.custo_entrega_service import calcular_custo_entrega
from app.services.custo_moto_service import calcular_custo_moto
from app.services.google_maps_service import calcular_distancia_km, calcular_rota_otimizada
from app.services.notificacao_entrega_service import notificar_inicio_rota, notificar_proximo_cliente
from app.models_configuracao_custo_moto import ConfiguracaoCustoMoto
from app.utils.logger import logger

router = APIRouter(prefix="/rotas-entrega", tags=["Entregas - Rotas"])
_rotas_schema_checked = False


class RegistrarRecebimentoPayload(BaseModel):
    forma_pagamento: str = Field(..., description="pix | cartao_debito | cartao_credito")
    numero_parcelas: int = Field(1, ge=1, le=12)



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
    db.execute(text("ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS observacoes TEXT"))
    db.execute(text("ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS km_entrega NUMERIC(10,2)"))
    db.execute(text("ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS lat_entrega NUMERIC(10,6)"))
    db.execute(text("ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS lon_entrega NUMERIC(10,6)"))
    db.commit()
    _rotas_schema_checked = True


@router.get("/", response_model=List[RotaEntregaResponse])
def listar_rotas(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Lista rotas de entrega do tenant.

    OTIMIZAÇÃO: Não otimiza automaticamente para economizar chamadas à API.
    Use POST /rotas-entrega/otimizar para otimizar manualmente.
    """
    from sqlalchemy.orm import joinedload
    from app.vendas_models import Venda
    from app.models import Cliente

    user, tenant_id = user_and_tenant
    ensure_rotas_entrega_schema(db)

    query = db.query(RotaEntrega).options(
        joinedload(RotaEntrega.entregador),
        joinedload(RotaEntrega.paradas).joinedload(RotaEntregaParada.venda).joinedload(Venda.cliente)
    ).filter(RotaEntrega.tenant_id == tenant_id)

    if status:
        query = query.filter(RotaEntrega.status == status)
    else:
        # Se não especificou status, mostra apenas rotas ativas (exclui concluídas)
        query = query.filter(RotaEntrega.status.in_(['pendente', 'em_rota', 'em_andamento']))

    # Ordenar: rotas com paradas otimizadas primeiro, depois por data
    rotas = query.order_by(RotaEntrega.created_at.asc()).all()

    # Se a rota tem paradas, ordenar internamente pelas paradas.ordem
    # E incluir dados do cliente para exibição
    for rota in rotas:
        if rota.paradas:
            rota.paradas = sorted(rota.paradas, key=lambda p: p.ordem)
            # Adicionar informações do cliente em cada parada
            for parada in rota.paradas:
                if parada.venda and parada.venda.cliente:
                    parada.cliente_nome = parada.venda.cliente.nome
                    parada.cliente_telefone = parada.venda.cliente.telefone
                    parada.cliente_celular = parada.venda.cliente.celular

    return rotas


@router.get("/vendas-pendentes/listar")
def listar_vendas_pendentes_entrega(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Lista vendas com entrega pendente (sem rota criada ainda).

    CRITÉRIO: tem_entrega = true E status_entrega = 'pendente' ou NULL
    Exclui vendas que já estão em rota, entregues ou canceladas.

    Retorna em ordem:
    1. Vendas com ordem_entrega_otimizada (já otimizadas)
    2. Vendas novas sem ordem (cronológico)

    Economiza chamadas à API: só otimiza quando usuário clicar no botão.
    """
    user, tenant_id = user_and_tenant

    # Buscar vendas com entrega pendente
    # CRITÉRIO: tem_entrega = true E status_entrega = 'pendente' ou NULL
    # Exclui: 'em_rota', 'entregue', 'cancelada'
    vendas = db.query(Venda).filter(
        Venda.tenant_id == tenant_id,
        Venda.tem_entrega == True,
        # Aceita apenas vendas pendentes (ainda não entraram em rota)
        (Venda.status_entrega == 'pendente') | (Venda.status_entrega == None)
    ).order_by(
        # Primeiro: vendas com ordem otimizada
        Venda.ordem_entrega_otimizada.asc().nullslast(),
        # Depois: vendas novas por data
        Venda.created_at.asc()
    ).all()

    return [{
        "id": v.id,
        "numero_venda": v.numero_venda,
        "cliente_id": v.cliente_id,
        "cliente_nome": v.cliente.nome if v.cliente else "Cliente não cadastrado",
        "endereco_entrega": v.endereco_entrega,
        "taxa_entrega": float(v.taxa_entrega) if v.taxa_entrega else 0,
        "distancia_km": float(v.distancia_km) if v.distancia_km else None,
        "ordem_otimizada": v.ordem_entrega_otimizada,
        "data_venda": v.data_venda.isoformat() if v.data_venda else None,
        "total": float(v.total) if v.total else 0,
        "entregador_id": v.entregador_id,
        "entregador_nome": v.entregador.nome if v.entregador else None,
    } for v in vendas]


@router.post("/{rota_id}/paradas/{parada_id}/registrar-recebimento")
def registrar_recebimento_entregador(
    rota_id: int,
    parada_id: int,
    payload: RegistrarRecebimentoPayload,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Pré-integração de recebimento no app do entregador.

    IMPORTANTE:
    - NÃO baixa financeiro ainda.
    - Apenas registra intenção de cobrança para ficar pronto para integração Stone/operadora.
    """
    _, tenant_id = user_and_tenant

    forma = (payload.forma_pagamento or "").strip().lower()
    formas_validas = {"pix", "cartao_debito", "cartao_credito"}
    if forma not in formas_validas:
        raise HTTPException(status_code=400, detail="Forma de pagamento inválida")

    if forma != "cartao_credito" and payload.numero_parcelas != 1:
        raise HTTPException(status_code=400, detail="Parcelas só são permitidas para cartão de crédito")

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

    venda = db.query(Venda).filter(Venda.id == parada.venda_id, Venda.tenant_id == tenant_id).first()
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


@router.post("/vendas-pendentes/otimizar")
def otimizar_vendas_pendentes(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Otimiza ordem de entrega das vendas pendentes usando Google Maps.
    Salva a ordem no banco para evitar chamadas futuras à API.

    Esta é a ÚNICA vez que chama o Google Maps - depois só lê do banco!
    """
    from app.services.google_maps_service import calcular_rota_otimizada

    user, tenant_id = user_and_tenant

    # Buscar configuração para ponto inicial
    config = db.query(ConfiguracaoEntrega).filter(
        ConfiguracaoEntrega.tenant_id == tenant_id
    ).first()

    if not config or not config.logradouro:
        raise HTTPException(
            status_code=400,
            detail="Configure o endereço da loja em Configurações > Entregas primeiro"
        )

    # Montar endereço completo
    origem = ", ".join(filter(None, [
        config.logradouro,
        config.numero,
        config.bairro,
        config.cidade,
        config.estado,
        config.cep
    ]))

    logger.info(f"📍 Ponto de origem: {origem}")

    # Buscar TODAS as vendas pendentes (incluindo as já otimizadas - RE-otimizar)
    # CRITÉRIO: tem_entrega = true E status_entrega NÃO é 'entregue' ou 'cancelada'
    vendas = db.query(Venda).filter(
        Venda.tenant_id == tenant_id,
        Venda.tem_entrega == True,
        ~Venda.status_entrega.in_(["entregue", "cancelada"]),
        Venda.endereco_entrega.isnot(None)
    ).order_by(Venda.created_at.asc()).all()

    if not vendas:
        raise HTTPException(status_code=404, detail="Nenhuma venda pendente para otimizar")

    logger.info(f"📦 Encontradas {len(vendas)} vendas para otimizar")

    if len(vendas) == 1:
        # Se só tem 1, não precisa otimizar
        vendas[0].ordem_entrega_otimizada = 1
        db.commit()
        logger.info("✅ Apenas 1 venda, ordem definida como 1")
        return {"message": "Apenas 1 venda, ordem definida como 1", "total_otimizado": 1}

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
                logger.info(f"   Posição {posicao}: Venda {venda.numero_venda} (índice {indice_original})")

        db.commit()

        logger.info(f"✅ Ordem salva! {len(ordem_indices)} vendas otimizadas")

        # Retornar ordem legível
        ordem_vendas = [vendas[i].numero_venda for i in ordem_indices]
        logger.info(f"📋 Ordem final: {ordem_vendas}")

        return {
            "message": f"Rotas otimizadas com sucesso! Ordem salva no banco.",
            "total_otimizado": len(ordem_indices),
            "ordem": ordem_vendas
        }

    except Exception as e:
        logger.error(f"❌ Erro ao otimizar rotas: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao otimizar rotas: {str(e)}")


@router.get("/{rota_id}", response_model=RotaEntregaResponse)
def obter_rota(
    rota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Obtém detalhes de uma rota específica.
    """
    user, tenant_id = user_and_tenant
    ensure_rotas_entrega_schema(db)

    rota = db.query(RotaEntrega).filter(
        RotaEntrega.id == rota_id,
        RotaEntrega.tenant_id == tenant_id
    ).first()

    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    rota.entregador = db.query(Cliente).filter(Cliente.id == rota.entregador_id).first()

    return rota


@router.put("/{rota_id}", response_model=RotaEntregaResponse)
def atualizar_rota(
    rota_id: int,
    payload: RotaEntregaUpdate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Atualiza dados de uma rota (status, observações, etc).
    """
    user, tenant_id = user_and_tenant
    ensure_rotas_entrega_schema(db)

    rota = db.query(RotaEntrega).filter(
        RotaEntrega.id == rota_id,
        RotaEntrega.tenant_id == tenant_id
    ).first()

    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    if rota.status == "concluida":
        raise HTTPException(status_code=400, detail="Rota concluída não pode ser alterada")

    # Atualizar campos fornecidos
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rota, field, value)

    db.commit()
    db.refresh(rota)

    rota.entregador = db.query(Cliente).filter(Cliente.id == rota.entregador_id).first()

    return rota


@router.post("/", response_model=RotaEntregaResponse)
def criar_rota(
    payload: RotaEntregaCreate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
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
    user, tenant_id = user_and_tenant

    # Validar entregador
    entregador = db.query(Cliente).filter(
        Cliente.id == payload.entregador_id,
        Cliente.tenant_id == tenant_id,
        Cliente.is_entregador == True,
        Cliente.entregador_ativo == True
    ).first()

    if not entregador:
        raise HTTPException(status_code=400, detail="Entregador inválido")

    # Buscar configuração de entrega para obter ponto inicial
    config_entrega = db.query(ConfiguracaoEntrega).filter(
        ConfiguracaoEntrega.tenant_id == tenant_id
    ).first()

    # ETAPA 9.3: Modo rota múltipla (várias vendas)
    if payload.vendas_ids and len(payload.vendas_ids) > 0:
        # Buscar vendas
        vendas = db.query(Venda).filter(
            Venda.id.in_(payload.vendas_ids),
            Venda.tenant_id == tenant_id
        ).all()

        if len(vendas) != len(payload.vendas_ids):
            raise HTTPException(status_code=404, detail="Uma ou mais vendas não encontradas")

        # Validar que todas têm endereço
        if not all(v.endereco_entrega for v in vendas):
            raise HTTPException(status_code=400, detail="Todas as vendas devem ter endereço de entrega")

        # Criar rota principal (sem venda_id específica, pois são várias)
        rota = RotaEntrega(
            tenant_id=tenant_id,
            entregador_id=payload.entregador_id,
            moto_da_loja=payload.moto_da_loja,
            status="pendente",
            created_by=user.id,
        )
        rota.numero = f"ROTA-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        rota.token_rastreio = secrets.token_urlsafe(32)

        # Somar taxas de entrega de todas as vendas
        taxa_total = sum(v.taxa_entrega for v in vendas if v.taxa_entrega)

        rota.taxa_entrega_cliente = taxa_total if taxa_total > 0 else None
        # valor_repasse_entregador será calculado posteriormente (não existe na venda)

        # Definir pontos inicial e final
        # Montar endereço completo do ponto inicial a partir da configuração
        if config_entrega:
            ponto_inicial = payload.ponto_inicial_rota or (
                f"{config_entrega.logradouro or ''}"
                f"{', ' + config_entrega.numero if config_entrega.numero else ''}"
                f"{' - ' + config_entrega.complemento if config_entrega.complemento else ''}"
                f"{' - ' + config_entrega.bairro if config_entrega.bairro else ''}"
                f"{' - ' + config_entrega.cidade if config_entrega.cidade else ''}"
                f"/{config_entrega.estado if config_entrega.estado else ''}"
            ).strip()
        else:
            ponto_inicial = payload.ponto_inicial_rota

        rota.ponto_inicial_rota = ponto_inicial

        # Ponto final: por padrão é o mesmo do inicial (retorna à origem)
        if payload.retorna_origem is False:
            # Não retorna: ponto final é a última entrega
            rota.ponto_final_rota = payload.ponto_final_rota or vendas[-1].endereco_entrega
            rota.retorna_origem = False
        else:
            # Retorna à origem (padrão)
            rota.ponto_final_rota = ponto_inicial
            rota.retorna_origem = True

        db.add(rota)
        db.flush()  # Obter ID da rota

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
            venda.status_entrega = "em_rota"

        db.commit()
        db.refresh(rota)

        return rota

    # Modo tradicional: rota com 1 venda apenas
    # Buscar venda para obter endereço de destino
    venda = db.query(Venda).filter(
        Venda.id == payload.venda_id,
        Venda.tenant_id == tenant_id
    ).first()

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
        entregador_id=payload.entregador_id,
        endereco_destino=payload.endereco_destino,
        distancia_prevista=distancia_prevista,  # Calculado automaticamente
        custo_previsto=payload.custo_previsto,
        moto_da_loja=payload.moto_da_loja,
        status="pendente",
        created_by=user.id,
        # ETAPA 7.1: Snapshot dos valores de repasse (se fornecidos)
        taxa_entrega_cliente=payload.taxa_entrega_cliente,
        valor_repasse_entregador=payload.valor_repasse_entregador,
    )

    # Número da rota (simples por enquanto)
    rota.numero = f"ROTA-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    rota.token_rastreio = secrets.token_urlsafe(32)

    db.add(rota)

    # Marcar venda como "em_rota"
    venda.status_entrega = "em_rota"

    db.commit()
    db.refresh(rota)

    return rota


@router.post("/{rota_id}/fechar", response_model=RotaEntregaResponse)
def fechar_rota(
    rota_id: int,
    payload: RotaEntregaUpdate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Fecha uma rota de entrega, calculando o custo real.

    Se km_inicial e km_final forem informados, calcula distancia_real automaticamente.
    """
    user, tenant_id = user_and_tenant

    rota = db.query(RotaEntrega).filter(
        RotaEntrega.id == rota_id,
        RotaEntrega.tenant_id == tenant_id
    ).first()

    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    if rota.status == "concluida":
        raise HTTPException(status_code=400, detail="Rota já concluída")

    entregador = db.query(Cliente).filter(
        Cliente.id == rota.entregador_id,
        Cliente.tenant_id == tenant_id
    ).first()

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
                logger.warning(f"KM final ({payload.km_final}) menor que inicial ({rota.km_inicial})")

    # Se não calculou automaticamente, usar valor informado
    if payload.distancia_real is not None and rota.distancia_real is None:
        rota.distancia_real = payload.distancia_real

    rota.tentativas = payload.tentativas or 1
    rota.observacoes = payload.observacoes
    rota.status = "concluida"
    rota.data_conclusao = datetime.now()

    # Calcular custo de entrega (entregador)
    rota.custo_real = calcular_custo_entrega(
        entregador=entregador,
        km=payload.distancia_real or Decimal("0"),
        tentativas=rota.tentativas,
        moto_da_loja=rota.moto_da_loja,
    )

    # ETAPA 8 + 11.1: Se moto da loja, calcular e armazenar custo da moto separadamente
    rota.custo_moto = Decimal("0")
    if rota.moto_da_loja and payload.distancia_real:
        config_moto = db.query(ConfiguracaoCustoMoto).filter(
            ConfiguracaoCustoMoto.tenant_id == tenant_id
        ).first()
        if config_moto:
            custo_moto = calcular_custo_moto(
                config=config_moto,
                km=payload.distancia_real
            )
            rota.custo_moto = custo_moto
            rota.custo_real += custo_moto

    db.commit()
    db.refresh(rota)

    # 🔔 FINANCEIRO (STUB)
    # - Se terceirizado → gerar contas a pagar
    # - Registrar custo no DRE (incluindo custo da moto)
    # (entrará na ETAPA 5)

    return rota


@router.get("/{rota_id}/paradas", response_model=List)
def listar_paradas_rota(
    rota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    ETAPA 9.3 - Lista paradas de uma rota na ordem otimizada
    """
    user, tenant_id = user_and_tenant

    # Validar que rota existe e pertence ao tenant
    rota = db.query(RotaEntrega).filter(
        RotaEntrega.id == rota_id,
        RotaEntrega.tenant_id == tenant_id
    ).first()

    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    # Buscar paradas ordenadas
    paradas = db.query(RotaEntregaParada).filter(
        RotaEntregaParada.rota_id == rota_id,
        RotaEntregaParada.tenant_id == tenant_id
    ).order_by(RotaEntregaParada.ordem).all()

    return paradas


@router.put("/{rota_id}/paradas/reordenar")
def reordenar_paradas(
    rota_id: int,
    nova_ordem: List[int],  # Lista de IDs das paradas na nova ordem
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
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
    user, tenant_id = user_and_tenant

    # Validar que rota existe e pertence ao tenant
    rota = db.query(RotaEntrega).filter(
        RotaEntrega.id == rota_id,
        RotaEntrega.tenant_id == tenant_id
    ).first()

    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    if rota.status == "concluida":
        raise HTTPException(status_code=400, detail="Não é possível reordenar rota concluída")

    # Buscar todas as paradas
    paradas = db.query(RotaEntregaParada).filter(
        RotaEntregaParada.rota_id == rota_id,
        RotaEntregaParada.tenant_id == tenant_id
    ).all()

    paradas_dict = {p.id: p for p in paradas}

    # Validar que todos os IDs fornecidos existem
    if set(nova_ordem) != set(paradas_dict.keys()):
        raise HTTPException(
            status_code=400,
            detail="Lista de IDs não corresponde às paradas da rota"
        )

    # Atualizar ordem
    for idx, parada_id in enumerate(nova_ordem):
        paradas_dict[parada_id].ordem = idx + 1

    db.commit()

    return {"message": "Ordem das paradas atualizada com sucesso"}


@router.post("/{rota_id}/iniciar", response_model=RotaEntregaResponse)
def iniciar_rota(
    rota_id: int,
    km_inicial: Optional[float] = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    ETAPA 9.4 - Inicia navegação da rota

    - Marca status como em_rota
    - Registra data_inicio
    - Registra KM inicial da moto (opcional)
    - Dispara eventos de mensagens
    """
    user, tenant_id = user_and_tenant

    # Validar rota
    rota = db.query(RotaEntrega).filter(
        RotaEntrega.id == rota_id,
        RotaEntrega.tenant_id == tenant_id
    ).first()

    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    if rota.status != "pendente":
        raise HTTPException(
            status_code=400,
            detail=f"Rota não pode ser iniciada. Status atual: {rota.status}"
        )

    # Verificar se tem paradas
    paradas_count = db.query(RotaEntregaParada).filter(
        RotaEntregaParada.rota_id == rota_id
    ).count()

    if paradas_count == 0:
        raise HTTPException(
            status_code=400,
            detail="Rota não possui paradas cadastradas"
        )

    # Iniciar rota
    rota.status = "em_rota"
    rota.data_inicio = datetime.now()

    # Registrar KM inicial (opcional)
    if km_inicial is not None:
        rota.km_inicial = Decimal(str(km_inicial))
        logger.info(f"KM inicial da rota: {km_inicial}")

    db.commit()
    db.refresh(rota)

    # ETAPA 9.4: Disparar mensagens automáticas para todos os clientes
    try:
        mensagens_enviadas = notificar_inicio_rota(db, rota_id, tenant_id)
        if mensagens_enviadas > 0:
            db.commit()  # Commit das mensagens
    except Exception as e:
        # Log do erro mas não falha a operação
        logger.info(f"Erro ao enviar notificações de início: {e}")

    return rota


@router.post("/{rota_id}/reverter-inicio", response_model=RotaEntregaResponse)
def reverter_inicio_rota(
    rota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Reverte o início de uma rota, voltando para status pendente.
    Só permite se nenhuma entrega foi realizada ainda.
    Útil quando inicia a rota mas precisa adicionar mais entregas antes de sair.
    """
    user, tenant_id = user_and_tenant

    # Validar rota
    rota = db.query(RotaEntrega).filter(
        RotaEntrega.id == rota_id,
        RotaEntrega.tenant_id == tenant_id
    ).first()

    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    if rota.status != "em_rota":
        raise HTTPException(
            status_code=400,
            detail=f"Rota não pode ser revertida. Status atual: {rota.status}"
        )

    # Verificar se alguma parada já foi entregue
    paradas_entregues = db.query(RotaEntregaParada).filter(
        RotaEntregaParada.rota_id == rota_id,
        RotaEntregaParada.status == "entregue"
    ).count()

    if paradas_entregues > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível reverter. {paradas_entregues} entrega(s) já foi(foram) realizada(s)."
        )

    # Reverter status
    rota.status = "pendente"
    rota.data_inicio = None

    db.commit()
    db.refresh(rota)

    logger.info(f"Rota #{rota_id} revertida para pendente")

    return rota


@router.post("/{rota_id}/atualizar-localizacao")
def atualizar_localizacao_rota(
    rota_id: int,
    lat: float,
    lon: float,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Atualiza a localização atual do entregador para rastreio ao vivo.
    """
    _, tenant_id = user_and_tenant
    ensure_rotas_entrega_schema(db)

    rota = db.query(RotaEntrega).filter(
        RotaEntrega.id == rota_id,
        RotaEntrega.tenant_id == tenant_id,
    ).first()

    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    if rota.status not in ("em_rota", "em_andamento"):
        raise HTTPException(status_code=400, detail="Rota não está em andamento")

    db.execute(
        text(
            """
            UPDATE rotas_entrega
            SET lat_atual = :lat,
                lon_atual = :lon,
                localizacao_atualizada_em = :agora
            WHERE id = :rid AND tenant_id = :tenant
            """
        ),
        {
            "lat": lat,
            "lon": lon,
            "agora": datetime.now(),
            "rid": rota_id,
            "tenant": tenant_id,
        },
    )
    db.commit()

    return {"ok": True}


@router.post("/{rota_id}/paradas/{parada_id}/marcar-entregue")
def marcar_parada_entregue(
    rota_id: int,
    parada_id: int,
    tentativa: bool = False,
    km_entrega: Optional[float] = None,
    lat_entrega: Optional[float] = None,
    lon_entrega: Optional[float] = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    ETAPA 9.4 - Marca parada como entregue ou tentativa

    Args:
        tentativa: True se cliente ausente (não entregue)
        km_entrega: KM da moto no momento da entrega (opcional)
        lat_entrega: Latitude GPS no momento da entrega (opcional)
        lon_entrega: Longitude GPS no momento da entrega (opcional)
    """
    user, tenant_id = user_and_tenant

    # Validar rota
    rota = db.query(RotaEntrega).filter(
        RotaEntrega.id == rota_id,
        RotaEntrega.tenant_id == tenant_id
    ).first()

    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    if rota.status != "em_rota":
        raise HTTPException(status_code=400, detail="Rota não está em andamento")

    # Validar parada
    parada = db.query(RotaEntregaParada).filter(
        RotaEntregaParada.id == parada_id,
        RotaEntregaParada.rota_id == rota_id,
        RotaEntregaParada.tenant_id == tenant_id
    ).first()

    if not parada:
        raise HTTPException(status_code=404, detail="Parada não encontrada")

    if parada.status == "entregue":
        raise HTTPException(status_code=400, detail="Parada já marcada como entregue")

    # Marcar status
    if tentativa:
        parada.status = "tentativa"
        rota.tentativas += 1
        mensagem = "Tentativa registrada. Cliente ausente."
    else:
        parada.status = "entregue"
        parada.data_entrega = datetime.now()

        # Registrar KM da entrega (opcional)
        if km_entrega is not None:
            parada.km_entrega = Decimal(str(km_entrega))
            logger.info(f"KM da entrega {parada_id}: {km_entrega}")

        # Registrar coordenadas GPS da entrega (opcional)
        if lat_entrega is not None and lon_entrega is not None:
            try:
                db.execute(
                    text("UPDATE rotas_entrega_paradas SET lat_entrega = :lat, lon_entrega = :lon WHERE id = :pid"),
                    {"lat": lat_entrega, "lon": lon_entrega, "pid": parada_id}
                )
                logger.info(f"GPS da entrega {parada_id}: lat={lat_entrega}, lon={lon_entrega}")
            except Exception as e:
                logger.warning(f"Não foi possível salvar GPS da entrega: {e}")

        mensagem = "Parada marcada como entregue!"

        # ETAPA 9.4: Disparar mensagem para próximo cliente
        try:
            notificou = notificar_proximo_cliente(db, rota_id, parada.ordem, tenant_id)
            if notificou:
                mensagem += " Próximo cliente foi notificado."
        except Exception as e:
            # Log do erro mas não falha a operação
            logger.info(f"Erro ao notificar próximo cliente: {e}")

    db.commit()

    # Verificar se todas as paradas foram entregues
    paradas_pendentes = db.query(RotaEntregaParada).filter(
        RotaEntregaParada.rota_id == rota_id,
        RotaEntregaParada.status == "pendente"
    ).count()

    if paradas_pendentes == 0:
        mensagem += " Todas as paradas foram concluídas. Feche a rota."

    return {"message": mensagem, "paradas_pendentes": paradas_pendentes}


@router.put("/{rota_id}/paradas/{parada_id}/observacao")
def adicionar_observacao_parada(
    rota_id: int,
    parada_id: int,
    observacao: str,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Adiciona ou atualiza observação sobre uma parada/entrega.
    Usado para aprendizado do sistema (ex: "Sempre entregar no vizinho").
    """
    user, tenant_id = user_and_tenant

    # Validar parada
    parada = db.query(RotaEntregaParada).filter(
        RotaEntregaParada.id == parada_id,
        RotaEntregaParada.rota_id == rota_id,
        RotaEntregaParada.tenant_id == tenant_id
    ).first()

    if not parada:
        raise HTTPException(status_code=404, detail="Parada não encontrada")

    parada.observacoes = observacao
    db.commit()

    return {"message": "Observação salva com sucesso", "observacoes": observacao}


@router.post("/{rota_id}/paradas/{parada_id}/nao-entregue")
def marcar_parada_nao_entregue(
    rota_id: int,
    parada_id: int,
    motivo: str = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Marca parada como não entregue e reverte venda para status 'aberto'.
    Usada quando entrega não pode ser realizada (cliente ausente, cartão recusado, etc).
    """
    user, tenant_id = user_and_tenant

    # Validar rota
    rota = db.query(RotaEntrega).filter(
        RotaEntrega.id == rota_id,
        RotaEntrega.tenant_id == tenant_id
    ).first()

    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    # Validar parada
    parada = db.query(RotaEntregaParada).filter(
        RotaEntregaParada.id == parada_id,
        RotaEntregaParada.rota_id == rota_id,
        RotaEntregaParada.tenant_id == tenant_id
    ).first()

    if not parada:
        raise HTTPException(status_code=404, detail="Parada não encontrada")

    # Salvar motivo como observação
    if motivo:
        obs_existente = parada.observacoes or ""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        parada.observacoes = f"{obs_existente}\n[{timestamp}] Não entregue: {motivo}".strip()

    # Reverter venda para status pendente (para aparecer na lista de entregas em aberto)
    venda = db.query(Venda).filter(Venda.id == parada.venda_id).first()
    if venda:
        venda.status_entrega = "pendente"

    # Remover parada da rota
    db.delete(parada)
    db.commit()

    logger.info(f"Parada {parada_id} marcada como não entregue. Venda {parada.venda_id} voltou para entregas em aberto.")

    return {
        "message": "Entrega marcada como não realizada. Venda voltou para entregas em aberto.",
        "venda_id": parada.venda_id
    }


@router.delete("/{rota_id}")
def excluir_rota(
    rota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
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
    rota = db.query(RotaEntrega).filter(
        RotaEntrega.id == rota_id,
        RotaEntrega.tenant_id == tenant_id
    ).first()

    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    # Validar se pode excluir
    if rota.status in ["concluida", "cancelada"]:
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível excluir rota com status '{rota.status}'"
        )

    # Buscar todas as paradas da rota
    paradas = db.query(RotaEntregaParada).filter(
        RotaEntregaParada.rota_id == rota_id,
        RotaEntregaParada.tenant_id == tenant_id
    ).all()

    # Reverter status das vendas para "aberto"
    vendas_liberadas = []
    for parada in paradas:
        if parada.venda_id:
            venda = db.query(Venda).filter(Venda.id == parada.venda_id).first()
            if venda:
                venda.status_entrega = "aberto"
                vendas_liberadas.append(venda.id)

    # Deletar paradas
    for parada in paradas:
        db.delete(parada)

    # Deletar rota
    db.delete(rota)
    db.commit()

    logger.info(f"Rota #{rota_id} excluída. {len(vendas_liberadas)} vendas voltaram para listagem de entregas pendentes.")

    return {
        "message": "Rota excluída com sucesso",
        "vendas_liberadas": vendas_liberadas,
        "total_vendas": len(vendas_liberadas)
    }


# ─── CENÁRIO 2+: Otimizar apenas as vendas selecionadas ───────────────────────

from pydantic import BaseModel as _BaseModel

class OtimizarSelecionadasPayload(_BaseModel):
    venda_ids: List[int]


@router.post("/vendas-pendentes/otimizar-selecionadas")
def otimizar_vendas_selecionadas(
    payload: OtimizarSelecionadasPayload,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Otimiza ordem de entrega APENAS das vendas selecionadas.
    Não afeta as demais vendas pendentes.
    """
    from app.services.google_maps_service import calcular_rota_otimizada

    user, tenant_id = user_and_tenant

    config = db.query(ConfiguracaoEntrega).filter(
        ConfiguracaoEntrega.tenant_id == tenant_id
    ).first()

    if not config or not config.logradouro:
        raise HTTPException(
            status_code=400,
            detail="Configure o endereço da loja em Configurações > Entregas primeiro"
        )

    origem = ", ".join(filter(None, [
        config.logradouro, config.numero, config.bairro,
        config.cidade, config.estado, config.cep
    ]))

    vendas = db.query(Venda).filter(
        Venda.id.in_(payload.venda_ids),
        Venda.tenant_id == tenant_id,
        Venda.tem_entrega == True,
        ~Venda.status_entrega.in_(["entregue", "cancelada"]),
        Venda.endereco_entrega.isnot(None)
    ).all()

    if not vendas:
        raise HTTPException(status_code=404, detail="Nenhuma venda encontrada para otimizar")

    if len(vendas) == 1:
        vendas[0].ordem_entrega_otimizada = 1
        db.commit()
        return {"message": "Apenas 1 venda, ordem definida como 1", "total_otimizado": 1}

    destinos = [v.endereco_entrega for v in vendas]
    ordem_indices, legs = calcular_rota_otimizada(origem, destinos)

    for posicao, indice_original in enumerate(ordem_indices, start=1):
        if indice_original < len(vendas):
            vendas[indice_original].ordem_entrega_otimizada = posicao

    db.commit()

    return {
        "message": f"{len(ordem_indices)} entregas selecionadas otimizadas com sucesso!",
        "total_otimizado": len(ordem_indices),
    }


# ─── CENÁRIO 4: Rastreio público (sem autenticação) ───────────────────────────

@router.get("/rastreio/{token}")
def rastreio_publico(
    token: str,
    db: Session = Depends(get_session),
):
    """
    Endpoint público para rastreamento de rota por token.
    Retorna última posição GPS e status das paradas (sem dados sensíveis).
    """
    rota = db.query(RotaEntrega).filter(
        RotaEntrega.token_rastreio == token
    ).first()

    if not rota:
        raise HTTPException(status_code=404, detail="Rastreio não encontrado ou link inválido")

    # Buscar paradas com última posição GPS conhecida
    paradas = db.query(RotaEntregaParada).filter(
        RotaEntregaParada.rota_id == rota.id
    ).order_by(RotaEntregaParada.ordem).all()

    # Última posição GPS (última parada entregue com GPS)
    ultima_posicao = None
    for p in reversed(paradas):
        lat = None
        lon = None
        try:
            result = db.execute(
                text("SELECT lat_entrega, lon_entrega FROM rotas_entrega_paradas WHERE id = :pid"),
                {"pid": p.id}
            ).fetchone()
            if result:
                lat, lon = result
        except Exception:
            pass
        if lat is not None and lon is not None:
            ultima_posicao = {"lat": float(lat), "lon": float(lon)}
            break

    entregues = sum(1 for p in paradas if p.status == "entregue")
    total = len(paradas)

    return {
        "rota_numero": rota.numero,
        "status": rota.status,
        "entregador_nome": rota.entregador.nome if rota.entregador else "Entregador",
        "total_paradas": total,
        "entregues": entregues,
        "pendentes": total - entregues,
        "ultima_posicao_gps": ultima_posicao,
        "paradas": [
            {
                "ordem": p.ordem,
                "endereco": p.endereco,
                "status": p.status,
                "data_entrega": p.data_entrega.isoformat() if p.data_entrega else None,
            }
            for p in paradas
        ],
    }
