from sqlalchemy.orm import Session
from app.fiscal_estado_padrao_models import FiscalEstadoPadrao
from app.empresa_config_fiscal_models import EmpresaConfigFiscal


def criar_config_fiscal_empresa(
    db: Session,
    tenant_id: int,
    uf: str,
    regime_tributario: str,
    cnae_principal: str | None = None
):
    """
    Cria a configuração fiscal da empresa herdando do estado.
    Se já existir, retorna a existente.
    """

    existente = (
        db.query(EmpresaConfigFiscal)
        .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
        .first()
    )
    if existente:
        return existente

    estado = (
        db.query(FiscalEstadoPadrao)
        .filter(FiscalEstadoPadrao.uf == uf)
        .first()
    )
    if not estado:
        raise ValueError(f"Configuração fiscal padrão não encontrada para UF {uf}")

    config = EmpresaConfigFiscal(
        tenant_id=tenant_id,
        fiscal_estado_padrao_id=estado.id,
        uf=estado.uf,

        regime_tributario=regime_tributario,
        cnae_principal=cnae_principal,
        contribuinte_icms=True,

        icms_aliquota_interna=estado.icms_aliquota_interna,
        icms_aliquota_interestadual=estado.icms_aliquota_interestadual,
        aplica_difal=estado.aplica_difal,

        cfop_venda_interna=estado.cfop_venda_interna,
        cfop_venda_interestadual=estado.cfop_venda_interestadual,
        cfop_compra=estado.cfop_compra,

        herdado_do_estado=True
    )

    db.add(config)
    db.commit()
    db.refresh(config)
    return config
