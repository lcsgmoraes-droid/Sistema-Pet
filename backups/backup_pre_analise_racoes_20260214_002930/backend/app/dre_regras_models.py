"""
Modelos para Regras de Classificação Automática DRE
Sistema de aprendizado baseado em histórico de classificações manuais
"""

from sqlalchemy import Column, String, Integer, Boolean, JSON, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.base_models import BaseTenantModel
from datetime import datetime
import enum


# ============================================================
# ENUMS
# ============================================================

class TipoRegraClassificacao(enum.Enum):
    """Tipo de regra para classificação automática"""
    BENEFICIARIO = "beneficiario"  # Match por nome do fornecedor/cliente
    PALAVRA_CHAVE = "palavra_chave"  # Match por palavras na descrição
    TIPO_DOCUMENTO = "tipo_documento"  # Match por tipo (PIX, BOLETO, GUIA_FGTS, etc)
    COMBO = "combo"  # Combinação de múltiplos critérios
    VENDA_AUTOMATICA = "venda_automatica"  # Vendas PDV/Online (já vem classificado)
    NOTA_ENTRADA = "nota_entrada"  # Compras de mercadoria (não entra DRE)


class OrigemRegra(enum.Enum):
    """Como a regra foi criada"""
    SISTEMA = "sistema"  # Regra pré-definida pelo sistema
    APRENDIZADO = "aprendizado"  # Criada automaticamente por aprendizado
    USUARIO = "usuario"  # Criada manualmente pelo usuário


# ============================================================
# MODELS
# ============================================================

class RegraClassificacaoDRE(BaseTenantModel):
    """
    Regras para classificação automática de lançamentos na DRE.
    Sistema aprende padrões e sugere classificações.
    """
    __tablename__ = "regras_classificacao_dre"
    __table_args__ = {'extend_existing': True}

    # Identificação
    nome = Column(String(150), nullable=False, comment="Nome descritivo da regra")
    descricao = Column(Text, nullable=True, comment="Descrição detalhada")
    
    # Tipo e origem
    tipo_regra = Column(SQLEnum(TipoRegraClassificacao), nullable=False)
    origem = Column(SQLEnum(OrigemRegra), nullable=False, default=OrigemRegra.SISTEMA)
    
    # Critérios (JSON flexível para diferentes tipos de regras)
    criterios = Column(JSON, nullable=False, comment="""
    Exemplos:
    - BENEFICIARIO: {"beneficiario": "MÉRCIO DA SILVA", "forma_pagamento": "PIX"}
    - PALAVRA_CHAVE: {"palavras": ["frete", "entrega"], "modo": "any"}
    - TIPO_DOCUMENTO: {"tipo": "GUIA_FGTS"}
    - COMBO: {"beneficiario": "STONE", "descricao_contem": "taxa"}
    """)
    
    # Classificação DRE a aplicar
    dre_subcategoria_id = Column(Integer, ForeignKey("dre_subcategorias.id"), nullable=False)
    canal = Column(String(50), nullable=True, comment="Se aplicável, forçar canal específico")
    
    # Controle de qualidade
    prioridade = Column(Integer, default=100, comment="Maior = executa primeiro")
    confianca = Column(Integer, default=100, comment="0-100: Confiança da regra")
    aplicacoes_sucesso = Column(Integer, default=0, comment="Quantas vezes foi aplicada com sucesso")
    aplicacoes_rejeitadas = Column(Integer, default=0, comment="Quantas vezes usuário rejeitou a sugestão")
    
    # Flags
    ativo = Column(Boolean, default=True)
    sugerir_apenas = Column(Boolean, default=False, comment="True = apenas sugere, False = aplica automaticamente")
    
    # Auditoria
    criado_por_user_id = Column(Integer, nullable=True, comment="User que criou (se manual)")
    
    # Relationships
    dre_subcategoria = relationship("DRESubcategoria", foreign_keys=[dre_subcategoria_id])
    
    def calcular_precisao(self) -> float:
        """Calcula a precisão da regra baseada em sucessos/rejeições"""
        total = self.aplicacoes_sucesso + self.aplicacoes_rejeitadas
        if total == 0:
            return 1.0  # Nova regra = confiança total
        return self.aplicacoes_sucesso / total
    
    def deve_sugerir(self) -> bool:
        """Define se deve apenas sugerir ou aplicar automaticamente"""
        # Regras com baixa confiança ou poucas aplicações = apenas sugerir
        if self.confianca < 70:
            return True
        if self.aplicacoes_sucesso < 3:
            return True
        if self.calcular_precisao() < 0.8:
            return True
        return self.sugerir_apenas


class HistoricoClassificacao(BaseTenantModel):
    """
    Histórico de classificações para rastreabilidade e melhoria do aprendizado
    """
    __tablename__ = "historico_classificacao_dre"
    __table_args__ = {'extend_existing': True}

    # Referência ao lançamento
    tipo_lancamento = Column(String(20), nullable=False, comment="'pagar' ou 'receber'")
    lancamento_id = Column(Integer, nullable=False, comment="ID do contas_pagar ou contas_receber")
    
    # Classificação aplicada
    dre_subcategoria_id = Column(Integer, ForeignKey("dre_subcategorias.id"), nullable=False)
    canal = Column(String(50), nullable=True)
    
    # Como foi classificado
    forma_classificacao = Column(String(50), nullable=False, comment="""
    - 'automatico_regra': Aplicado por regra automática
    - 'automatico_sistema': Venda/Compra (lógica nativa)
    - 'sugestao_aceita': Usuário aceitou sugestão
    - 'manual': Usuário classificou manualmente
    - 'reclassificacao': Usuário alterou classificação existente
    """)
    
    regra_aplicada_id = Column(Integer, ForeignKey("regras_classificacao_dre.id"), nullable=True)
    
    # Dados do lançamento (snapshot para análise)
    descricao = Column(String(255))
    beneficiario = Column(String(255), nullable=True)
    tipo_documento = Column(String(50), nullable=True)
    valor = Column(Integer, nullable=False, comment="Valor em centavos")
    
    # Feedback do usuário
    usuario_aceitou = Column(Boolean, default=True, comment="False se usuário rejeitou/alterou")
    observacoes = Column(Text, nullable=True)
    
    # Auditoria
    classificado_por_user_id = Column(Integer, nullable=True)
    
    # Relationships
    dre_subcategoria = relationship("DRESubcategoria", foreign_keys=[dre_subcategoria_id])
    regra_aplicada = relationship("RegraClassificacaoDRE", foreign_keys=[regra_aplicada_id])
