from sqlalchemy.orm import Session
from app.fiscal_estado_padrao_models import FiscalEstadoPadrao
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.models import Tenant


def obter_ou_criar_config_fiscal_empresa_padrao(
    db: Session,
    tenant_id,
    commit: bool = False,
):
    """
    Retorna a configuracao fiscal da empresa ou cria um padrao minimo.
    Evita que tenants novos quebrem o PDV antes de passarem pela tela fiscal.
    """
    existente = (
        db.query(EmpresaConfigFiscal)
        .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
        .first()
    )
    if existente:
        return existente

    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    uf = (getattr(tenant, "uf", None) or "SP").strip().upper()[:2] or "SP"

    config = EmpresaConfigFiscal(
        tenant_id=tenant_id,
        uf=uf,
        regime_tributario="Simples Nacional",
        contribuinte_icms=True,
        icms_aliquota_interna=18.0,
        icms_aliquota_interestadual=12.0,
        aplica_difal=True,
        cfop_venda_interna="5102",
        cfop_venda_interestadual="6102",
        cfop_compra="1102",
        pis_cst_padrao=None,
        pis_aliquota=0,
        cofins_cst_padrao=None,
        cofins_aliquota=0,
        herdado_do_estado=True,
    )
    db.add(config)
    db.flush()

    if commit:
        db.commit()
        db.refresh(config)

    return config


def criar_config_fiscal_empresa(
    db: Session,
    tenant_id: int,
    uf: str,
    regime_tributario: str,
    cnae_principal: str | None = None,
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

    estado = db.query(FiscalEstadoPadrao).filter(FiscalEstadoPadrao.uf == uf).first()
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
        herdado_do_estado=True,
    )

    db.add(config)
    db.commit()
    db.refresh(config)
    return config
