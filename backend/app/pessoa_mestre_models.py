"""Pessoa mestre — Checkpoint 4 da camada geral do grupo comercial.

O mais sensível dos quatro domínios (dado pessoal, LGPD) e o mais
complexo (a mesma tabela `clientes` local cobre cliente/fornecedor/
veterinário/funcionário ao mesmo tempo, via as flags `is_cliente`/
`is_fornecedor`/`is_veterinario`/`is_funcionario`). Por isso o vínculo
aqui é sempre
sugestão + confirmação manual, nunca automático — mesmo quando um CPF
bate exatamente, é uma ação explícita do usuário que efetiva o vínculo
(ver Documentacao/Dominio/Plano-Camada-Geral.md, Checkpoint 4).

Guarda só identidade (nome, documento, contato, endereço, tipo, CRMV).
Histórico de compra, segmentação, campos financeiros/DRE, consentimento e
tudo que descreve a relação comercial continuam 100% no Cliente local —
cada loja é dona do que coletou.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.clientes.common import tipos_cadastro_da_pessoa
from app.db import Base


class PessoaMestre(Base):
    __tablename__ = "pessoa_mestre"
    __table_args__ = (
        UniqueConstraint("grupo_id", "cpf", name="uq_pessoa_mestre_grupo_cpf"),
        UniqueConstraint("grupo_id", "cnpj", name="uq_pessoa_mestre_grupo_cnpj"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    grupo_id = Column(
        Integer,
        ForeignKey("grupos_comerciais.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    nome = Column(String(255), nullable=False)
    tipo_pessoa = Column(String(2), nullable=True)  # PF | PJ
    is_cliente = Column(Boolean, nullable=False, default=False, server_default="0")
    is_fornecedor = Column(Boolean, nullable=False, default=False, server_default="0")
    is_veterinario = Column(Boolean, nullable=False, default=False, server_default="0")
    is_funcionario = Column(Boolean, nullable=False, default=False, server_default="0")
    cpf = Column(String(14), nullable=True, index=True)
    cnpj = Column(String(18), nullable=True, index=True)
    inscricao_estadual = Column(String(20), nullable=True)
    razao_social = Column(String(255), nullable=True)
    nome_fantasia = Column(String(255), nullable=True)
    crmv = Column(String(20), nullable=True)
    data_nascimento = Column(DateTime, nullable=True)

    telefone = Column(String(50), nullable=True)
    celular = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)

    cep = Column(String(10), nullable=True)
    endereco = Column(String(500), nullable=True)
    numero = Column(String(20), nullable=True)
    complemento = Column(String(100), nullable=True)
    bairro = Column(String(100), nullable=True)
    cidade = Column(String(100), nullable=True)
    estado = Column(String(2), nullable=True)
    codigo_municipio = Column(String(7), nullable=True)

    ativo = Column(Boolean, nullable=False, default=True, server_default="true")
    criado_por_usuario_id = Column(Integer, nullable=False)
    criado_em = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    atualizado_em = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    @property
    def tipos_cadastro(self) -> list[str]:
        return tipos_cadastro_da_pessoa(self)
