"""Schemas Pydantic do modulo veterinario."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AgendamentoCreate(BaseModel):
    pet_id: int
    cliente_id: Optional[int] = None
    veterinario_id: Optional[int] = None
    consultorio_id: Optional[int] = None
    data_hora: datetime
    duracao_minutos: int = 30
    tipo: str = "consulta"
    motivo: Optional[str] = None
    is_emergencia: bool = False
    sintoma_emergencia: Optional[str] = None
    observacoes: Optional[str] = None


class AgendamentoUpdate(BaseModel):
    pet_id: Optional[int] = None
    cliente_id: Optional[int] = None
    veterinario_id: Optional[int] = None
    consultorio_id: Optional[int] = None
    data_hora: Optional[datetime] = None
    duracao_minutos: Optional[int] = None
    tipo: Optional[str] = None
    motivo: Optional[str] = None
    status: Optional[str] = None
    is_emergencia: Optional[bool] = None
    observacoes: Optional[str] = None
    pretriagem: Optional[dict] = None


class AgendamentoResponse(BaseModel):
    id: int
    pet_id: int
    cliente_id: int
    veterinario_id: Optional[int]
    consultorio_id: Optional[int]
    data_hora: datetime
    duracao_minutos: int
    tipo: str
    motivo: Optional[str]
    status: str
    is_emergencia: bool
    consulta_id: Optional[int]
    observacoes: Optional[str]
    pet_nome: Optional[str] = None
    cliente_nome: Optional[str] = None
    veterinario_nome: Optional[str] = None
    consultorio_nome: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class VeterinarioSimples(BaseModel):
    id: int
    nome: str
    crmv: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None

    class Config:
        from_attributes = True


class ConsultorioCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=120)
    descricao: Optional[str] = None
    ordem: Optional[int] = Field(default=None, ge=1, le=999)


class ConsultorioUpdate(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=1, max_length=120)
    descricao: Optional[str] = None
    ordem: Optional[int] = Field(default=None, ge=1, le=999)
    ativo: Optional[bool] = None


class ConsultorioResponse(BaseModel):
    id: int
    nome: str
    descricao: Optional[str] = None
    ordem: int
    ativo: bool

    class Config:
        from_attributes = True


class ConsultaCreate(BaseModel):
    pet_id: int
    cliente_id: int
    veterinario_id: Optional[int] = None
    tipo: str = "consulta"
    agendamento_id: Optional[int] = None
    queixa_principal: Optional[str] = None


class ConsultaUpdate(BaseModel):
    queixa_principal: Optional[str] = None
    historia_clinica: Optional[str] = None
    peso_consulta: Optional[float] = None
    temperatura: Optional[float] = None
    frequencia_cardiaca: Optional[int] = None
    frequencia_respiratoria: Optional[int] = None
    tpc: Optional[str] = None
    mucosas: Optional[str] = None
    hidratacao: Optional[str] = None
    nivel_dor: Optional[int] = None
    saturacao_o2: Optional[float] = None
    pressao_sistolica: Optional[int] = None
    pressao_diastolica: Optional[int] = None
    glicemia: Optional[float] = None
    exame_fisico: Optional[str] = None
    hipotese_diagnostica: Optional[str] = None
    diagnostico: Optional[str] = None
    diagnostico_simples: Optional[str] = None
    conduta: Optional[str] = None
    retorno_em_dias: Optional[int] = None
    data_retorno: Optional[date] = None
    asa_score: Optional[int] = None
    asa_justificativa: Optional[str] = None
    observacoes_internas: Optional[str] = None
    observacoes_tutor: Optional[str] = None
    veterinario_id: Optional[int] = None


class ConsultaResponse(BaseModel):
    id: int
    pet_id: int
    cliente_id: int
    veterinario_id: Optional[int]
    tipo: str
    status: str
    queixa_principal: Optional[str]
    historia_clinica: Optional[str]
    peso_consulta: Optional[float]
    temperatura: Optional[float]
    frequencia_cardiaca: Optional[int]
    frequencia_respiratoria: Optional[int]
    tpc: Optional[str]
    mucosas: Optional[str]
    hidratacao: Optional[str]
    nivel_dor: Optional[int]
    saturacao_o2: Optional[float]
    pressao_sistolica: Optional[int]
    pressao_diastolica: Optional[int]
    glicemia: Optional[float]
    exame_fisico: Optional[str]
    hipotese_diagnostica: Optional[str]
    diagnostico: Optional[str]
    diagnostico_simples: Optional[str]
    conduta: Optional[str]
    retorno_em_dias: Optional[int]
    data_retorno: Optional[date]
    asa_score: Optional[int]
    asa_justificativa: Optional[str]
    observacoes_internas: Optional[str]
    observacoes_tutor: Optional[str]
    hash_prontuario: Optional[str]
    finalizado_em: Optional[datetime]
    inicio_atendimento: Optional[datetime]
    fim_atendimento: Optional[datetime]
    pet_nome: Optional[str] = None
    cliente_nome: Optional[str] = None
    veterinario_nome: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ItemPrescricaoIn(BaseModel):
    nome_medicamento: str
    concentracao: Optional[str] = None
    forma_farmaceutica: Optional[str] = None
    quantidade: Optional[str] = None
    posologia: str
    via_administracao: Optional[str] = None
    duracao_dias: Optional[int] = None
    medicamento_catalogo_id: Optional[int] = None


class PrescricaoCreate(BaseModel):
    consulta_id: int
    pet_id: int
    veterinario_id: Optional[int] = None
    tipo_receituario: str = "simples"
    observacoes: Optional[str] = None
    itens: List[ItemPrescricaoIn]


class PrescricaoResponse(BaseModel):
    id: int
    consulta_id: int
    pet_id: int
    veterinario_id: Optional[int]
    numero: Optional[str]
    data_emissao: date
    tipo_receituario: str
    observacoes: Optional[str]
    hash_receita: Optional[str]
    itens: List[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class VacinaCreate(BaseModel):
    pet_id: int
    consulta_id: Optional[int] = None
    agendamento_id: Optional[int] = None
    veterinario_id: Optional[int] = None
    protocolo_id: Optional[int] = None
    nome_vacina: str
    fabricante: Optional[str] = None
    lote: Optional[str] = None
    data_aplicacao: date
    data_proxima_dose: Optional[date] = None
    numero_dose: int = 1
    via_administracao: Optional[str] = None
    observacoes: Optional[str] = None


class VacinaResponse(BaseModel):
    id: int
    pet_id: int
    consulta_id: Optional[int]
    nome_vacina: str
    fabricante: Optional[str]
    lote: Optional[str]
    data_aplicacao: date
    data_proxima_dose: Optional[date]
    numero_dose: int
    via_administracao: Optional[str]
    observacoes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ExameCreate(BaseModel):
    pet_id: int
    consulta_id: Optional[int] = None
    agendamento_id: Optional[int] = None
    tipo: str = "laboratorial"
    nome: str
    data_solicitacao: Optional[date] = None
    laboratorio: Optional[str] = None
    observacoes: Optional[str] = None


class ExameUpdate(BaseModel):
    data_resultado: Optional[date] = None
    status: Optional[str] = None
    resultado_texto: Optional[str] = None
    resultado_json: Optional[dict] = None
    interpretacao: Optional[str] = None
    interpretacao_ia: Optional[str] = None
    interpretacao_ia_resumo: Optional[str] = None
    interpretacao_ia_confianca: Optional[float] = None
    interpretacao_ia_alertas: Optional[list] = None
    interpretacao_ia_payload: Optional[dict] = None
    arquivo_url: Optional[str] = None
    arquivo_nome: Optional[str] = None
    observacoes: Optional[str] = None


class ExameResponse(BaseModel):
    id: int
    pet_id: int
    consulta_id: Optional[int]
    tipo: str
    nome: str
    data_solicitacao: Optional[date]
    data_resultado: Optional[date]
    status: str
    laboratorio: Optional[str]
    resultado_texto: Optional[str]
    resultado_json: Optional[dict]
    interpretacao: Optional[str]
    interpretacao_ia: Optional[str]
    interpretacao_ia_resumo: Optional[str]
    interpretacao_ia_confianca: Optional[float]
    interpretacao_ia_alertas: Optional[list]
    interpretacao_ia_payload: Optional[dict]
    arquivo_url: Optional[str]
    arquivo_nome: Optional[str]
    observacoes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ProcedimentoCreate(BaseModel):
    consulta_id: int
    catalogo_id: Optional[int] = None
    nome: str
    descricao: Optional[str] = None
    valor: Optional[float] = None
    realizado: bool = True
    observacoes: Optional[str] = None
    insumos: list[dict] = Field(default_factory=list)
    baixar_estoque: bool = True


class ProcedimentoResponse(BaseModel):
    id: int
    consulta_id: int
    catalogo_id: Optional[int]
    nome: str
    descricao: Optional[str]
    valor: Optional[float]
    valor_cobrado: float = 0
    realizado: bool
    observacoes: Optional[str]
    insumos: list[dict] = Field(default_factory=list)
    custo_total: float = 0
    margem_valor: float = 0
    margem_percentual: float = 0
    modo_operacional: str = "funcionario"
    comissao_empresa_pct: float = 0
    repasse_empresa_valor: float = 0
    receita_tenant_valor: float = 0
    entrada_empresa_valor: float = 0
    estoque_baixado: bool = False
    estoque_movimentacao_ids: list[int] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True


class CatalogoCreate(BaseModel):
    nome: str
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    valor_padrao: Optional[float] = None
    duracao_minutos: Optional[int] = None
    requer_anestesia: bool = False
    observacoes: Optional[str] = None
    insumos: list[dict] = Field(default_factory=list)


class CatalogoUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    valor_padrao: Optional[float] = None
    duracao_minutos: Optional[int] = None
    requer_anestesia: Optional[bool] = None
    observacoes: Optional[str] = None
    insumos: Optional[list[dict]] = None


class CatalogoResponse(BaseModel):
    id: int
    nome: str
    descricao: Optional[str]
    categoria: Optional[str]
    valor_padrao: Optional[float]
    duracao_minutos: Optional[int]
    requer_anestesia: bool
    observacoes: Optional[str]
    insumos: list[dict] = Field(default_factory=list)
    custo_estimado: float = 0
    margem_estimada: float = 0
    margem_percentual_estimada: float = 0
    modo_operacional: str = "funcionario"
    comissao_empresa_pct: float = 0
    repasse_empresa_estimado: float = 0
    receita_tenant_estimada: float = 0
    ativo: bool

    class Config:
        from_attributes = True


class MedicamentoCreate(BaseModel):
    nome: str
    nome_comercial: Optional[str] = None
    principio_ativo: Optional[str] = None
    fabricante: Optional[str] = None
    forma_farmaceutica: Optional[str] = None
    concentracao: Optional[str] = None
    especies_indicadas: Optional[list] = None
    indicacoes: Optional[str] = None
    contraindicacoes: Optional[str] = None
    interacoes: Optional[str] = None
    posologia_referencia: Optional[str] = None
    dose_min_mgkg: Optional[float] = None
    dose_max_mgkg: Optional[float] = None
    eh_antibiotico: bool = False
    eh_controlado: bool = False
    observacoes: Optional[str] = None


class MedicamentoUpdate(BaseModel):
    nome: Optional[str] = None
    nome_comercial: Optional[str] = None
    principio_ativo: Optional[str] = None
    fabricante: Optional[str] = None
    forma_farmaceutica: Optional[str] = None
    concentracao: Optional[str] = None
    especies_indicadas: Optional[list] = None
    indicacoes: Optional[str] = None
    contraindicacoes: Optional[str] = None
    interacoes: Optional[str] = None
    posologia_referencia: Optional[str] = None
    dose_min_mgkg: Optional[float] = None
    dose_max_mgkg: Optional[float] = None
    eh_antibiotico: Optional[bool] = None
    eh_controlado: Optional[bool] = None
    observacoes: Optional[str] = None


class ProtocoloVacinaUpdate(BaseModel):
    nome: Optional[str] = None
    especie: Optional[str] = None
    dose_inicial_semanas: Optional[int] = None
    reforco_anual: Optional[bool] = None
    numero_doses_serie: Optional[int] = None
    intervalo_doses_dias: Optional[int] = None
    observacoes: Optional[str] = None


class InternacaoCreate(BaseModel):
    pet_id: int
    consulta_id: Optional[int] = None
    veterinario_id: Optional[int] = None
    motivo: Optional[str] = None
    motivo_internacao: Optional[str] = None
    box: Optional[str] = None
    baia_numero: Optional[str] = None
    data_entrada: Optional[datetime] = None


class EvolucaoCreate(BaseModel):
    temperatura: Optional[float] = None
    frequencia_cardiaca: Optional[int] = None
    frequencia_respiratoria: Optional[int] = None
    freq_cardiaca: Optional[int] = None
    freq_respiratoria: Optional[int] = None
    nivel_dor: Optional[int] = None
    pressao_sistolica: Optional[int] = None
    glicemia: Optional[float] = None
    peso: Optional[float] = None
    observacoes: Optional[str] = None


class ProcedimentoInternacaoCreate(BaseModel):
    horario_agendado: Optional[datetime] = None
    medicamento: str
    dose: Optional[str] = None
    via: Optional[str] = None
    quantidade_prevista: Optional[float] = None
    quantidade_executada: Optional[float] = None
    quantidade_desperdicio: Optional[float] = None
    unidade_quantidade: Optional[str] = None
    tipo_registro: Optional[str] = "procedimento"
    insumos: list[dict] = Field(default_factory=list)
    observacoes_agenda: Optional[str] = None
    executado_por: Optional[str] = None
    horario_execucao: Optional[datetime] = None
    observacao_execucao: Optional[str] = None
    status: Optional[str] = "concluido"


class InternacaoConfigUpdate(BaseModel):
    total_baias: int = Field(..., ge=1, le=200)


class ProcedimentoAgendaInternacaoCreate(BaseModel):
    horario_agendado: datetime
    medicamento: str
    dose: Optional[str] = None
    via: Optional[str] = None
    quantidade_prevista: Optional[float] = None
    unidade_quantidade: Optional[str] = None
    lembrete_min: Optional[int] = Field(30, ge=0, le=1440)
    observacoes_agenda: Optional[str] = None


class ProcedimentoAgendaInternacaoConcluir(BaseModel):
    executado_por: str
    horario_execucao: datetime
    observacao_execucao: Optional[str] = None
    quantidade_prevista: Optional[float] = None
    quantidade_executada: Optional[float] = None
    quantidade_desperdicio: Optional[float] = None
    unidade_quantidade: Optional[str] = None


class PerfilComportamentalIn(BaseModel):
    temperamento: Optional[str] = None
    reacao_animais: Optional[str] = None
    reacao_pessoas: Optional[str] = None
    medo_secador: Optional[str] = None
    medo_tesoura: Optional[str] = None
    aceita_focinheira: Optional[str] = None
    comportamento_carro: Optional[str] = None
    observacoes: Optional[str] = None


class PartnerLinkCreate(BaseModel):
    vet_tenant_id: str
    tipo_relacao: str = "parceiro"
    comissao_empresa_pct: Optional[float] = None


class PartnerLinkUpdate(BaseModel):
    tipo_relacao: Optional[str] = None
    comissao_empresa_pct: Optional[float] = None
    ativo: Optional[bool] = None


class PartnerLinkResponse(BaseModel):
    id: int
    empresa_tenant_id: str
    vet_tenant_id: str
    tipo_relacao: str
    comissao_empresa_pct: Optional[float]
    ativo: bool
    criado_em: datetime
    vet_tenant_nome: Optional[str] = None
    empresa_tenant_nome: Optional[str] = None

    class Config:
        from_attributes = True


class ExameChatPayload(BaseModel):
    pergunta: str


class VetAssistenteIAPayload(BaseModel):
    mensagem: str
    modo: str = "livre"
    conversa_id: Optional[int] = None
    salvar_historico: bool = True
    pet_id: Optional[int] = None
    consulta_id: Optional[int] = None
    exame_id: Optional[int] = None
    medicamento_1: Optional[str] = None
    medicamento_2: Optional[str] = None
    peso_kg: Optional[float] = None
    especie: Optional[str] = None


class VetMensagemFeedbackPayload(BaseModel):
    util: bool
    nota: Optional[int] = Field(default=None, ge=1, le=5)
    comentario: Optional[str] = None
