# -*- coding: utf-8 -*-
"""
Models para o módulo de Vendas (PDV)
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, DECIMAL, Identity, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from app.db import Base
from app.base_models import BaseTenantModel
from app.utils.serialization import safe_decimal_to_float, safe_datetime_to_iso


class Venda(BaseTenantModel):
    """Tabela principal de vendas
    
    Herda de BaseTenantModel que já fornece:
    - id: Integer, Identity(always=True), primary_key
    - tenant_id: UUID, injetado automaticamente
    - created_at, updated_at: DateTime, gerenciados automaticamente
    """
    __tablename__ = 'vendas'
    
    numero_venda = Column(String(20), unique=True, nullable=False, index=True)  # VEN-YYYYMMDD-XXXX
    
    # Cliente e Vendedor
    cliente_id = Column(Integer, ForeignKey('clientes.id'), nullable=True)
    vendedor_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    funcionario_id = Column(Integer, ForeignKey('clientes.id'), nullable=True)  # Funcionário comissionado
    
    # Valores
    subtotal = Column(DECIMAL(10, 2), nullable=False)
    desconto_valor = Column(DECIMAL(10, 2), default=0)
    desconto_percentual = Column(DECIMAL(5, 2), default=0)
    total = Column(DECIMAL(10, 2), nullable=False)
    
    # Entrega
    tem_entrega = Column(Boolean, default=False)
    taxa_entrega = Column(DECIMAL(10, 2), default=0)
    
    # 📊 Distribuição da taxa de entrega (quanto vai para quem)
    percentual_taxa_entregador = Column(DECIMAL(5, 2), default=0)  # % da taxa que vai para o entregador (0-100)
    percentual_taxa_loja = Column(DECIMAL(5, 2), default=100)  # % da taxa que fica para a loja (0-100)
    valor_taxa_entregador = Column(DECIMAL(10, 2), default=0)  # Valor calculado para o entregador (gera conta a pagar)
    valor_taxa_loja = Column(DECIMAL(10, 2), default=0)  # Valor calculado que fica para a loja (receita líquida)
    
    entregador_id = Column(Integer, ForeignKey('clientes.id'), nullable=True)
    loja_origem = Column(String(100), nullable=True)
    endereco_entrega = Column(Text, nullable=True)
    distancia_km = Column(DECIMAL(10, 2), nullable=True)
    valor_por_km = Column(DECIMAL(10, 2), nullable=True)
    observacoes_entrega = Column(Text, nullable=True)
    status_entrega = Column(String(20), nullable=True)  # pendente, em_rota, entregue, cancelado
    data_entrega = Column(DateTime, nullable=True)
    ordem_entrega_otimizada = Column(Integer, nullable=True, index=True)  # Ordem otimizada pelo Google Maps (economiza chamadas à API)
    
    # Observações da Venda
    observacoes = Column(Text, nullable=True)
    
    # Vínculo com Caixa
    caixa_id = Column(Integer, ForeignKey('caixas.id'), nullable=True, index=True)  # Caixa onde a venda foi feita
    
    # Canal de Venda (para DRE por canal)
    canal = Column(String(50), default='loja_fisica', nullable=False, index=True)  # loja_fisica, mercado_livre, shopee, amazon, site, instagram
    
    # Financeiro (FASE 3) - COMENTADO até migração
    # nsu = Column(String(50), nullable=True, index=True)  # NSU da operadora de cartão (para conciliação)
    # origem_venda = Column(String(20), default='fisica')  # fisica, online
    
    # ============================
    # CONCILIAÇÃO DE VENDAS (NOVA ARQUITETURA 3 ABAS)
    # ============================
    conciliado_vendas = Column(Boolean, default=False, nullable=False, index=True, comment="Se venda foi conferida na Aba 1 (PDV vs Stone)")
    conciliado_vendas_em = Column(DateTime, nullable=True, comment="Data/hora que vendas foram conferidas")
    
    # Status e Auditoria
    status = Column(String(20), nullable=False, default='aberta')  # aberta, finalizada, cancelada
    data_venda = Column(DateTime, nullable=False, default=datetime.now)
    data_finalizacao = Column(DateTime, nullable=True)
    cancelada_por = Column(Integer, ForeignKey('users.id'), nullable=True)
    motivo_cancelamento = Column(Text, nullable=True)
    data_cancelamento = Column(DateTime, nullable=True)  # 🆕 CANCELAMENTO ATÔMICO
    
    # DRE por Competência (PASSO 1 - Sprint 5)
    dre_gerada = Column(Boolean, default=False, nullable=False)  # Controla se DRE já foi gerada (receita, CMV, desconto)
    data_geracao_dre = Column(DateTime, nullable=True)  # Quando a DRE foi gerada pela primeira vez
    
    # Nota Fiscal Eletrônica (NF-e e NFC-e)
    nfe_tipo = Column(String(10), nullable=True)  # 'nfe' ou 'nfce'
    nfe_modelo = Column(String(5), nullable=True)  # '55' (NF-e) ou '65' (NFC-e)
    nfe_numero = Column(Integer, nullable=True, index=True)
    nfe_serie = Column(Integer, nullable=True)
    nfe_chave = Column(String(44), nullable=True, index=True)  # Chave de acesso
    nfe_status = Column(String(20), nullable=True)  # emitindo, autorizada, cancelada, denegada
    nfe_xml = Column(Text, nullable=True)  # XML da NF-e/NFC-e
    nfe_data_emissao = Column(DateTime, nullable=True)
    nfe_data_autorizacao = Column(DateTime, nullable=True)
    nfe_motivo_rejeicao = Column(Text, nullable=True)
    nfe_bling_id = Column(Integer, nullable=True)  # ID no Bling
    
    # Multi-tenant
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    cliente = relationship("Cliente", foreign_keys=[cliente_id], backref="vendas")
    vendedor = relationship("User", foreign_keys=[vendedor_id], backref="vendas_realizadas")
    entregador = relationship("Cliente", foreign_keys=[entregador_id], backref="entregas_realizadas")
    cancelador = relationship("User", foreign_keys=[cancelada_por], backref="vendas_canceladas")
    usuario = relationship("User", foreign_keys=[user_id], backref="vendas_empresa")
    
    itens = relationship("VendaItem", back_populates="venda", cascade="all, delete-orphan")
    pagamentos = relationship("VendaPagamento", back_populates="venda", cascade="all, delete-orphan")
    baixas = relationship("VendaBaixa", back_populates="venda", cascade="all, delete-orphan")
    
    def to_dict(self):
        # Calcular valor pago
        valor_pago = sum(float(pag.valor) for pag in self.pagamentos) if hasattr(self, 'pagamentos') else 0
        
        # Desserializar enderecos_adicionais do cliente
        import json
        cliente_dict = None
        if self.cliente:
            enderecos_adicionais = None
            if self.cliente.enderecos_adicionais:
                if isinstance(self.cliente.enderecos_adicionais, str):
                    try:
                        enderecos_adicionais = json.loads(self.cliente.enderecos_adicionais)
                    except:
                        enderecos_adicionais = None
                else:
                    enderecos_adicionais = self.cliente.enderecos_adicionais
            
            cliente_dict = {
                'id': self.cliente.id,
                'nome': self.cliente.nome,
                'telefone': self.cliente.telefone,
                'celular': self.cliente.celular,
                'email': self.cliente.email,
                'endereco': self.cliente.endereco,
                'numero': self.cliente.numero,
                'complemento': self.cliente.complemento,
                'bairro': self.cliente.bairro,
                'cidade': self.cliente.cidade,
                'estado': self.cliente.estado,
                'enderecos_adicionais': enderecos_adicionais
            }
        
        return {
            'id': self.id,
            'numero_venda': self.numero_venda,
            'cliente_id': self.cliente_id,
            'cliente_nome': self.cliente.nome if self.cliente else None,
            'nome_cliente': self.cliente.nome if self.cliente else None,
            'cliente': cliente_dict,
            'vendedor_id': self.vendedor_id,
            'funcionario_id': self.funcionario_id,
            'subtotal': safe_decimal_to_float(self.subtotal),
            'desconto_valor': safe_decimal_to_float(self.desconto_valor) or 0,
            'desconto_percentual': safe_decimal_to_float(self.desconto_percentual) or 0,
            'total': safe_decimal_to_float(self.total),
            'valor_total': safe_decimal_to_float(self.total),  # Alias para compatibilidade
            'valor_pago': valor_pago,
            'valor_restante': safe_decimal_to_float(self.total) - valor_pago,
            'tem_entrega': self.tem_entrega,
            'taxa_entrega': safe_decimal_to_float(self.taxa_entrega) or 0,
            'entrega': {
                'endereco_completo': self.endereco_entrega,
                'taxa_entrega_total': safe_decimal_to_float(self.taxa_entrega) or 0,
                'taxa_loja': safe_decimal_to_float(self.valor_taxa_loja) if self.valor_taxa_loja else 0,
                'taxa_entregador': safe_decimal_to_float(self.valor_taxa_entregador) if self.valor_taxa_entregador else 0,
                'percentual_taxa_loja': safe_decimal_to_float(self.percentual_taxa_loja) if self.percentual_taxa_loja else 0,
                'percentual_taxa_entregador': safe_decimal_to_float(self.percentual_taxa_entregador) if self.percentual_taxa_entregador else 0,
                'distancia_km': safe_decimal_to_float(self.distancia_km),
                'valor_por_km': safe_decimal_to_float(self.valor_por_km),
                'loja_origem': self.loja_origem,
                'observacoes_entrega': self.observacoes_entrega,
                'entregador_id': self.entregador_id,
                'status_entrega': self.status_entrega
            } if self.tem_entrega else None,
            'status': self.status,
            'status_entrega': self.status_entrega,
            'status_pagamento': 'pago' if valor_pago >= safe_decimal_to_float(self.total) else 'parcial' if valor_pago > 0 else 'pendente',
            'forma_pagamento': self.pagamentos[0].forma_pagamento if (hasattr(self, 'pagamentos') and self.pagamentos and len(self.pagamentos) > 0) else None,
            'data_venda': safe_datetime_to_iso(self.data_venda),
            'data_finalizacao': safe_datetime_to_iso(self.data_finalizacao),
            'observacoes': self.observacoes,
            'observacoes_entrega': self.observacoes_entrega,
            'endereco_entrega': self.endereco_entrega,
            'itens': [item.to_dict() for item in self.itens] if hasattr(self, 'itens') else [],
            'pagamentos': [pag.to_dict() for pag in self.pagamentos] if hasattr(self, 'pagamentos') else [],
        }
    
    def __repr__(self):
        return f"<Venda {self.numero_venda} - R$ {self.total}>"


class VendaItem(BaseTenantModel):
    """Itens da venda (produtos ou serviços)"""
    __tablename__ = 'venda_itens'
    
    id = Column(Integer, primary_key=True, index=True)
    venda_id = Column(Integer, ForeignKey('vendas.id', ondelete='CASCADE'), nullable=False)
    
    # Produto ou Serviço
    tipo = Column(String(20), nullable=False)  # produto, servico
    produto_id = Column(Integer, ForeignKey('produtos.id'), nullable=True)
    
    # ========== SPRINT 2: SUPORTE A VARIAÇÕES ==========
    # CORRIGIDO: Não existe tabela product_variations separada
    # O sistema usa produtos.tipo_produto = 'VARIACAO' dentro da própria tabela produtos
    # Por isso, product_variation_id aponta para produtos.id
    # Manter por compatibilidade, mas usar produto_id para variações também
    product_variation_id = Column(Integer, nullable=True)  # ⚠️ DEPRECATED: usar produto_id
    
    servico_descricao = Column(String(255), nullable=True)
    
    # Valores
    quantidade = Column(DECIMAL(10, 3), nullable=False)
    preco_unitario = Column(DECIMAL(10, 2), nullable=False)
    desconto_item = Column(DECIMAL(10, 2), default=0)
    subtotal = Column(DECIMAL(10, 2), nullable=False)
    
    # Referência ao lote (FIFO)
    lote_id = Column(Integer, ForeignKey('produto_lotes.id'), nullable=True)
    
    # Vincular item a um pet específico
    pet_id = Column(Integer, ForeignKey('pets.id'), nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    
    # Relacionamentos
    venda = relationship("Venda", back_populates="itens")
    produto = relationship("Produto", backref="vendas_itens")
    lote = relationship("ProdutoLote", backref="vendas_itens")
    pet = relationship("Pet", backref="vendas_itens")
    
    # ========== SPRINT 2: SUPORTE A VARIAÇÕES ==========
    # ❌ DESABILITADO: ProductVariation removido - causava conflitos
    # variation = relationship("ProductVariation", backref="vendas_itens")
    
    def to_dict(self):
        from sqlalchemy.orm import Session
        from sqlalchemy import inspect
        
        result = {
            'id': self.id,
            'tipo': self.tipo,
            'produto_id': self.produto_id,
            'produto_nome': self.produto.nome if self.produto else self.servico_descricao,
            'servico_descricao': self.servico_descricao,
            'quantidade': safe_decimal_to_float(self.quantidade),
            'preco_unitario': safe_decimal_to_float(self.preco_unitario),
            'valor_unitario': safe_decimal_to_float(self.preco_unitario),  # Alias para compatibilidade
            'desconto_item': safe_decimal_to_float(self.desconto_item) or 0,
            'subtotal': safe_decimal_to_float(self.subtotal),
            'pet_id': self.pet_id,
            'pet_nome': self.pet.nome if self.pet else None,
            'pet_codigo': self.pet.codigo if self.pet else None,
        }
        
        # Incluir detalhes do produto se disponível
        if self.produto:
            result['produto'] = {
                'id': self.produto.id,
                'nome': self.produto.nome,
                'codigo': self.produto.codigo if hasattr(self.produto, 'codigo') else None,
            }
        
        # Incluir detalhes do serviço se for serviço
        if self.tipo == 'servico' and self.servico_descricao:
            result['servico'] = {
                'nome': self.servico_descricao,
            }
        
        # Adicionar informações de KIT se o produto for um KIT
        if self.produto:
            result['tipo_produto'] = self.produto.tipo_produto
            result['tipo_kit'] = self.produto.tipo_kit
            
            # Se for KIT, incluir composição
            if self.produto.tipo_produto == 'KIT':
                try:
                    # Carregar componentes do KIT (lazy load se necessário)
                    from .produtos_models import ProdutoKitComponente
                    
                    session = inspect(self.produto).session
                    if session:
                        componentes = session.query(ProdutoKitComponente).filter_by(
                            kit_id=self.produto.id
                        ).all()
                        
                        result['composicao_kit'] = [
                            {
                                'produto_id': comp.produto_componente_id,
                                'produto_nome': comp.produto_componente.nome if comp.produto_componente else None,
                                'quantidade': safe_decimal_to_float(comp.quantidade)
                            }
                            for comp in componentes
                        ]
                    else:
                        result['composicao_kit'] = []
                except Exception as e:
                    # Se der erro, retornar lista vazia
                    result['composicao_kit'] = []
            else:
                result['composicao_kit'] = []
        else:
            result['tipo_produto'] = None
            result['tipo_kit'] = None
            result['composicao_kit'] = []
        
        return result
    
    def __repr__(self):
        return f"<VendaItem {self.tipo} - {self.quantidade}x R$ {self.preco_unitario}>"


class VendaPagamento(BaseTenantModel):
    """Formas de pagamento da venda"""
    __tablename__ = 'venda_pagamentos'
    
    id = Column(Integer, primary_key=True, index=True)
    venda_id = Column(Integer, ForeignKey('vendas.id', ondelete='CASCADE'), nullable=False)
    
    # Forma de Pagamento
    forma_pagamento = Column(String(50), nullable=False)  # dinheiro, cartao_credito, cartao_debito, pix, boleto, outros
    valor = Column(DECIMAL(10, 2), nullable=False)
    
    # Detalhes (se cartão)
    bandeira = Column(String(30), nullable=True)  # visa, master, elo, etc
    numero_parcelas = Column(Integer, default=1)  # Número de parcelas (cartão parcelado)
    numero_transacao = Column(String(100), nullable=True)
    numero_autorizacao = Column(String(100), nullable=True)
    nsu_cartao = Column(String(50), nullable=True, index=True)  # NSU da operadora (para conciliação)
    operadora_id = Column(Integer, ForeignKey('operadoras_cartao.id'), nullable=True, index=True)  # Operadora (Stone, Cielo, etc)
    status_conciliacao = Column(Enum('nao_conciliado', 'conciliado', name='status_conciliacao_enum'), nullable=False, server_default='nao_conciliado')  # Status da conciliação
    
    # Troco (se dinheiro)
    valor_recebido = Column(DECIMAL(10, 2), nullable=True)
    troco = Column(DECIMAL(10, 2), nullable=True)
    
    # Status
    status = Column(String(20), default='pendente')  # pendente, aprovado, recusado, estornado
    data_pagamento = Column(DateTime, default=datetime.now)
    
    created_at = Column(DateTime, default=func.now())
    
    # Relacionamentos
    venda = relationship("Venda", back_populates="pagamentos")
    operadora_cartao = relationship("OperadoraCartao", back_populates="venda_pagamentos")
    
    def to_dict(self):
        return {
            'id': self.id,
            'forma_pagamento': self.forma_pagamento,
            'valor': safe_decimal_to_float(self.valor),
            'bandeira': self.bandeira,
            'numero_parcelas': self.numero_parcelas,
            'status': self.status,
            'data_pagamento': safe_datetime_to_iso(self.data_pagamento),
        }
    
    def __repr__(self):
        return f"<VendaPagamento {self.forma_pagamento} - R$ {self.valor}>"


class VendaBaixa(BaseTenantModel):
    """Registros de baixas (parciais ou totais) de vendas"""
    __tablename__ = 'venda_baixas'
    
    # Override BaseTenantModel's updated_at since this table doesn't have it
    updated_at = None
    
    id = Column(Integer, primary_key=True, index=True)
    venda_id = Column(Integer, ForeignKey('vendas.id', ondelete='CASCADE'), nullable=False)
    
    # Valores
    valor_baixa = Column(DECIMAL(10, 2), nullable=False)
    valor_anterior = Column(DECIMAL(10, 2), nullable=False)  # Saldo antes da baixa
    valor_restante = Column(DECIMAL(10, 2), nullable=False)  # Saldo após baixa
    
    # Forma de recebimento
    forma_pagamento = Column(String(50), nullable=False)
    
    # Auditoria
    tipo = Column(String(20), nullable=False)  # baixa_total, baixa_parcial
    usuario_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    observacoes = Column(Text, nullable=True)
    data_baixa = Column(DateTime, default=datetime.now)
    
    # Controle de edição/exclusão
    editado = Column(Boolean, default=False)
    editado_por = Column(Integer, ForeignKey('users.id'), nullable=True)
    data_edicao = Column(DateTime, nullable=True)
    excluido = Column(Boolean, default=False)
    excluido_por = Column(Integer, ForeignKey('users.id'), nullable=True)
    data_exclusao = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    
    # Relacionamentos
    venda = relationship("Venda", back_populates="baixas")
    usuario = relationship("User", foreign_keys=[usuario_id], backref="baixas_realizadas")
    editor = relationship("User", foreign_keys=[editado_por], backref="baixas_editadas")
    exclusor = relationship("User", foreign_keys=[excluido_por], backref="baixas_excluidas")
    
    def to_dict(self):
        return {
            'id': self.id,
            'valor_baixa': safe_decimal_to_float(self.valor_baixa),
            'valor_anterior': safe_decimal_to_float(self.valor_anterior),
            'valor_restante': safe_decimal_to_float(self.valor_restante),
            'forma_pagamento': self.forma_pagamento,
            'tipo': self.tipo,
            'data_baixa': safe_datetime_to_iso(self.data_baixa),
            'observacoes': self.observacoes,
        }
    
    def __repr__(self):
        return f"<VendaBaixa {self.tipo} - R$ {self.valor_baixa}>"

