"""Bank reconciliation and acquirer template models for finance."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.base_models import BaseTenantModel

from app.dre_plano_contas_models import DRESubcategoria


class ExtratoBancario(BaseTenantModel):
    """Extratos bancários importados (OFX, CSV, planilhas adquirentes)"""

    __tablename__ = "extratos_bancarios"
    __table_args__ = {"extend_existing": True}

    # id, tenant_id, created_at, updated_at são definidos por BaseTenantModel
    conta_bancaria_id = Column(
        Integer, ForeignKey("contas_bancarias.id", ondelete="CASCADE"), nullable=False
    )
    arquivo_nome = Column(String(255))
    data_upload = Column(DateTime, default=datetime.utcnow)
    periodo_inicio = Column(Date)
    periodo_fim = Column(Date)
    total_movimentacoes = Column(Integer, default=0)
    conciliadas = Column(Integer, default=0)
    pendentes = Column(Integer, default=0)
    status = Column(String(50))  # 'processando', 'concluido', 'revisao'

    # Relationships
    conta_bancaria = relationship("ContaBancaria")
    movimentacoes = relationship("MovimentacaoBancaria", back_populates="extrato")


class MovimentacaoBancaria(BaseTenantModel):
    """Cada linha do extrato bancário - núcleo da conciliação"""

    __tablename__ = "movimentacoes_bancarias"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    extrato_id = Column(
        Integer, ForeignKey("extratos_bancarios.id", ondelete="CASCADE")
    )
    conta_bancaria_id = Column(
        Integer, ForeignKey("contas_bancarias.id", ondelete="CASCADE"), nullable=False
    )

    # Dados do OFX
    fitid = Column(String(255))  # ID único do banco
    data_movimento = Column(DateTime)
    valor = Column(Numeric(15, 2))
    tipo = Column(String(20))  # 'CREDIT', 'DEBIT'
    memo = Column(Text)  # Descrição original

    # Classificação
    status_conciliacao = Column(
        String(50)
    )  # 'pendente', 'sugerido', 'conciliado', 'manual'
    confianca_sugestao = Column(Integer)  # 0-100%

    # Vínculos
    tipo_vinculo = Column(
        String(50)
    )  # 'fornecedor', 'transferencia', 'taxa', 'recebimento'
    fornecedor_id = Column(Integer, ForeignKey("clientes.id"))
    conta_pagar_id = Column(Integer, ForeignKey("contas_pagar.id", ondelete="SET NULL"))
    conta_receber_id = Column(
        Integer, ForeignKey("contas_receber.id", ondelete="SET NULL")
    )
    transferencia_destino_conta_id = Column(Integer, ForeignKey("contas_bancarias.id"))
    categoria_dre_id = Column(Integer, ForeignKey("dre_subcategorias.id"))
    centro_custo_id = Column(Integer)  # Futuro

    # Recorrência
    recorrente = Column(Boolean, default=False)
    periodicidade = Column(String(20))  # 'mensal', 'anual', etc
    grupo_recorrencia = Column(String(36))  # UUID para agrupar

    # Auditoria
    classificado_por = Column(Integer, ForeignKey("users.id"))
    classificado_em = Column(DateTime)
    regra_aplicada_id = Column(Integer, ForeignKey("regras_conciliacao.id"))
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    extrato = relationship("ExtratoBancario", back_populates="movimentacoes")
    conta_bancaria = relationship("ContaBancaria", foreign_keys=[conta_bancaria_id])
    conta_pagar = relationship("ContaPagar")
    conta_receber = relationship("ContaReceber")
    fornecedor = relationship("Cliente", foreign_keys=[fornecedor_id])
    transferencia_destino = relationship(
        "ContaBancaria", foreign_keys=[transferencia_destino_conta_id]
    )
    regra_aplicada = relationship("RegraConciliacao")


class RegraConciliacao(BaseTenantModel):
    """Regras de aprendizado para classificação automática"""

    __tablename__ = "regras_conciliacao"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Padrão de reconhecimento
    padrao_memo = Column(String(255))  # Ex: "%MANFRIM%"
    tipo_operacao = Column(String(50))  # 'Pagamento', 'Pix', 'Taxa'
    descricao = Column(String(255))

    # Ação automática
    fornecedor_id = Column(Integer, ForeignKey("clientes.id"))
    categoria_dre_id = Column(Integer, ForeignKey("dre_subcategorias.id"))
    centro_custo_id = Column(Integer)

    # Confiabilidade
    vezes_aplicada = Column(Integer, default=0)
    vezes_confirmada = Column(Integer, default=0)
    confianca = Column(Integer)  # (confirmada/aplicada) * 100
    prioridade = Column(Integer)

    # Status
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    fornecedor = relationship("Cliente", foreign_keys=[fornecedor_id])
    categoria_dre = relationship(DRESubcategoria, foreign_keys=[categoria_dre_id])


class ProvisaoAutomatica(BaseTenantModel):
    """Provisões geradas automaticamente para contas recorrentes"""

    __tablename__ = "provisoes_automaticas"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    regra_id = Column(Integer, ForeignKey("regras_conciliacao.id"))
    conta_pagar_id = Column(Integer, ForeignKey("contas_pagar.id"))  # Provisão criada
    data_vencimento = Column(Date)
    valor = Column(Numeric(15, 2))
    descricao = Column(Text)
    status = Column(String(50))  # 'provisionado', 'realizado', 'cancelado'
    movimentacao_real_id = Column(
        Integer, ForeignKey("movimentacoes_bancarias.id", ondelete="SET NULL")
    )

    # Auditoria
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    regra = relationship("RegraConciliacao")
    conta_pagar = relationship("ContaPagar")
    movimentacao_real = relationship("MovimentacaoBancaria")


class TemplateAdquirente(BaseTenantModel):
    """Templates para importar planilhas de diferentes adquirentes"""

    __tablename__ = "templates_adquirentes"
    __table_args__ = {"extend_existing": True}

    # id, tenant_id, created_at, updated_at são definidos por BaseTenantModel
    nome_adquirente = Column(String(100))  # 'Stone', 'Cielo', 'Rede', etc
    tipo_relatorio = Column(String(50))  # 'vendas', 'recebimentos', 'extrato'
    mapeamento = Column(Text)  # JSON com mapeamento de colunas
    palavras_chave = Column(Text)  # JSON array com palavras para detecção
    colunas_obrigatorias = Column(Text)  # JSON array
    vezes_usado = Column(Integer, default=0)
    ultima_utilizacao = Column(DateTime)
    auto_aplicar = Column(Boolean, default=True)
