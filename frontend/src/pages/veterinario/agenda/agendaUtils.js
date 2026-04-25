export const STATUS_COLOR = {
  agendado: "border-l-sky-300 bg-sky-50",
  confirmado: "border-l-emerald-300 bg-emerald-50",
  aguardando: "border-l-yellow-400 bg-yellow-50",
  em_atendimento: "border-l-blue-400 bg-blue-50",
  finalizado: "border-l-green-400 bg-green-50",
  cancelado: "border-l-gray-300 bg-gray-50",
};

export const STATUS_BADGE = {
  agendado: "bg-sky-100 text-sky-800",
  confirmado: "bg-emerald-100 text-emerald-800",
  aguardando: "bg-yellow-100 text-yellow-800",
  em_atendimento: "bg-blue-100 text-blue-800",
  finalizado: "bg-green-100 text-green-700",
  cancelado: "bg-gray-100 text-gray-500",
};

export const STATUS_LABEL = {
  agendado: "Agendado",
  confirmado: "Confirmado",
  aguardando: "Aguardando",
  em_atendimento: "Em atendimento",
  finalizado: "Finalizado",
  cancelado: "Cancelado",
};

export const TIPO_OPTIONS = [
  { value: "consulta", label: "Consulta", hint: "Abre o prontuario e inicia o atendimento clinico." },
  { value: "retorno", label: "Retorno", hint: "Continua a avaliacao de uma consulta anterior." },
  { value: "vacina", label: "Vacina", hint: "Abre o registro de vacinacao do pet ja selecionado." },
  { value: "exame", label: "Exame", hint: "Abre a solicitacao/registro de exame para o pet." },
];

export const TIPO_LABEL = {
  consulta: "Consulta",
  retorno: "Retorno",
  vacina: "Vacina",
  exame: "Exame",
};

export const TIPO_BADGE = {
  consulta: "bg-blue-100 text-blue-700",
  retorno: "bg-indigo-100 text-indigo-700",
  vacina: "bg-orange-100 text-orange-700",
  exame: "bg-violet-100 text-violet-700",
};

export const TIPO_ACAO = {
  consulta: "Iniciar consulta",
  retorno: "Iniciar retorno",
  vacina: "Abrir vacina",
  exame: "Abrir exame",
};

export const FORM_NOVO_INICIAL = {
  pet_id: "",
  veterinario_id: "",
  consultorio_id: "",
  tipo: "consulta",
  data: "",
  hora: "",
  motivo: "",
  emergencia: false,
};

export function isoDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function addDias(d, n) {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}

export function inicioMes(d) {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

export function fimMes(d) {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0);
}

export function inicioDaGradeMensal(d) {
  const primeiro = inicioMes(d);
  return addDias(primeiro, -primeiro.getDay());
}

export function gerarHorariosBase() {
  const horarios = [];
  for (let hora = 8; hora <= 18; hora += 1) {
    for (let minuto = 0; minuto < 60; minuto += 30) {
      if (hora === 18 && minuto > 0) continue;
      horarios.push(`${String(hora).padStart(2, "0")}:${String(minuto).padStart(2, "0")}`);
    }
  }
  return horarios;
}

export const HORARIOS_BASE = gerarHorariosBase();

export function normalizarTipoAgendamento(tipo) {
  return TIPO_LABEL[tipo] ? tipo : "consulta";
}
