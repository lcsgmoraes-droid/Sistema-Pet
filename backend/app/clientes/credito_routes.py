"""Rotas de credito e saneamento de campos duplicados de clientes."""

from datetime import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.audit_log import log_update
from app.db import get_session
from app.models import Cliente
from app.clientes.schemas import AjustarCreditoRequest

router = APIRouter()


def _validar_tenant_e_obter_usuario(user_and_tenant):
    current_user, tenant_id = user_and_tenant
    return current_user, tenant_id


def _obter_cliente_ou_404(db: Session, cliente_id: int, tenant_id: str):
    cliente = (
        db.query(Cliente)
        .filter(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id)
        .first()
    )
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente n??o encontrado"
        )
    return cliente

# ==================== REMOVER CAMPO DUPLICADO ====================


@router.put("/{cliente_id}/remover-campo")
def remover_campo_duplicado(
    cliente_id: int,
    campo: str,
    novo_cliente_codigo: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Remove campo duplicado (telefone/celular/CPF) de um cliente antigo
    e adiciona observaÃ§Ã£o sobre a remoÃ§Ã£o.
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Validar campo
    if campo not in ["telefone", "celular", "cpf", "cnpj"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campo invÃ¡lido. Use: telefone, celular, cpf ou cnpj",
        )

    # Buscar cliente antigo
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)

    # Validar que estÃ¡ ativo
    if not cliente.ativo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente nÃ£o encontrado"
        )

    # Guardar valor antigo para log
    valor_antigo = getattr(cliente, campo)

    # Remover o campo
    setattr(cliente, campo, None)

    # Adicionar observaÃ§Ã£o
    observacao_atual = cliente.observacoes or ""
    nova_observacao = f"[SISTEMA] {campo.capitalize()} removido (valor anterior: {valor_antigo}) - Transferido para cadastro do cliente cÃ³digo {novo_cliente_codigo}"

    if observacao_atual:
        cliente.observacoes = f"{observacao_atual}\n\n{nova_observacao}"
    else:
        cliente.observacoes = nova_observacao

    cliente.updated_at = dt.utcnow()
    db.commit()

    # Log de auditoria
    log_update(
        db,
        current_user.id,
        "cliente",
        cliente.id,
        {campo: valor_antigo},
        {campo: None, "observacoes": cliente.observacoes},
    )

    return {
        "message": f"{campo.capitalize()} removido com sucesso",
        "cliente_id": cliente.id,
        "campo_removido": campo,
        "valor_anterior": valor_antigo,
    }


# ============================================================================
# GERENCIAMENTO DE CRÃ‰DITO
# ============================================================================


@router.post("/{cliente_id}/credito/adicionar")
def adicionar_credito(
    cliente_id: int,
    dados: AjustarCreditoRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Adiciona crÃ©dito ao saldo do cliente"""
    from decimal import Decimal

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)

    if not cliente.ativo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente nÃ£o encontrado"
        )

    if dados.valor <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valor deve ser maior que zero",
        )

    from app.models import CreditoLog

    # Adicionar crédito
    credito_anterior = float(cliente.credito or 0)
    cliente.credito = Decimal(str(credito_anterior + dados.valor))
    cliente.updated_at = dt.utcnow()

    # Log estruturado de crédito
    log_credito = CreditoLog(
        tenant_id=tenant_id,
        cliente_id=cliente.id,
        tipo="adicao_manual",
        valor=Decimal(str(dados.valor)),
        saldo_anterior=Decimal(str(credito_anterior)),
        saldo_atual=Decimal(str(float(cliente.credito))),
        motivo=dados.motivo,
        usuario_nome=current_user.nome or current_user.email,
    )
    db.add(log_credito)

    db.commit()

    # Log de auditoria
    log_update(
        db,
        current_user.id,
        "cliente",
        cliente.id,
        {"credito": credito_anterior},
        {"credito": float(cliente.credito)},
    )

    return {
        "message": "CrÃ©dito adicionado com sucesso",
        "cliente_id": cliente.id,
        "cliente_nome": cliente.nome,
        "credito_anterior": credito_anterior,
        "valor_adicionado": dados.valor,
        "credito_atual": float(cliente.credito),
        "motivo": dados.motivo,
    }


@router.post("/{cliente_id}/credito/remover")
def remover_credito(
    cliente_id: int,
    dados: AjustarCreditoRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Remove crÃ©dito do saldo do cliente"""
    from decimal import Decimal

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)

    if not cliente.ativo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente nÃ£o encontrado"
        )

    if dados.valor <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valor deve ser maior que zero",
        )

    credito_atual = float(cliente.credito or 0)

    if dados.valor > credito_atual:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Valor a remover (R$ {dados.valor:.2f}) excede o crÃ©dito disponÃ­vel (R$ {credito_atual:.2f})",
        )

    from app.models import CreditoLog

    # Remover crédito
    novo_saldo = Decimal(str(credito_atual - dados.valor))
    cliente.credito = novo_saldo
    cliente.updated_at = dt.utcnow()

    # Log estruturado de crédito
    log_credito = CreditoLog(
        tenant_id=tenant_id,
        cliente_id=cliente.id,
        tipo="remocao_manual",
        valor=Decimal(str(dados.valor)),
        saldo_anterior=Decimal(str(credito_atual)),
        saldo_atual=novo_saldo,
        motivo=dados.motivo,
        usuario_nome=current_user.nome or current_user.email,
    )
    db.add(log_credito)

    db.commit()

    # Log de auditoria
    log_update(
        db,
        current_user.id,
        "cliente",
        cliente.id,
        {"credito": credito_atual},
        {"credito": float(cliente.credito)},
    )

    return {
        "message": "CrÃ©dito removido com sucesso",
        "cliente_id": cliente.id,
        "cliente_nome": cliente.nome,
        "credito_anterior": credito_atual,
        "valor_removido": dados.valor,
        "credito_atual": float(cliente.credito),
        "motivo": dados.motivo,
    }


# ============================================================================
# HISTÃ“RICO DE COMPRAS
# ============================================================================


# ============================================================================
# EXTRATO DE CRÉDITO
# ============================================================================
