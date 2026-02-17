"""
Endpoints para gerenciamento de lembretes de produtos recorrentes (medicamentos, rações, etc)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
import logging

from .db import get_session
from .auth import get_current_user, get_current_user_and_tenant
from .models import User, Cliente, Pet
from .produtos_models import Produto, Lembrete
from .vendas_models import Venda

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lembretes", tags=["lembretes"])


# ==================== SCHEMAS ====================

class LembreteCreate:
    """Schema para criar lembrete"""
    pass


class LembreteResponse:
    """Schema para resposta de lembrete"""
    pass


# ==================== ENDPOINTS ====================

@router.post("/criar", summary="Criar novo lembrete")
async def criar_lembrete(
    cliente_id: int,
    pet_id: int,
    produto_id: int,
    intervalo_dias: int,
    quantidade: float = 1.0,
    observacoes: str = None,
    venda_id: int = None,
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """Criar novo lembrete para um produto recorrente"""
    current_user, tenant_id = user_and_tenant
    
    try:
        import json
        
        # Validações
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
        
        pet = db.query(Pet).filter(Pet.id == pet_id, Pet.cliente_id == cliente_id).first()
        if not pet:
            raise HTTPException(status_code=404, detail="Pet não encontrado")
        
        produto = db.query(Produto).filter(Produto.id == produto_id, Produto.tenant_id == tenant_id).first()
        if not produto:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        
        # Validar compatibilidade com espécie
        if produto.especie_compativel and produto.especie_compativel.lower() != "both":
            if pet.especie.lower() != produto.especie_compativel.lower():
                raise HTTPException(
                    status_code=400,
                    detail=f"Produto incompatível: {produto.nome} é apenas para {produto.especie_compativel}s"
                )
        
        # Calcular data da próxima dose
        data_proxima_dose = datetime.utcnow() + timedelta(days=intervalo_dias)
        data_notificacao_7_dias = data_proxima_dose - timedelta(days=7)
        
        # Criar histórico inicial
        historico_inicial = [{
            "dose": 1,
            "data": datetime.utcnow().isoformat(),
            "comprou": True,
            "status": "criado"
        }]
        
        # Criar lembrete
        lembrete = Lembrete(
            tenant_id=tenant_id,
            cliente_id=cliente_id,
            pet_id=pet_id,
            produto_id=produto_id,
            venda_id=venda_id,
            data_compra=datetime.utcnow(),
            data_proxima_dose=data_proxima_dose,
            data_notificacao_7_dias=data_notificacao_7_dias,
            status='pendente',
            quantidade_recomendada=quantidade,
            preco_estimado=produto.preco_venda,
            observacoes=observacoes,
            dose_atual=1,
            dose_total=produto.numero_doses,  # Pegar do produto
            historico_doses=json.dumps(historico_inicial)
        )
        
        db.add(lembrete)
        db.commit()
        db.refresh(lembrete)
        
        return {
            "id": lembrete.id,
            "status": "criado",
            "proxima_dose": lembrete.data_proxima_dose.isoformat(),
            "notificacao_7_dias": lembrete.data_notificacao_7_dias.isoformat(),
            "dose_atual": lembrete.dose_atual,
            "dose_total": lembrete.dose_total,
            "progresso": f"{lembrete.dose_atual}/{lembrete.dose_total}" if lembrete.dose_total else "infinito"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar lembrete: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar lembrete: {str(e)}")


@router.get("/pendentes", summary="Listar lembretes pendentes")
async def listar_lembretes_pendentes(
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """Listar todos os lembretes pendentes do usuário"""
    current_user, tenant_id = user_and_tenant
    
    try:
        # Validação defensiva: se current_user não existe ou não tem id, retorna lista vazia
        if not current_user or not hasattr(current_user, 'id') or not current_user.id:
            return {"total": 0, "lembretes": []}
        
        lembretes = db.query(Lembrete).filter(
            Lembrete.tenant_id == tenant_id,
            Lembrete.status == 'pendente'
        ).order_by(Lembrete.data_proxima_dose).all()
        
        return {
            "total": len(lembretes),
            "lembretes": [
                {
                    "id": l.id,
                    "pet_nome": l.pet.nome,
                    "produto_nome": l.produto.nome,
                    "data_proxima_dose": l.data_proxima_dose.isoformat(),
                    "dias_restantes": (l.data_proxima_dose.date() - datetime.utcnow().date()).days,
                    "status": l.status,
                    "quantidade": l.quantidade_recomendada,
                    "preco_estimado": l.preco_estimado,
                    "dose_atual": l.dose_atual,
                    "dose_total": l.dose_total
                }
                for l in lembretes
            ]
        }
        
    except Exception as e:
        logger.error(f"Erro ao listar lembretes: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar lembretes: {str(e)}")


@router.get("/para-notificar", summary="Lembretes para enviar notificação")
async def listar_lembretes_para_notificar(
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """Listar lembretes que devem receber notificação (7 dias antes)"""
    current_user, tenant_id = user_and_tenant
    
    try:
        agora = datetime.utcnow()
        
        # Lembretes que atingiram a data de notificação (7 dias antes)
        lembretes = db.query(Lembrete).filter(
            Lembrete.user_id == current_user.id,
            Lembrete.status == 'pendente',
            Lembrete.notificacao_enviada == False,
            Lembrete.data_notificacao_7_dias <= agora
        ).all()
        
        return {
            "total": len(lembretes),
            "lembretes": [
                {
                    "id": l.id,
                    "cliente_id": l.cliente_id,
                    "cliente_nome": l.cliente.nome,
                    "telefone": l.cliente.telefone,
                    "email": l.cliente.email,
                    "pet_nome": l.pet.nome,
                    "produto_nome": l.produto.nome,
                    "data_proxima_dose": l.data_proxima_dose.isoformat(),
                    "metodo_notificacao": l.metodo_notificacao
                }
                for l in lembretes
            ]
        }
        
    except Exception as e:
        logger.error(f"Erro ao listar lembretes para notificar: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@router.post("/{lembrete_id}/notificar", summary="Marcar notificação como enviada")
async def marcar_notificacao_enviada(
    lembrete_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Marcar que a notificação foi enviada para este lembrete"""
    try:
        lembrete = db.query(Lembrete).filter(
            Lembrete.id == lembrete_id,
            Lembrete.tenant_id == tenant_id
        ).first()
        
        if not lembrete:
            raise HTTPException(status_code=404, detail="Lembrete não encontrado")
        
        lembrete.notificacao_enviada = True
        lembrete.data_notificacao_enviada = datetime.utcnow()
        lembrete.status = 'notificado'
        
        db.commit()
        db.refresh(lembrete)
        
        return {
            "id": lembrete.id,
            "status": "notificação enviada",
            "data_envio": lembrete.data_notificacao_enviada.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao marcar notificação: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@router.post("/{lembrete_id}/completar", summary="Marcar lembrete como completado")
async def completar_lembrete(
    lembrete_id: int,
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    current_user, tenant_id = user_and_tenant
    """Marcar lembrete como completado (cliente fez a compra/dose)"""
    try:
        lembrete = db.query(Lembrete).filter(
            Lembrete.id == lembrete_id,
            Lembrete.tenant_id == tenant_id
        ).first()
        
        if not lembrete:
            raise HTTPException(status_code=404, detail="Lembrete não encontrado")
        
        lembrete.status = 'completado'
        lembrete.data_completado = datetime.utcnow()
        
        db.commit()
        db.refresh(lembrete)
        
        return {
            "id": lembrete.id,
            "status": "completado",
            "data_conclusao": lembrete.data_completado.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao completar lembrete: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@router.post("/{lembrete_id}/renovar", summary="Renovar lembrete após compra")
async def renovar_lembrete(
    lembrete_id: int,
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """Renovar um lembrete após o cliente fazer a compra (criar novo lembrete com intervalo)"""
    current_user, tenant_id = user_and_tenant
    try:
        import json
        from datetime import datetime
        
        lembrete_anterior = db.query(Lembrete).filter(
            Lembrete.id == lembrete_id,
            Lembrete.tenant_id == tenant_id
        ).first()
        
        if not lembrete_anterior:
            raise HTTPException(status_code=404, detail="Lembrete não encontrado")
        
        produto = lembrete_anterior.produto
        
        if not produto.tem_recorrencia or not produto.intervalo_dias:
            raise HTTPException(
                status_code=400,
                detail=f"Produto {produto.nome} não tem recorrência configurada"
            )
        
        # Atualizar histórico de doses
        historico = json.loads(lembrete_anterior.historico_doses) if lembrete_anterior.historico_doses else []
        historico.append({
            "dose": lembrete_anterior.dose_atual,
            "data": datetime.utcnow().isoformat(),
            "comprou": True,
            "status": "completado"
        })
        
        # Marcar anterior como completado
        lembrete_anterior.status = 'completado'
        lembrete_anterior.data_completado = datetime.utcnow()
        lembrete_anterior.historico_doses = json.dumps(historico)
        
        # Verificar se há dose_total definida
        if lembrete_anterior.dose_total and lembrete_anterior.dose_atual >= lembrete_anterior.dose_total:
            # Última dose completada - FINALIZAR
            db.commit()
            return {
                "anterior_id": lembrete_anterior.id,
                "status": "ciclo_completado",
                "mensagem": f"✅ Ciclo de {lembrete_anterior.dose_total} doses finalizado com sucesso!",
                "dose_final": lembrete_anterior.dose_atual,
                "historico": historico
            }
        
        # Criar novo lembrete para próxima dose
        data_proxima_dose = datetime.utcnow() + timedelta(days=produto.intervalo_dias)
        data_notificacao_7_dias = data_proxima_dose - timedelta(days=7)
        
        novo_lembrete = Lembrete(
            tenant_id=tenant_id,
            cliente_id=lembrete_anterior.cliente_id,
            pet_id=lembrete_anterior.pet_id,
            produto_id=lembrete_anterior.produto_id,
            data_compra=datetime.utcnow(),
            data_proxima_dose=data_proxima_dose,
            data_notificacao_7_dias=data_notificacao_7_dias,
            status='pendente',
            quantidade_recomendada=lembrete_anterior.quantidade_recomendada,
            preco_estimado=produto.preco_venda,
            observacoes=lembrete_anterior.observacoes,
            dose_atual=lembrete_anterior.dose_atual + 1,  # Incrementar dose
            dose_total=lembrete_anterior.dose_total,
            historico_doses=json.dumps(historico)
        )
        
        db.add(novo_lembrete)
        db.commit()
        db.refresh(novo_lembrete)
        
        return {
            "anterior_id": lembrete_anterior.id,
            "novo_id": novo_lembrete.id,
            "status": "lembrete renovado",
            "proxima_dose": novo_lembrete.data_proxima_dose.isoformat(),
            "dose_atual": novo_lembrete.dose_atual,
            "dose_total": novo_lembrete.dose_total,
            "progresso": f"{novo_lembrete.dose_atual}/{novo_lembrete.dose_total}" if novo_lembrete.dose_total else f"{novo_lembrete.dose_atual} (infinito)",
            "historico": historico
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao renovar lembrete: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@router.delete("/{lembrete_id}", summary="Cancelar lembrete")
async def cancelar_lembrete(
    lembrete_id: int,
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    current_user, tenant_id = user_and_tenant
    """Cancelar um lembrete"""
    try:
        lembrete = db.query(Lembrete).filter(
            Lembrete.id == lembrete_id,
            Lembrete.tenant_id == tenant_id
        ).first()
        
        if not lembrete:
            raise HTTPException(status_code=404, detail="Lembrete não encontrado")
        
        lembrete.status = 'cancelado'
        
        db.commit()
        
        return {
            "id": lembrete.id,
            "status": "cancelado"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao cancelar lembrete: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


# ==================== ENDPOINTS DE TESTE ====================

@router.post("/{lembrete_id}/simular-data", summary="[TESTE] Simular data do lembrete")
async def simular_data_lembrete(
    lembrete_id: int,
    dias_no_futuro: int = Query(..., description="Dias para adicionar (negativo = passado)"),
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    current_user, tenant_id = user_and_tenant
    """
    [APENAS PARA TESTES]
    Altera a data_proxima_dose e data_notificacao_7_dias para simular cenários.
    
    Exemplos:
    - dias_no_futuro = -10 → simula lembrete vencido há 10 dias
    - dias_no_futuro = 5 → simula próxima dose em 5 dias
    - dias_no_futuro = 15 → simula dose distante (15 dias)
    """
    try:
        lembrete = db.query(Lembrete).filter(
            Lembrete.id == lembrete_id,
            Lembrete.tenant_id == tenant_id
        ).first()
        
        if not lembrete:
            raise HTTPException(status_code=404, detail="Lembrete não encontrado")
        
        # Calcular novas datas
        nova_data = datetime.now() + timedelta(days=dias_no_futuro)
        nova_notificacao = nova_data - timedelta(days=7)
        
        # Atualizar
        lembrete.data_proxima_dose = nova_data
        lembrete.data_notificacao_7_dias = nova_notificacao
        
        db.commit()
        
        # Determinar urgência
        dias_ate = (nova_data.date() - datetime.now().date()).days
        if dias_ate < 0:
            urgencia = "VENCIDO"
        elif dias_ate <= 7:
            urgencia = "PROXIMOS_7_DIAS"
        else:
            urgencia = "FUTURO"
        
        return {
            "id": lembrete.id,
            "data_proxima_dose": nova_data.isoformat(),
            "dias_ate_dose": dias_ate,
            "urgencia": urgencia,
            "mensagem": f"Data simulada: {nova_data.strftime('%d/%m/%Y')}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao simular data: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")
