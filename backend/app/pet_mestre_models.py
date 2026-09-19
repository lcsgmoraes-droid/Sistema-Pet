"""Pet mestre — Checkpoint 3 da camada geral do grupo comercial.

Identidade e perfil de saúde/comportamento do animal, compartilhados entre
lojas do mesmo grupo — o ganho mais visível pro tutor (não precisa
recadastrar alergia/doença crônica/microchip numa segunda loja). Eventos
clínicos (consulta, vacina, exame, internação) continuam 100% locais —
aqui não entra nada do prontuário, só a identidade do pet. `PerfilComportamental`
(hoje satélite 1:1 do Pet local) entra dobrado direto nos campos deste
modelo, não como tabela satélite própria. Ver
Documentacao/Dominio/Plano-Camada-Geral.md, Checkpoint 3.
"""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.db import Base


class PetMestre(Base):
    __tablename__ = "pet_mestre"

    id = Column(Integer, primary_key=True, autoincrement=True)
    grupo_id = Column(
        Integer,
        ForeignKey("grupos_comerciais.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identidade
    nome = Column(String(255), nullable=False)
    especie = Column(String(50), nullable=False)
    raca = Column(String(100), nullable=True)
    sexo = Column(String(10), nullable=True)
    porte = Column(String(20), nullable=True)
    cor = Column(String(100), nullable=True)
    cor_pelagem = Column(String(100), nullable=True)
    data_nascimento = Column(DateTime, nullable=True)
    castrado = Column(Boolean, default=False)
    castrado_data = Column(Date, nullable=True)
    foto_url = Column(String(500), nullable=True)

    # Saúde
    microchip = Column(String(50), nullable=True, index=True)
    tipo_sanguineo = Column(String(20), nullable=True)
    pedigree_registro = Column(String(100), nullable=True)
    alergias = Column(Text, nullable=True)
    alergias_lista = Column(JSON, nullable=True)
    doencas_cronicas = Column(Text, nullable=True)
    condicoes_cronicas_lista = Column(JSON, nullable=True)
    medicamentos_continuos = Column(Text, nullable=True)
    medicamentos_continuos_lista = Column(JSON, nullable=True)
    restricoes_alimentares_lista = Column(JSON, nullable=True)
    historico_clinico = Column(Text, nullable=True)

    # Perfil comportamental (dobrado do satélite local PerfilComportamental)
    temperamento = Column(String(50), nullable=True)
    reacao_animais = Column(String(50), nullable=True)
    reacao_pessoas = Column(String(50), nullable=True)
    medo_secador = Column(String(50), nullable=True)
    medo_tesoura = Column(String(50), nullable=True)
    aceita_focinheira = Column(String(50), nullable=True)
    comportamento_carro = Column(String(50), nullable=True)

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
