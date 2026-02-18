from app.base_models import BaseTenantModel
"""
Modelos para ABA 7 - Importação de Extrato Bancário com IA
Referência: ROADMAP_IA_AMBICOES.md (linhas 1-250)

NOTA: CategoriaFinanceira já existe em financeiro_models.py e será estendida via migração
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db import Base


class PadraoCategoriacaoIA(BaseTenantModel):
    """
    Padrões aprendidos pela IA para categorizar transações automaticamente.
    A cada validação humana, o sistema aprende e melhora a confiança.
    """
    __tablename__ = 'padroes_categorizacao_ia'
    
    # Identificação
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # O que identificar
    tipo_transacao = Column(String(50))  # 'pix', 'boleto', 'ted', 'cartao', 'dinheiro'
    beneficiario_pattern = Column(String(500))  # Texto ou regex (ex: "Mercio%" ou "ENERGISA%")
    cnpj_cpf = Column(String(20), nullable=True)  # Se conseguir extrair
    
    # Valores e tolerância
    valor_minimo = Column(Numeric(10, 2), nullable=True)
    valor_maximo = Column(Numeric(10, 2), nullable=True)
    valor_medio = Column(Numeric(10, 2), nullable=True)
    tolerancia_percentual = Column(Float, default=10.0)  # ±10%
    
    # Frequência (para detectar recorrência)
    frequencia = Column(String(50), nullable=True)  # 'mensal', 'semanal', 'diaria', 'anual'
    dia_mes_tipico = Column(Integer, nullable=True)  # Dia do mês (ex: 10 para aluguel)
    
    # Categoria
    categoria_financeira_id = Column(Integer, ForeignKey('categorias_financeiras.id'), nullable=True)
    categoria_nome = Column(String(100))  # Cache para facilitar buscas
    tipo_lancamento = Column(String(20))  # 'receita' ou 'despesa'
    
    # Estatísticas de aprendizado
    total_aplicacoes = Column(Integer, default=0)
    total_acertos = Column(Integer, default=0)
    total_erros = Column(Integer, default=0)
    total_editos = Column(Integer, default=0)
    confianca_atual = Column(Float, default=0.5)  # 0.0 a 1.0
    
    # Histórico
    primeira_confirmacao = Column(DateTime, nullable=True)
    ultima_confirmacao = Column(DateTime, nullable=True)
    ultima_atualizacao = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Status
    ativo = Column(Boolean, default=True)
    criado_manualmente = Column(Boolean, default=False)  # User criou vs IA criou
    
    # Relacionamentos
    # usuario = relationship("User", back_populates="padroes_categorizacao")  # Disabled - User.padroes_categorizacao comentado
    lancamentos_aplicados = relationship("LancamentoImportado", back_populates="padrao_sugerido")


class LancamentoImportado(BaseTenantModel):
    """
    Transações importadas de extratos bancários.
    Aguardam validação humana antes de virarem lançamentos definitivos.
    """
    __tablename__ = 'lancamentos_importados'
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Dados da transação original
    data_transacao = Column(DateTime, nullable=False)
    descricao_original = Column(Text)  # Texto exato do extrato
    valor = Column(Numeric(10, 2), nullable=False)
    tipo = Column(String(20))  # 'entrada' ou 'saida'
    
    # Dados extraídos via NLP
    tipo_transacao = Column(String(50), nullable=True)  # PIX, TED, boleto
    cnpj_cpf_extraido = Column(String(20), nullable=True)
    beneficiario_extraido = Column(String(200), nullable=True)
    codigo_barras = Column(String(100), nullable=True)
    
    # Categorização pela IA
    categoria_financeira_id = Column(Integer, ForeignKey('categorias_financeiras.id'), nullable=True)
    padrao_sugerido_id = Column(Integer, ForeignKey('padroes_categorizacao_ia.id'), nullable=True)
    confianca_ia = Column(Float, default=0.0)  # 0.0 a 1.0
    categorias_alternativas = Column(JSON, nullable=True)  # TOP 3 sugestões: [{id, nome, confianca}]
    
    # Validação humana
    status_validacao = Column(String(20), default='pendente')  # 'pendente', 'aprovado', 'editado', 'rejeitado'
    confirmado_usuario = Column(Boolean, default=False)
    categoria_usuario_id = Column(Integer, ForeignKey('categorias_financeiras.id'), nullable=True)
    data_validacao = Column(DateTime, nullable=True)
    
    # Linkagem automática
    conta_pagar_id = Column(Integer, ForeignKey('contas_pagar.id'), nullable=True)
    conta_receber_id = Column(Integer, ForeignKey('contas_receber.id', ondelete='SET NULL'), nullable=True)
    linkagem_automatica = Column(Boolean, default=False)
    confianca_linkagem = Column(Float, nullable=True)
    
    # Lançamento criado
    lancamento_manual_id = Column(Integer, ForeignKey('lancamentos_manuais.id'), nullable=True)
    processado = Column(Boolean, default=False)
    data_processamento = Column(DateTime, nullable=True)
    
    # Metadados
    arquivo_origem = Column(String(500), nullable=True)  # Nome do arquivo importado
    linha_arquivo = Column(Integer, nullable=True)  # Linha no arquivo
    hash_transacao = Column(String(64), nullable=True, index=True)  # Para evitar duplicatas
    
    criado_em = Column(DateTime, default=datetime.now)
    atualizado_em = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relacionamentos
    # usuario = relationship("User", back_populates="lancamentos_importados")  # Disabled - User.lancamentos_importados comentado
    padrao_sugerido = relationship("PadraoCategoriacaoIA", back_populates="lancamentos_aplicados")
    categoria_sugerida = relationship("CategoriaFinanceira", foreign_keys=[categoria_financeira_id])
    categoria_validada = relationship("CategoriaFinanceira", foreign_keys=[categoria_usuario_id])


class ArquivoExtratoImportado(BaseTenantModel):
    """
    Histórico de arquivos de extrato importados.
    """
    __tablename__ = 'arquivos_extrato_importados'
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Arquivo
    nome_arquivo = Column(String(500), nullable=False)
    tipo_arquivo = Column(String(20))  # 'excel', 'csv', 'pdf', 'ofx'
    tamanho_bytes = Column(Integer)
    hash_arquivo = Column(String(64), index=True)  # MD5 para evitar duplicatas
    
    # Processamento
    data_upload = Column(DateTime, default=datetime.now)
    data_processamento_inicio = Column(DateTime, nullable=True)
    data_processamento_fim = Column(DateTime, nullable=True)
    tempo_processamento_segundos = Column(Float, nullable=True)
    
    # Banco detectado
    banco_detectado = Column(String(100), nullable=True)  # 'Itaú', 'Bradesco', 'Nubank'
    formato_detectado = Column(String(50), nullable=True)
    
    # Estatísticas
    total_transacoes = Column(Integer, default=0)
    total_categorizado_automatico = Column(Integer, default=0)
    total_precisa_revisao = Column(Integer, default=0)
    total_processado = Column(Integer, default=0)
    
    # Status
    status = Column(String(20), default='pendente')  # 'pendente', 'processando', 'concluido', 'erro'
    mensagem_erro = Column(Text, nullable=True)
    
    # Relacionamentos
    # usuario = relationship("User", back_populates="arquivos_extrato")  # Disabled - User.arquivos_extrato comentado


class HistoricoAtualizacaoDRE(BaseTenantModel):
    """
    Histórico de atualizações retroativas em DRE já fechada.
    Para auditoria e rastreamento.
    """
    __tablename__ = 'historico_atualizacao_dre'
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    dre_periodo_id = Column(Integer, ForeignKey('dre_periodos.id'), nullable=False)
    
    # Dados da atualização
    tipo_alteracao = Column(String(50))  # 'devolucao', 'nota_atrasada', 'correcao_manual'
    descricao = Column(Text)
    
    # Valores antes/depois
    valores_anteriores = Column(JSON)  # {receita_bruta: 26500, lucro_liquido: 3430, ...}
    valores_novos = Column(JSON)
    diferencas = Column(JSON)  # {receita_bruta: -150, lucro_liquido: -2200, ...}
    
    # Auditoria
    usuario_alteracao_id = Column(Integer, ForeignKey('users.id'))
    data_alteracao = Column(DateTime, default=datetime.now)
    motivo = Column(Text, nullable=True)
    aprovado_por = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Relacionamentos
    # usuario = relationship("User", foreign_keys=[usuario_id], back_populates="historico_dre")  # Disabled - User.historico_dre comentado
    dre_periodo = relationship("DREPeriodo", back_populates="historico_atualizacoes")


class ConfiguracaoTributaria(BaseTenantModel):
    """
    Configuração de regime tributário da empresa.
    Usado para cálculo automático de impostos na DRE.
    """
    __tablename__ = 'configuracao_tributaria'
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)
    
    # Regime tributário
    regime = Column(String(50), nullable=False)  # 'simples_nacional', 'lucro_presumido', 'lucro_real', 'mei'
    
    # Simples Nacional
    anexo_simples = Column(String(20), nullable=True)  # 'Anexo I', 'Anexo II', etc
    faixa_simples = Column(String(50), nullable=True)  # 'Faixa 1 (até 180k)'
    aliquota_efetiva_simples = Column(Float, nullable=True)  # 8.54%
    
    # Lucro Presumido
    presuncao_lucro_percentual = Column(Float, nullable=True)  # 8% para comércio
    aliquota_irpj = Column(Float, nullable=True)  # 15%
    aliquota_adicional_irpj = Column(Float, nullable=True)  # 10% acima 20k/mês
    aliquota_csll = Column(Float, nullable=True)  # 9%
    aliquota_pis = Column(Float, nullable=True)  # 0.65%
    aliquota_cofins = Column(Float, nullable=True)  # 3%
    
    # ICMS (Estadual)
    estado = Column(String(2), nullable=True)  # 'SP', 'RJ', etc
    aliquota_icms = Column(Float, nullable=True)  # 18%
    incluir_icms_dre = Column(Boolean, default=True)
    
    # ISS (para serviços)
    aliquota_iss = Column(Float, nullable=True)  # 2% a 5%
    incluir_iss_dre = Column(Boolean, default=False)
    
    # Metadados
    criado_em = Column(DateTime, default=datetime.now)
    atualizado_em = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relacionamentos
    # usuario = relationship("User", back_populates="configuracao_tributaria")  # Disabled - User.configuracao_tributaria comentado


    # Relacionamentos - DUPLICADO (manter comentado)
    # usuario = relationship("User", back_populates="configuracao_tributaria")

