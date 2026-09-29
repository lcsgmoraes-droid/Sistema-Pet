from sqlalchemy.orm import Session
from app.fiscal_estado_padrao_models import FiscalEstadoPadrao
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.models import Tenant
from app.fiscal_state_rules import default_company_fiscal_values, normalize_uf


def obter_ou_criar_config_fiscal_empresa_padrao(
    db: Session,
    tenant_id,
    commit: bool = False,
):
    """
    Retorna a configuracao fiscal da empresa ou cria um padrao minimo.
    Evita que tenants novos quebrem o PDV antes de passarem pela tela fiscal.
    """
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    uf = normalize_uf(getattr(tenant, "uf", None))
    existente = (
        db.query(EmpresaConfigFiscal)
        .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
        .first()
    )
    if existente:
        if uf and normalize_uf(existente.uf) != uf:
            existente.uf = uf
            existente.configuracao_confirmada = False
            existente.configuracao_confirmada_em = None
            if existente.herdado_do_estado:
                referencia = default_company_fiscal_values(uf)
                existente.icms_aliquota_interna = referencia["icms_aliquota_interna"]
            if "simples" in str(existente.regime_tributario or "").casefold():
                existente.aplica_difal = False
            db.flush()
            if commit:
                db.commit()
                db.refresh(existente)
        return existente

    config = EmpresaConfigFiscal(
        tenant_id=tenant_id,
        **default_company_fiscal_values(uf),
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
        aplica_difal=(
            False
            if "simples" in str(regime_tributario or "").casefold()
            else estado.aplica_difal
        ),
        cfop_venda_interna=estado.cfop_venda_interna,
        cfop_venda_interestadual=estado.cfop_venda_interestadual,
        cfop_compra=estado.cfop_compra,
        herdado_do_estado=True,
    )

    db.add(config)
    db.commit()
    db.refresh(config)
    return config
