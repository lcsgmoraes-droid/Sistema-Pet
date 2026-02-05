from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

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


@router.get("/", response_model=List[RotaEntregaResponse])
def listar_rotas(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Lista rotas de entrega do tenant.
    """
    user, tenant_id = user_and_tenant
    
    query = db.query(RotaEntrega).filter(RotaEntrega.tenant_id == tenant_id)
    
    if status:
        query = query.filter(RotaEntrega.status == status)
    
    rotas = query.order_by(RotaEntrega.created_at.desc()).all()
    
    # Carregar entregador para cada rota
    for rota in rotas:
        rota.entregador = db.query(Cliente).filter(Cliente.id == rota.entregador_id).first()
    
    return rotas


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

    db.add(rota)
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
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    ETAPA 9.4 - Inicia navegação da rota
    
    - Marca status como em_rota
    - Registra data_inicio
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


@router.post("/{rota_id}/paradas/{parada_id}/marcar-entregue")
def marcar_parada_entregue(
    rota_id: int,
    parada_id: int,
    tentativa: bool = False,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    ETAPA 9.4 - Marca parada como entregue ou tentativa
    
    Args:
        tentativa: True se cliente ausente (não entregue)
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
