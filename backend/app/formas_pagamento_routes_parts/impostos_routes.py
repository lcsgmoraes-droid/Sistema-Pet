"""Rotas de configuracao de impostos para analise de vendas."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.formas_pagamento_models import ConfiguracaoImposto

router = APIRouter()


@router.get("/impostos")
def listar_impostos(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Listar configurações de impostos.
    Inclui dinamicamente o Simples Nacional se ativo.
    """
    current_user, tenant_id = user_and_tenant

    # Buscar impostos cadastrados
    impostos = (
        db.query(ConfiguracaoImposto).filter(ConfiguracaoImposto.ativo.is_(True)).all()
    )

    resultado = [i.to_dict() for i in impostos]

    # 🔹 Injetar Simples Nacional dinamicamente
    config_fiscal = (
        db.query(EmpresaConfigFiscal)
        .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
        .first()
    )

    if (
        config_fiscal
        and config_fiscal.simples_ativo
        and config_fiscal.aliquota_simples_vigente
    ):
        resultado.append(
            {
                "codigo": "SIMPLES_NACIONAL",
                "nome": f"Simples Nacional - Anexo {config_fiscal.simples_anexo or 'I'}",
                "percentual": float(config_fiscal.aliquota_simples_vigente),
                "origem": "fiscal",
                "editavel": False,
                "ativo": True,
                "padrao": False,
                "descricao": f"Alíquota vigente do Simples Nacional (atualizado em {config_fiscal.simples_ultima_atualizacao or 'não informado'})",
            }
        )

    return resultado


@router.post("/impostos")
def criar_imposto(
    nome: str,
    percentual: float,
    padrao: bool = False,
    descricao: str = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Criar nova configuração de imposto"""

    # Se marcar como padrão, desmarcar outros
    if padrao:
        db.query(ConfiguracaoImposto).update({"padrao": False})

    novo_imposto = ConfiguracaoImposto(
        nome=nome, percentual=percentual, ativo=True, padrao=padrao, descricao=descricao
    )

    db.add(novo_imposto)
    db.commit()
    db.refresh(novo_imposto)

    return novo_imposto.to_dict()


@router.put("/impostos/{imposto_id}/padrao")
def definir_imposto_padrao(
    imposto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Definir um imposto como padrão"""

    # Desmarcar todos como padrão
    db.query(ConfiguracaoImposto).update({"padrao": False})

    # Marcar o selecionado
    imposto = (
        db.query(ConfiguracaoImposto)
        .filter(ConfiguracaoImposto.id == imposto_id)
        .first()
    )

    if not imposto:
        raise HTTPException(
            status_code=404, detail="Configuração de imposto não encontrada"
        )

    imposto.padrao = True
    imposto.ativo = True
    db.commit()

    return {"message": "Imposto definido como padrão"}
