import { hojeIso } from "./consultaFormUtils";

export function criarConsultaFormInicial() {
  return {
    pet_id: "",
    veterinario_id: "",
    motivo_consulta: "",
    peso_kg: "",
    temperatura: "",
    freq_cardiaca: "",
    freq_respiratoria: "",
    tpc: "",
    mucosa: "",
    estado_hidratacao: "",
    nivel_consciencia: "",
    nivel_dor: "",
    exame_fisico: "",
    historico_clinico: "",
    diagnostico: "",
    prognostico: "",
    tratamento: "",
    observacoes: "",
    retorno_em_dias: "",
    prescricao_itens: [],
    procedimentos_realizados: [],
  };
}

export function criarNovoExameFormInicial() {
  return {
    tipo: "laboratorial",
    nome: "",
    data_solicitacao: hojeIso(),
    laboratorio: "",
    observacoes: "",
  };
}

export function criarCalculadoraFormInicial() {
  return {
    medicamento_id: "",
    peso_kg: "",
    dose_mg_kg: "",
    frequencia_horas: "12",
    dias: "7",
  };
}

export function criarInsumoRapidoFormInicial() {
  return {
    quantidade_utilizada: "1",
    quantidade_desperdicio: "",
    observacoes: "",
  };
}

export function criarPrescricaoItemInicial() {
  return {
    medicamento_id: "",
    nome: "",
    principio_ativo: "",
    dose_mg: "",
    unidade: "mg",
    dose_minima_mg_kg: "",
    dose_maxima_mg_kg: "",
    frequencia: "",
    duracao_dias: "",
    via: "oral",
    instrucoes: "",
  };
}

export function criarProcedimentoRealizadoInicial() {
  return {
    catalogo_id: "",
    nome: "",
    descricao: "",
    valor: "",
    observacoes: "",
    baixar_estoque: true,
  };
}
