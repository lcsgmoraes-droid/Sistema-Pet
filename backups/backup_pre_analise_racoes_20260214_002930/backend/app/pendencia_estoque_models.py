"""
Modelos para Sistema de Pendências/Lista de Espera de Estoque
Permite registrar clientes interessados em produtos sem estoque
e notificar automaticamente quando o produto retornar
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.base_models import BaseTenantModel


class PendenciaEstoque(BaseTenantModel):
    """
    Registra clientes aguardando produtos sem estoque.
    Quando o produto entra no estoque, cliente é notificado automaticamente.
    """
    __tablename__ = 'pendencias_estoque'
    
    # Relacionamentos
    cliente_id = Column(Integer, ForeignKey('clientes.id'), nullable=False, index=True)
    produto_id = Column(Integer, ForeignKey('produtos.id'), nullable=False, index=True)
    usuario_registrou_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Dados da pendência
    quantidade_desejada = Column(Float, nullable=False)
    valor_referencia = Column(Float, nullable=True)  # Preço do produto no momento do registro
    observacoes = Column(Text, nullable=True)
    
    # Status: pendente, notificado, finalizado, cancelado
    status = Column(String(20), default='pendente', nullable=False, index=True)
    
    # Controle de notificação
    data_notificacao = Column(DateTime, nullable=True)
    whatsapp_enviado = Column(Boolean, default=False)
    mensagem_whatsapp_id = Column(String(100), nullable=True)  # ID da mensagem enviada
    
    # Finalização
    data_finalizacao = Column(DateTime, nullable=True)
    venda_id = Column(Integer, ForeignKey('vendas.id'), nullable=True)  # Venda que finalizou a pendência
    motivo_cancelamento = Column(Text, nullable=True)
    
    # Prioridade (0 = normal, 1 = alta, 2 = urgente)
    prioridade = Column(Integer, default=0)
    
    # Metadata
    data_registro = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    cliente = relationship("Cliente", foreign_keys=[cliente_id], backref="pendencias_estoque")
    produto = relationship("Produto", foreign_keys=[produto_id], backref="pendencias")
    usuario_registrou = relationship("User", foreign_keys=[usuario_registrou_id])
    venda = relationship("Venda", foreign_keys=[venda_id])
    
    def to_dict(self):
        """Converte para dicionário"""
        return {
            'id': self.id,
            'tenant_id': str(self.tenant_id),
            'cliente_id': self.cliente_id,
            'cliente_nome': self.cliente.nome if self.cliente else None,
            'cliente_telefone': self.cliente.celular if self.cliente else None,
            'produto_id': self.produto_id,
            'produto_nome': self.produto.nome if self.produto else None,
            'produto_codigo': self.produto.codigo if self.produto else None,
            'quantidade_desejada': float(self.quantidade_desejada) if self.quantidade_desejada else 0,
            'valor_referencia': float(self.valor_referencia) if self.valor_referencia else None,
            'observacoes': self.observacoes,
            'status': self.status,
            'prioridade': self.prioridade,
            'data_registro': self.data_registro.isoformat() if self.data_registro else None,
            'data_notificacao': self.data_notificacao.isoformat() if self.data_notificacao else None,
            'whatsapp_enviado': self.whatsapp_enviado,
            'data_finalizacao': self.data_finalizacao.isoformat() if self.data_finalizacao else None,
            'venda_id': self.venda_id,
            'motivo_cancelamento': self.motivo_cancelamento,
            'usuario_registrou': self.usuario_registrou.nome if self.usuario_registrou else None
        }
