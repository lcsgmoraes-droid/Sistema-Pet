"""
Modelos de Estoque - Alertas e Controles
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.base_models import BaseTenantModel


class AlertaEstoqueNegativo(BaseTenantModel):
    """
    Alerta persistente de estoque negativo.
    
    🟢 MODELO CONTROLADO:
    - Registra quando produto fica com estoque negativo
    - Mantém histórico de alertas
    - Permite rastreamento de produtos pendentes de reposição
    - Exibe no dashboard e relatórios
    """
    __tablename__ = "alertas_estoque_negativo"

    produto_id = Column(Integer, ForeignKey('produtos.id'), nullable=False)
    produto_nome = Column(String(255), nullable=False)  # Denormalizado para performance
    
    # Estado do estoque no momento do alerta
    estoque_anterior = Column(Float, nullable=False)
    quantidade_vendida = Column(Float, nullable=False)
    estoque_resultante = Column(Float, nullable=False)  # Valor negativo
    
    # Contexto da venda que gerou o alerta
    venda_id = Column(Integer, ForeignKey('vendas.id'), nullable=True)
    venda_codigo = Column(String(50), nullable=True)
    
    # Controle do alerta
    data_alerta = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(String(20), nullable=False, default='pendente')  # pendente, resolvido, ignorado
    data_resolucao = Column(DateTime, nullable=True)
    usuario_resolucao_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True)
    observacao = Column(String(500), nullable=True)
    
    # Flags
    notificado = Column(Boolean, nullable=False, default=False)
    critico = Column(Boolean, nullable=False, default=False)  # True se estoque_resultante < -5
    
    # Relationships
    produto = relationship("Produto", foreign_keys=[produto_id])
    venda = relationship("Venda", foreign_keys=[venda_id])
    usuario_resolucao = relationship("User", foreign_keys=[usuario_resolucao_id])

    def __repr__(self):
        return f"<AlertaEstoqueNegativo {self.produto_nome}: {self.estoque_resultante}>"
