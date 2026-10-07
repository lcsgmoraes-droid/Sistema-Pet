"""Validação da preferência de vendedor nas vendas do PDV."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.empresa_config_geral_models import EmpresaConfigGeral


def exigir_vendedor_pdv(
    db: Session, tenant_id, vendedor_funcionario_id, *, canal="loja_fisica"
):
    if canal not in (None, "loja_fisica") or vendedor_funcionario_id is not None:
        return
    config = (
        db.query(EmpresaConfigGeral)
        .filter(EmpresaConfigGeral.tenant_id == tenant_id)
        .first()
    )
    if config and config.vendedor_obrigatorio_pdv:
        raise HTTPException(
            status_code=400, detail="Selecione o vendedor antes de salvar a venda."
        )
