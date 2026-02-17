from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, Identity, Text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from .db import Base
from .base_models import BaseTenantModel


class EmpresaConfigFiscal(BaseTenantModel):
    """
    Configuração fiscal da empresa (multi-tenant)
    Define valores padrão de tributação que serão herdados pelos produtos
    """
    __tablename__ = "empresa_config_fiscal"

    # ID já vem do BaseTenantModel com Identity
    # tenant_id já vem do BaseTenantModel como UUID
    # created_at e updated_at já vêm do BaseTenantModel

    # Temporariamente sem FK até fiscal_estado_padrao ser recriado
    fiscal_estado_padrao_id = Column(
        Integer,
        nullable=True  # Pode ser None se personalizado
    )

    uf = Column(String(2), nullable=False)

    regime_tributario = Column(String(50), nullable=False)
    cnae_principal = Column(String(10))
    contribuinte_icms = Column(Boolean, nullable=False)

    icms_aliquota_interna = Column(Numeric(5, 2), nullable=False)
    icms_aliquota_interestadual = Column(Numeric(5, 2), nullable=False)
    aplica_difal = Column(Boolean, nullable=False)

    cfop_venda_interna = Column(String(4), nullable=False)
    cfop_venda_interestadual = Column(String(4), nullable=False)
    cfop_compra = Column(String(4), nullable=False)

    pis_cst_padrao = Column(String(3))
    pis_aliquota = Column(Numeric(5, 2))
    cofins_cst_padrao = Column(String(3))
    cofins_aliquota = Column(Numeric(5, 2))

    municipio_iss = Column(String(100))
    iss_aliquota = Column(Numeric(5, 2))
    iss_retido = Column(Boolean, default=False)

    herdado_do_estado = Column(Boolean, nullable=False, default=True)
    
    # ============================
    # SIMPLES NACIONAL
    # ============================
    simples_ativo = Column(Boolean, default=False)
    simples_anexo = Column(String(5), default='I')  # I, II, III, IV ou V
    aliquota_simples_vigente = Column(Numeric(5, 2), default=0)  # Alíquota atual utilizada
    aliquota_simples_sugerida = Column(Numeric(5, 2), default=0)  # Sugestão baseada no histórico
    
    # ============================
    # PROVISÕES TRABALHISTAS (NOVO)
    # ============================
    folha_valor_base_mensal = Column(Numeric(10, 2), default=0)  # Valor total da folha mensal
    inss_patronal_percentual = Column(Numeric(5, 2), default=20)  # % INSS patronal (padrão 20%)
    fgts_percentual = Column(Numeric(5, 2), default=8)  # % FGTS (padrão 8%)
    
    # ============================
    # CNAE - Descrições e Secundários
    # ============================
    cnae_descricao = Column(Text)  # Descrição do CNAE principal
    cnaes_secundarios = Column(JSONB)  # Lista de CNAEs secundários [{codigo, descricao}]

    # created_at e updated_at já vêm do BaseTenantModel
