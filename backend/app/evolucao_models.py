"""Metricas globais e anonimas do ciclo de implantacao das funcionalidades."""

from sqlalchemy import Column, DateTime, Integer, String

from app.db import Base


class EvolucaoFuncionalidadeUso(Base):
    """Contador agregado, sem dados de clientes ou empresas.

    A tabela e global por design porque o status exibido em Novidades representa
    o estagio do produto CorePet como um todo, e nao o uso de uma empresa.
    """

    __tablename__ = "evolucao_funcionalidade_usos"

    item_id = Column(String(120), primary_key=True)
    usos_total = Column(Integer, nullable=False, default=0)
    primeiro_uso_em = Column(DateTime(timezone=True), nullable=True)
    ultimo_uso_em = Column(DateTime(timezone=True), nullable=True)
    limiar_teste_atingido_em = Column(DateTime(timezone=True), nullable=True)
