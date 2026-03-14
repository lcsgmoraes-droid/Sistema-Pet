"""
Modelos do módulo veterinário.
Todas as tabelas seguem o padrão multi-tenant (BaseTenantModel).
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, Text,
    DateTime, Date, ForeignKey, JSON, DECIMAL, Numeric, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.base_models import BaseTenantModel
from app.db import Base


# ==============================================================
# CATÁLOGO DE MEDICAMENTOS VETERINÁRIOS
# ==============================================================

class MedicamentoCatalogo(BaseTenantModel):
    """
    Catálogo de medicamentos veterinários.
    Pode ser preenchido manualmente ou via importação de bulas.
    """
    __tablename__ = "vet_medicamentos_catalogo"

    nome = Column(String(255), nullable=False, index=True)
    nome_comercial = Column(String(255), nullable=True)
    principio_ativo = Column(String(255), nullable=True, index=True)
    fabricante = Column(String(255), nullable=True)
    forma_farmaceutica = Column(String(100), nullable=True)   # comprimido, injetável, solução, etc.
    concentracao = Column(String(100), nullable=True)         # 50mg, 10mg/mL, etc.
    especies_indicadas = Column(JSON, nullable=True)          # ["cão","gato"]
    indicacoes = Column(Text, nullable=True)
    contraindicacoes = Column(Text, nullable=True)
    interacoes = Column(Text, nullable=True)
    posologia_referencia = Column(Text, nullable=True)        # Ex: 10mg/kg a cada 12h
    dose_min_mgkg = Column(Float, nullable=True)
    dose_max_mgkg = Column(Float, nullable=True)
    eh_antibiotico = Column(Boolean, default=False, nullable=False)
    eh_controlado = Column(Boolean, default=False, nullable=False)  # receituário especial
    observacoes = Column(Text, nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)


# ==============================================================
# PROTOCOLO DE VACINAS
# ==============================================================

class ProtocoloVacina(BaseTenantModel):
    """Vacinas disponíveis para cadastro — configurável por clínica."""
    __tablename__ = "vet_protocolos_vacinas"

    nome = Column(String(255), nullable=False)         # V10, Antirrábica, etc.
    especie = Column(String(50), nullable=True)        # cão, gato, todos
    dose_inicial_semanas = Column(Integer, nullable=True)
    reforco_anual = Column(Boolean, default=True)
    intervalo_doses_dias = Column(Integer, nullable=True)  # dias entre doses da série
    numero_doses_serie = Column(Integer, default=1)
    observacoes = Column(Text, nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)


# ==============================================================
# AGENDAMENTO VETERINÁRIO
# ==============================================================

class AgendamentoVet(BaseTenantModel):
    """Agenda de consultas veterinárias."""
    __tablename__ = "vet_agendamentos"

    pet_id = Column(Integer, ForeignKey("pets.id"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    veterinario_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)  # Cliente com tipo_cadastro=veterinario
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    data_hora = Column(DateTime(timezone=True), nullable=False, index=True)
    duracao_minutos = Column(Integer, default=30)

    tipo = Column(String(50), nullable=False, default="consulta")
    # consulta | retorno | vacina | cirurgia | emergencia | exame | internacao

    motivo = Column(Text, nullable=True)                    # motivo da consulta
    status = Column(String(30), nullable=False, default="agendado", index=True)
    # agendado | confirmado | em_atendimento | finalizado | cancelado | faltou

    # Pré-triagem respondida pelo tutor no app
    pretriagem = Column(JSON, nullable=True)

    # Emergência
    is_emergencia = Column(Boolean, default=False, nullable=False)
    sintoma_emergencia = Column(String(255), nullable=True)

    # Vínculo com consulta gerada
    consulta_id = Column(Integer, ForeignKey("vet_consultas.id"), nullable=True)

    # Hora efetiva de início e fim
    inicio_atendimento = Column(DateTime(timezone=True), nullable=True)
    fim_atendimento = Column(DateTime(timezone=True), nullable=True)

    observacoes = Column(Text, nullable=True)

    # Relacionamentos
    pet = relationship("Pet", foreign_keys=[pet_id])
    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    veterinario = relationship("Cliente", foreign_keys=[veterinario_id])
    consulta = relationship("ConsultaVet", foreign_keys=[consulta_id], back_populates="agendamento")


# ==============================================================
# CONSULTA VETERINÁRIA
# ==============================================================

class ConsultaVet(BaseTenantModel):
    """
    Prontuário de consulta veterinária.
    Criada ao iniciar o atendimento a partir de um agendamento (ou avulsa).
    """
    __tablename__ = "vet_consultas"

    pet_id = Column(Integer, ForeignKey("pets.id"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    veterinario_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Controle de tempo do atendimento
    inicio_atendimento = Column(DateTime(timezone=True), nullable=True)
    fim_atendimento = Column(DateTime(timezone=True), nullable=True)

    # Tipo
    tipo = Column(String(50), nullable=False, default="consulta")
    # consulta | retorno | emergencia | cirurgia | preventivo

    status = Column(String(30), nullable=False, default="em_andamento", index=True)
    # em_andamento | finalizada | cancelada

    # ---- ANAMNESE ----
    queixa_principal = Column(Text, nullable=True)
    historia_clinica = Column(Text, nullable=True)  # anamnese livre

    # ---- SINAIS VITAIS ----
    peso_consulta = Column(Float, nullable=True)           # kg — registra nova pesagem
    temperatura = Column(Float, nullable=True)             # °C
    frequencia_cardiaca = Column(Integer, nullable=True)   # bpm
    frequencia_respiratoria = Column(Integer, nullable=True)  # mpm
    tpc = Column(String(20), nullable=True)                # Tempo de Preenchimento Capilar
    mucosas = Column(String(100), nullable=True)           # coradas, pálidas, ictéricas, etc.
    hidratacao = Column(String(50), nullable=True)         # hidratado, desidratado leve/moderado/grave
    nivel_dor = Column(Integer, nullable=True)             # escala 0-10
    saturacao_o2 = Column(Float, nullable=True)            # %
    pressao_sistolica = Column(Integer, nullable=True)     # mmHg
    pressao_diastolica = Column(Integer, nullable=True)    # mmHg
    glicemia = Column(Float, nullable=True)                # mg/dL

    # ---- EXAME FÍSICO ----
    exame_fisico = Column(Text, nullable=True)             # descrição do exame físico geral

    # ---- DIAGNÓSTICO ----
    hipotese_diagnostica = Column(Text, nullable=True)     # hipóteses
    diagnostico = Column(Text, nullable=True)              # diagnóstico definitivo
    diagnostico_simples = Column(Text, nullable=True)      # tradução em linguagem simples (IA)

    # ---- CONDUTA ----
    conduta = Column(Text, nullable=True)
    retorno_em_dias = Column(Integer, nullable=True)
    data_retorno = Column(Date, nullable=True)

    # ---- ASA SCORE ----
    asa_score = Column(Integer, nullable=True)             # 1-5
    asa_justificativa = Column(Text, nullable=True)

    # ---- OBSERVAÇÕES ----
    observacoes_internas = Column(Text, nullable=True)     # não aparece para tutor
    observacoes_tutor = Column(Text, nullable=True)        # visível no app

    # Hash para imutabilidade do prontuário finalizado
    hash_prontuario = Column(String(64), nullable=True)    # SHA-256 ao finalizar
    finalizado_em = Column(DateTime(timezone=True), nullable=True)
    finalizado_por_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relacionamentos
    pet = relationship("Pet", foreign_keys=[pet_id])
    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    veterinario = relationship("Cliente", foreign_keys=[veterinario_id])
    agendamento = relationship("AgendamentoVet", back_populates="consulta", uselist=False,
                               foreign_keys="AgendamentoVet.consulta_id")
    prescricoes = relationship("PrescricaoVet", back_populates="consulta", cascade="all, delete-orphan")
    exames = relationship("ExameVet", back_populates="consulta", cascade="all, delete-orphan")
    procedimentos = relationship("ProcedimentoConsulta", back_populates="consulta", cascade="all, delete-orphan")
    fotos_clinicas = relationship("FotoClinica", back_populates="consulta", cascade="all, delete-orphan")


# ==============================================================
# PRESCRIÇÃO VETERINÁRIA
# ==============================================================

class PrescricaoVet(BaseTenantModel):
    """Receita veterinária vinculada a uma consulta."""
    __tablename__ = "vet_prescricoes"

    consulta_id = Column(Integer, ForeignKey("vet_consultas.id"), nullable=False, index=True)
    pet_id = Column(Integer, ForeignKey("pets.id"), nullable=False, index=True)
    veterinario_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    numero = Column(String(50), nullable=True, index=True)   # número da receita
    data_emissao = Column(Date, nullable=False)

    # Tipo de receituário
    tipo_receituario = Column(String(30), default="simples")
    # simples | controle_especial_b | controle_especial_a | veterinaria_especial

    observacoes = Column(Text, nullable=True)

    # Hash/QR para validação
    hash_receita = Column(String(64), nullable=True)

    # Relacionamentos
    consulta = relationship("ConsultaVet", back_populates="prescricoes")
    pet = relationship("Pet", foreign_keys=[pet_id])
    itens = relationship("ItemPrescricao", back_populates="prescricao", cascade="all, delete-orphan")


class ItemPrescricao(BaseTenantModel):
    """Item (medicamento) de uma prescrição."""
    __tablename__ = "vet_itens_prescricao"

    prescricao_id = Column(Integer, ForeignKey("vet_prescricoes.id"), nullable=False, index=True)
    medicamento_catalogo_id = Column(Integer, ForeignKey("vet_medicamentos_catalogo.id"), nullable=True)

    nome_medicamento = Column(String(255), nullable=False)   # pode ser livre (sem catálogo)
    concentracao = Column(String(100), nullable=True)
    forma_farmaceutica = Column(String(100), nullable=True)
    quantidade = Column(String(100), nullable=True)          # "30 comprimidos"
    posologia = Column(Text, nullable=False)                 # "1 comp a cada 12h por 7 dias"
    via_administracao = Column(String(50), nullable=True)    # oral, subcutânea, IV, etc.
    duracao_dias = Column(Integer, nullable=True)

    # Relacionamentos
    prescricao = relationship("PrescricaoVet", back_populates="itens")
    medicamento = relationship("MedicamentoCatalogo", foreign_keys=[medicamento_catalogo_id])


# ==============================================================
# VACINAÇÃO
# ==============================================================

class VacinaRegistro(BaseTenantModel):
    """Registro de vacina aplicada em um pet."""
    __tablename__ = "vet_vacinas_registros"

    pet_id = Column(Integer, ForeignKey("pets.id"), nullable=False, index=True)
    consulta_id = Column(Integer, ForeignKey("vet_consultas.id"), nullable=True)
    veterinario_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    protocolo_id = Column(Integer, ForeignKey("vet_protocolos_vacinas.id"), nullable=True)

    nome_vacina = Column(String(255), nullable=False)         # nome livre ou do protocolo
    fabricante = Column(String(255), nullable=True)
    lote = Column(String(100), nullable=True)
    data_aplicacao = Column(Date, nullable=False, index=True)
    data_proxima_dose = Column(Date, nullable=True, index=True)
    numero_dose = Column(Integer, default=1)                  # 1ª dose, 2ª dose, reforço anual
    via_administracao = Column(String(50), nullable=True)     # subcutânea, intramuscular, intranasal

    observacoes = Column(Text, nullable=True)

    # Relacionamentos
    pet = relationship("Pet", foreign_keys=[pet_id])
    consulta = relationship("ConsultaVet", foreign_keys=[consulta_id])
    protocolo = relationship("ProtocoloVacina", foreign_keys=[protocolo_id])


# ==============================================================
# EXAMES LABORATORIAIS / DE IMAGEM
# ==============================================================

class ExameVet(BaseTenantModel):
    """Exames solicitados ou com resultado registrado."""
    __tablename__ = "vet_exames"

    pet_id = Column(Integer, ForeignKey("pets.id"), nullable=False, index=True)
    consulta_id = Column(Integer, ForeignKey("vet_consultas.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    tipo = Column(String(50), nullable=False, index=True)
    # laboratorial | imagem | eletrocardiograma | outro

    nome = Column(String(255), nullable=False)               # hemograma, rx_torax, etc.
    data_solicitacao = Column(Date, nullable=True)
    data_resultado = Column(Date, nullable=True, index=True)

    status = Column(String(30), default="solicitado")
    # solicitado | coletado | aguardando | disponivel | interpretado

    laboratorio = Column(String(255), nullable=True)
    resultado_texto = Column(Text, nullable=True)            # resultado livre
    resultado_json = Column(JSON, nullable=True)             # valores estruturados
    interpretacao = Column(Text, nullable=True)              # interpretação do vet
    interpretacao_ia = Column(Text, nullable=True)           # sugestão da IA
    interpretacao_ia_resumo = Column(Text, nullable=True)
    interpretacao_ia_confianca = Column(Float, nullable=True)
    interpretacao_ia_alertas = Column(JSON, nullable=True)
    interpretacao_ia_payload = Column(JSON, nullable=True)

    # Arquivo/imagem do resultado
    arquivo_url = Column(String(500), nullable=True)
    arquivo_nome = Column(String(255), nullable=True)

    observacoes = Column(Text, nullable=True)

    # Relacionamentos
    pet = relationship("Pet", foreign_keys=[pet_id])
    consulta = relationship("ConsultaVet", back_populates="exames", foreign_keys=[consulta_id])


# ==============================================================
# PROCEDIMENTOS REALIZADOS NA CONSULTA
# ==============================================================

class CatalogoProcedimento(BaseTenantModel):
    """Catálogo de procedimentos da clínica (configurável)."""
    __tablename__ = "vet_catalogo_procedimentos"

    nome = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)
    categoria = Column(String(100), nullable=True)  # cirurgia, exame, consulta, tosa, etc.
    valor_padrao = Column(DECIMAL(10, 2), nullable=True)
    duracao_minutos = Column(Integer, nullable=True)
    requer_anestesia = Column(Boolean, default=False)
    observacoes = Column(Text, nullable=True)
    insumos = Column(JSON, nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)


class ProcedimentoConsulta(BaseTenantModel):
    """Procedimento realizado durante uma consulta."""
    __tablename__ = "vet_procedimentos_consulta"

    consulta_id = Column(Integer, ForeignKey("vet_consultas.id"), nullable=False, index=True)
    catalogo_id = Column(Integer, ForeignKey("vet_catalogo_procedimentos.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    nome = Column(String(255), nullable=False)               # cópia do nome ou livre
    descricao = Column(Text, nullable=True)
    valor = Column(DECIMAL(10, 2), nullable=True)
    realizado = Column(Boolean, default=True)

    observacoes = Column(Text, nullable=True)
    insumos = Column(JSON, nullable=True)
    estoque_baixado = Column(Boolean, default=False, nullable=False)
    estoque_movimentacao_ids = Column(JSON, nullable=True)

    # Relacionamentos
    consulta = relationship("ConsultaVet", back_populates="procedimentos")
    catalogo = relationship("CatalogoProcedimento", foreign_keys=[catalogo_id])


# ==============================================================
# INTERNAÇÃO
# ==============================================================

class InternacaoVet(BaseTenantModel):
    """Registro de internação hospitalar veterinária."""
    __tablename__ = "vet_internacoes"

    pet_id = Column(Integer, ForeignKey("pets.id"), nullable=False, index=True)
    consulta_id = Column(Integer, ForeignKey("vet_consultas.id"), nullable=True)
    veterinario_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    data_entrada = Column(DateTime(timezone=True), nullable=False)
    data_saida = Column(DateTime(timezone=True), nullable=True)

    motivo = Column(Text, nullable=False)
    status = Column(String(30), default="internado", index=True)
    # internado | alta | obito | transferido

    # Sinais monitorados (lista de registros ao longo do dia)
    evolucoes = relationship("EvolucaoInternacao", back_populates="internacao",
                             cascade="all, delete-orphan")

    observacoes = Column(Text, nullable=True)

    # Relacionamentos
    pet = relationship("Pet", foreign_keys=[pet_id])
    veterinario = relationship("Cliente", foreign_keys=[veterinario_id])


class EvolucaoInternacao(BaseTenantModel):
    """Registro de sinais vitais durante internação (frequência horária/diária)."""
    __tablename__ = "vet_evolucoes_internacao"

    internacao_id = Column(Integer, ForeignKey("vet_internacoes.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    data_hora = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    temperatura = Column(Float, nullable=True)
    frequencia_cardiaca = Column(Integer, nullable=True)
    frequencia_respiratoria = Column(Integer, nullable=True)
    nivel_dor = Column(Integer, nullable=True)
    pressao_sistolica = Column(Integer, nullable=True)
    glicemia = Column(Float, nullable=True)
    peso = Column(Float, nullable=True)
    observacoes = Column(Text, nullable=True)

    # Relacionamentos
    internacao = relationship("InternacaoVet", back_populates="evolucoes")


# ==============================================================
# REGISTRO DE PESO (curva de peso ao longo do tempo)
# ==============================================================

class PesoRegistro(BaseTenantModel):
    """Histórico de peso do pet em cada consulta/pesagem avulsa."""
    __tablename__ = "vet_peso_registros"

    pet_id = Column(Integer, ForeignKey("pets.id"), nullable=False, index=True)
    consulta_id = Column(Integer, ForeignKey("vet_consultas.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    data = Column(Date, nullable=False, index=True)
    peso_kg = Column(Float, nullable=False)
    observacoes = Column(Text, nullable=True)

    # Relacionamentos
    pet = relationship("Pet", foreign_keys=[pet_id])


# ==============================================================
# FOTOS CLÍNICAS
# ==============================================================

class FotoClinica(BaseTenantModel):
    """Fotos clínicas vinculadas a uma consulta (dermatologia, feridas, pós-op)."""
    __tablename__ = "vet_fotos_clinicas"

    consulta_id = Column(Integer, ForeignKey("vet_consultas.id"), nullable=False, index=True)
    pet_id = Column(Integer, ForeignKey("pets.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    url = Column(String(500), nullable=False)
    nome_arquivo = Column(String(255), nullable=True)
    tipo = Column(String(50), nullable=True)  # dermatologia, ferida, pos_op, outro
    descricao = Column(Text, nullable=True)
    data_foto = Column(Date, nullable=False, server_default=func.now())

    # Relacionamentos
    consulta = relationship("ConsultaVet", back_populates="fotos_clinicas", foreign_keys=[consulta_id])


# ==============================================================
# PERFIL COMPORTAMENTAL DO PET
# ==============================================================

class PerfilComportamental(BaseTenantModel):
    """Perfil comportamental do pet — alimenta módulo de Banho e Tosa."""
    __tablename__ = "vet_perfil_comportamental"

    pet_id = Column(Integer, ForeignKey("pets.id"), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    temperamento = Column(String(50), nullable=True)         # calmo | agitado | ansioso | agressivo
    reacao_animais = Column(String(50), nullable=True)       # amigavel | indiferente | agressivo
    reacao_pessoas = Column(String(50), nullable=True)       # amigavel | timido | agressivo
    medo_secador = Column(String(50), nullable=True)         # sim | nao | moderado
    medo_tesoura = Column(String(50), nullable=True)
    aceita_focinheira = Column(String(50), nullable=True)    # sim | nao | com_resistencia
    comportamento_carro = Column(String(50), nullable=True)  # calmo | agitado | vomita
    observacoes = Column(Text, nullable=True)

    # Relacionamentos
    pet = relationship("Pet", foreign_keys=[pet_id])


# ==============================================================
# VÍNCULO ENTRE TENANTS (MULTI-TENANT PARCEIRO)
# ==============================================================

class VetPartnerLink(Base):
    """
    Vínculo entre o tenant da loja (empresa_tenant_id) e o tenant do
    veterinário parceiro (vet_tenant_id).

    tipo_relacao:
      'parceiro'   — veterinário tem tenant próprio, financeiro separado
      'funcionario' — veterinário trabalha dentro do mesmo tenant da loja

    Não herda BaseTenantModel pois não pertence a um tenant específico.
    """
    __tablename__ = "vet_partner_link"

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vet_tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo_relacao = Column(
        String(20),
        nullable=False,
        default="parceiro",
        server_default="parceiro",
    )  # 'parceiro' | 'funcionario'
    comissao_empresa_pct = Column(Numeric(5, 2), nullable=True)  # ex: 20.00
    ativo = Column(Boolean, nullable=False, default=True, server_default="true")
    criado_em = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
