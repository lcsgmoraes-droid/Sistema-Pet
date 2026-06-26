"""
Models para Conciliação de Cartões - Fase 1

Implementa estrutura completa para conciliação de cartões com validação em cascata.

Baseado em:
- docs/ARQUITETURA_CONCILIACAO_CARTOES.md
- docs/ROADMAP_CONCILIACAO_CARTOES.md
- docs/AJUSTES_ARQUITETURA_APLICADOS.md

Models criados:
1. EmpresaParametros - Parâmetros configuráveis (tolerâncias, taxas estimadas)
2. AdquirenteTemplate - Templates para parsear CSVs de operadoras
3. ArquivoEvidencia - Metadados dos arquivos importados
4. ConciliacaoImportacao - Dados brutos importados (OFX, CSV)
5. ConciliacaoLote - Lotes de pagamento/transferências
6. ConciliacaoValidacao - Resultado da validação em cascata
7. ConciliacaoLog - Log completo de auditoria
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Date,
    Text,
    ForeignKey,
    Numeric,
)
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

from .db import Base
from .base_models import BaseTenantModel, TenantScoped


# ==============================================================================
# EMPRESA_PARAMETROS - Configurações por empresa (Ajuste #2)
# ==============================================================================


class ConciliacaoRecebimento(BaseTenantModel):
    """
    Tabela para salvar dados dos recebimentos importados da planilha Stone.

    Usado na Aba 2 (Conciliação de Recebimentos) para validação em cascata:
    - Recebimentos Detalhados
    - Recibo de Lote
    - OFX

    E na Aba 3 (Amarração) para vincular recebimentos às vendas.
    """

    __tablename__ = "conciliacao_recebimentos"
    __table_args__ = {"extend_existing": True}

    # Sobrescrever id para usar autoincrement padrão (não Identity)
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # Dados da planilha Stone
    nsu = Column(String(100), nullable=False, index=True, comment="NSU da transação")
    adquirente = Column(
        String(100), nullable=True, index=True, comment="Operadora do recebimento"
    )
    data_recebimento = Column(
        Date, nullable=False, index=True, comment="Data que dinheiro entrou"
    )
    valor = Column(Numeric(15, 2), nullable=False, comment="Valor do recebimento")
    parcela_numero = Column(
        Integer, nullable=True, comment="Número da parcela (1, 2, 3, etc)"
    )
    total_parcelas = Column(
        Integer, nullable=True, comment="Total de parcelas da venda"
    )

    # Tipo de recebimento
    tipo_recebimento = Column(
        String(30),
        nullable=False,
        default="parcela_individual",
        comment="antecipacao (todas de vez) | parcela_individual (1/3, 2/3, etc)",
    )

    # Lote (agrupamento Stone)
    lote_id = Column(String(100), nullable=True, index=True, comment="ID do lote Stone")
    lote_valor = Column(Numeric(15, 2), nullable=True, comment="Valor total do lote")

    # Validação (Aba 2)
    validado = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Se passou validação cascata (Aba 2)",
    )
    validado_em = Column(DateTime, nullable=True, comment="Quando foi validado")
    validacao_id = Column(
        Integer,
        nullable=True,
        comment="FK desabilitado - tabela conciliacao_validacoes não existe",
    )  # was: ForeignKey('conciliacao_validacoes.id')

    # Amarração (Aba 3)
    amarrado = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Se foi amarrado a uma venda (Aba 3)",
    )
    amarrado_em = Column(DateTime, nullable=True, comment="Quando foi amarrado")
    venda_id = Column(
        Integer,
        ForeignKey("vendas.id"),
        nullable=True,
        index=True,
        comment="FK para venda vinculada",
    )

    # Auditoria - Sobrescrever nomes para não conflitar com BaseTenantModel
    criado_em = Column("criado_em", DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = Column(
        "atualizado_em", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Desabilitar created_at/updated_at do BaseTenantModel
    created_at = None
    updated_at = None

    # Relationships
    # validacao = relationship("ConciliacaoValidacao", foreign_keys=[validacao_id])  # Disabled - FK validacao_id não existe

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": str(self.tenant_id),
            "nsu": self.nsu,
            "adquirente": self.adquirente,
            "data_recebimento": self.data_recebimento.isoformat()
            if self.data_recebimento
            else None,
            "valor": float(self.valor) if self.valor else 0,
            "parcela_numero": self.parcela_numero,
            "total_parcelas": self.total_parcelas,
            "tipo_recebimento": self.tipo_recebimento,
            "lote_id": self.lote_id,
            "lote_valor": float(self.lote_valor) if self.lote_valor else 0,
            "validado": self.validado,
            "amarrado": self.amarrado,
            "venda_id": self.venda_id,
        }


class ConciliacaoMetrica(TenantScoped, Base):
    """
    Tabela para armazenar métricas diárias de amarração automática.

    Usado para monitorar a saúde do sistema:
    - % de amarração automática
    - Se cair abaixo de 90% = alerta CRÍTICO (problema na operação)

    Permite gráficos históricos e alertas proativos.

    NOTA: Mantém esquema próprio (criado_em em vez de created_at) por isso não
    herda BaseTenantModel; adota o mixin TenantScoped para entrar no filtro global
    de tenant (tenant_id vem do mixin, schema idêntico).
    """

    __tablename__ = "conciliacao_metricas"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # Data da métrica
    data_referencia = Column(
        Date, nullable=False, index=True, comment="Data dos recebimentos processados"
    )

    # Quantidades
    total_recebimentos = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total de recebimentos validados (Aba 2)",
    )
    recebimentos_amarrados = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Recebimentos amarrados automaticamente",
    )
    recebimentos_orfaos = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Recebimentos SEM venda correspondente",
    )

    # Valores
    valor_total_recebimentos = Column(
        Numeric(15, 2),
        nullable=False,
        default=0,
        comment="Valor total dos recebimentos",
    )
    valor_amarrado = Column(
        Numeric(15, 2),
        nullable=False,
        default=0,
        comment="Valor amarrado automaticamente",
    )
    valor_orfao = Column(
        Numeric(15, 2), nullable=False, default=0, comment="Valor órfão (sem venda)"
    )

    # KPI principal
    taxa_amarracao_automatica = Column(
        Numeric(5, 2),
        nullable=False,
        default=0,
        index=True,
        comment="% de amarração automática (98% = saudável, < 90% = CRÍTICO)",
    )

    # Alertas
    alerta_saude = Column(
        String(20),
        nullable=False,
        default="OK",
        index=True,
        comment="OK (>= 90%) | CRÍTICO (< 90%)",
    )

    # Parcelas liquidadas (transparência)
    parcelas_liquidadas = Column(
        Integer, nullable=False, default=0, comment="Quantas parcelas foram baixadas"
    )
    valor_total_liquidado = Column(
        Numeric(15, 2), nullable=False, default=0, comment="Valor total liquidado"
    )

    # Auditoria
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    criado_por_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, comment="Quem processou Aba 3"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": str(self.tenant_id),
            "data_referencia": self.data_referencia.isoformat()
            if self.data_referencia
            else None,
            "quantidades": {
                "total_recebimentos": self.total_recebimentos,
                "amarrados": self.recebimentos_amarrados,
                "orfaos": self.recebimentos_orfaos,
            },
            "valores": {
                "total": float(self.valor_total_recebimentos)
                if self.valor_total_recebimentos
                else 0,
                "amarrado": float(self.valor_amarrado) if self.valor_amarrado else 0,
                "orfao": float(self.valor_orfao) if self.valor_orfao else 0,
            },
            "kpi": {
                "taxa_amarracao": float(self.taxa_amarracao_automatica)
                if self.taxa_amarracao_automatica
                else 0,
                "alerta_saude": self.alerta_saude,
            },
            "liquidacao": {
                "parcelas": self.parcelas_liquidadas,
                "valor_total": float(self.valor_total_liquidado)
                if self.valor_total_liquidado
                else 0,
            },
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }


class HistoricoConciliacao(BaseTenantModel):
    """
    Registro histórico de conciliações realizadas.

    Objetivo:
    - Rastrear quais datas/operadoras já foram conciliadas
    - Evitar reprocessamento duplicado
    - Auditoria completa do processo
    - Histórico consultável

    Cada registro = 1 conciliação completa (3 abas)
    """

    __tablename__ = "historico_conciliacao"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # Identificação única da conciliação
    data_referencia = Column(
        Date, nullable=False, index=True, comment="Data conciliada (ex: 10/02/2026)"
    )
    operadora = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Operadora: Stone, PagSeguro, Rede, Cielo, etc.",
    )

    # Status do processo
    status = Column(
        String(50),
        nullable=False,
        default="em_andamento",
        comment="em_andamento | concluida | reprocessada | cancelada",
    )

    # Abas concluídas
    aba1_concluida = Column(Boolean, default=False, comment="Conciliação de Vendas")
    aba2_concluida = Column(Boolean, default=False, comment="Validação de Recebimentos")
    aba3_concluida = Column(Boolean, default=False, comment="Amarração Automática")

    aba1_concluida_em = Column(DateTime, nullable=True)
    aba2_concluida_em = Column(DateTime, nullable=True)
    aba3_concluida_em = Column(DateTime, nullable=True)

    # Metadados da conciliação
    arquivos_processados = Column(
        JSONB, comment="Lista de arquivos: [{nome, tipo, tamanho, hash}]"
    )

    totais = Column(
        JSONB, comment="Valores totais: {vendas, recebimentos, amarrado, divergencias}"
    )

    divergencias_encontradas = Column(Integer, default=0)
    divergencias_aceitas = Column(Boolean, default=False)

    # Resultado da amarração (Aba 3)
    parcelas_amarradas = Column(Integer, default=0)
    parcelas_orfas = Column(Integer, default=0)
    taxa_amarracao = Column(Numeric(5, 2), comment="% de sucesso da amarração")

    # Auditoria
    usuario_responsavel = Column(String(200), comment="Usuário que realizou")
    observacoes = Column(Text, nullable=True)

    # Concluída em (quando todas as 3 abas terminarem)
    concluida_em = Column(DateTime, nullable=True)

    # Índice composto para evitar duplicação
    __table_args__ = ({"extend_existing": True},)

    def __repr__(self):
        return f"<HistoricoConciliacao(data={self.data_referencia}, operadora={self.operadora}, status={self.status})>"

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": str(self.tenant_id),
            "data_referencia": self.data_referencia.isoformat()
            if self.data_referencia
            else None,
            "operadora": self.operadora,
            "status": self.status,
            "abas": {
                "aba1": {
                    "concluida": self.aba1_concluida,
                    "concluida_em": self.aba1_concluida_em.isoformat()
                    if self.aba1_concluida_em
                    else None,
                },
                "aba2": {
                    "concluida": self.aba2_concluida,
                    "concluida_em": self.aba2_concluida_em.isoformat()
                    if self.aba2_concluida_em
                    else None,
                },
                "aba3": {
                    "concluida": self.aba3_concluida,
                    "concluida_em": self.aba3_concluida_em.isoformat()
                    if self.aba3_concluida_em
                    else None,
                },
            },
            "arquivos": self.arquivos_processados or [],
            "totais": self.totais or {},
            "divergencias": {
                "encontradas": self.divergencias_encontradas,
                "aceitas": self.divergencias_aceitas,
            },
            "amarracao": {
                "parcelas_amarradas": self.parcelas_amarradas,
                "parcelas_orfas": self.parcelas_orfas,
                "taxa": float(self.taxa_amarracao) if self.taxa_amarracao else 0,
            },
            "usuario_responsavel": self.usuario_responsavel,
            "observacoes": self.observacoes,
            "concluida_em": self.concluida_em.isoformat()
            if self.concluida_em
            else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
