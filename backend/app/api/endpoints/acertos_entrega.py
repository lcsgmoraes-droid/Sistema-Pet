"""
Endpoints de Acerto Financeiro de Entregas
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from app.db import get_session
from app.auth import get_current_user_and_tenant
from app.services.acerto_entrega_service import (
    executar_acerto_entregador,
    processar_acertos_do_dia
)
from app.models import Cliente

router = APIRouter(prefix="/acertos-entrega", tags=["Acertos de Entrega"])


@router.post("/processar-dia")
def processar_acertos_dia(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Processa todos os acertos que vencem hoje.
    
    Pode ser executado manualmente ou pelo job diário.
    Não duplica processamento.
    """
    user, tenant = user_and_tenant
    
    resultados = processar_acertos_do_dia(db, tenant.id)
    
    return {
        "data_processamento": date.today().isoformat(),
        "total_processados": len(resultados),
        "acertos": resultados
    }


@router.post("/{entregador_id}/executar")
def executar_acerto_manual(
    entregador_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Executa acerto de um entregador específico manualmente.
    
    Ignora verificação de vencimento (forçado).
    """
    user, tenant = user_and_tenant
    
    entregador = db.query(Cliente).filter(
        Cliente.id == entregador_id,
        Cliente.tenant_id == tenant.id,
        Cliente.is_entregador == True
    ).first()
    
    if not entregador:
        raise HTTPException(status_code=404, detail="Entregador não encontrado")
    
    if not entregador.tipo_acerto_entrega:
        raise HTTPException(
            status_code=400,
            detail="Entregador não possui tipo de acerto configurado"
        )
    
    # Força execução (ignora data de vencimento)
    resultado = executar_acerto_entregador(db, entregador)
    
    if not resultado:
        return {
            "mensagem": "Nenhuma rota pendente de acerto",
            "entregador": entregador.nome
        }
    
    return resultado


@router.get("/pendentes")
def listar_acertos_pendentes(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Lista entregadores com acerto vencendo hoje.
    """
    user, tenant = user_and_tenant
    hoje = date.today()
    
    from app.services.acerto_entrega_service import acerto_vence_hoje
    from sqlalchemy import and_
    
    entregadores = db.query(Cliente).filter(
        and_(
            Cliente.tenant_id == tenant.id,
            Cliente.is_entregador == True,
            Cliente.entregador_ativo == True,
            Cliente.tipo_acerto_entrega.isnot(None)
        )
    ).all()
    
    pendentes = []
    
    for entregador in entregadores:
        if acerto_vence_hoje(entregador, hoje):
            pendentes.append({
                "id": entregador.id,
                "nome": entregador.nome,
                "tipo_cadastro": entregador.tipo_cadastro,
                "tipo_acerto": entregador.tipo_acerto_entrega,
                "ultimo_acerto": entregador.data_ultimo_acerto.isoformat() if entregador.data_ultimo_acerto else None
            })
    
    return {
        "data": hoje.isoformat(),
        "total": len(pendentes),
        "entregadores": pendentes
    }


@router.get("/{entregador_id}/historico")
def historico_acerto(
    entregador_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Mostra histórico de acertos de um entregador.
    """
    user, tenant = user_and_tenant
    
    entregador = db.query(Cliente).filter(
        Cliente.id == entregador_id,
        Cliente.tenant_id == tenant.id,
        Cliente.is_entregador == True
    ).first()
    
    if not entregador:
        raise HTTPException(status_code=404, detail="Entregador não encontrado")
    
    from app.models import ContasPagar
    
    contas = db.query(ContasPagar).filter(
        ContasPagar.tenant_id == tenant.id,
        ContasPagar.fornecedor_id == entregador_id,
        ContasPagar.tipo_documento == "ACERTO_ENTREGA"
    ).order_by(ContasPagar.data_emissao.desc()).all()
    
    return {
        "entregador": {
            "id": entregador.id,
            "nome": entregador.nome,
            "tipo_cadastro": entregador.tipo_cadastro,
            "controla_rh": entregador.controla_rh,
            "gera_cp_custo": entregador.gera_conta_pagar_custo_entrega,
            "tipo_acerto": entregador.tipo_acerto_entrega,
            "ultimo_acerto": entregador.data_ultimo_acerto.isoformat() if entregador.data_ultimo_acerto else None
        },
        "contas_pagar": [
            {
                "id": cp.id,
                "valor": float(cp.valor),
                "descricao": cp.descricao,
                "data_emissao": cp.data_emissao.isoformat(),
                "data_vencimento": cp.data_vencimento.isoformat(),
                "status": cp.status
            }
            for cp in contas
        ]
    }
