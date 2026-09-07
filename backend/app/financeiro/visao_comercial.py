"""Preferência de leitura; não altera vendas, baixas, estoque ou regras fiscais."""

from typing import Literal

from app.empresa_config_geral_models import EmpresaConfigGeral

VisaoComercial = Literal["venda", "recebimento"]


def obter_visao_comercial(db, tenant_id) -> VisaoComercial:
    valor = (
        db.query(EmpresaConfigGeral.visao_comercial)
        .filter(EmpresaConfigGeral.tenant_id == tenant_id)
        .scalar()
    )
    return "recebimento" if valor == "recebimento" else "venda"
