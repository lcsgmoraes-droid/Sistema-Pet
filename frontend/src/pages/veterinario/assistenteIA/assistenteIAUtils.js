export const assistenteIaCss = {
  input:
    "w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-300",
  select:
    "w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-cyan-300",
  textarea:
    "w-full border border-gray-200 rounded-lg px-3 py-2 text-sm min-h-[90px] focus:outline-none focus:ring-2 focus:ring-cyan-300",
};

export const perguntasRapidasAssistenteIA = [
  {
    label: "Interação de medicamentos",
    texto: "pode associar amoxicilina com prednisolona?",
  },
  {
    label: "Calcular dose",
    texto: "calcule a dose de amoxicilina por mg/kg",
  },
  {
    label: "Hipóteses por sintomas",
    texto: "pelos sintomas de vômito, apatia e febre, quais as principais possibilidades?",
  },
  {
    label: "Checklist diagnóstico",
    texto: "o que mais devo olhar para fechar diagnóstico?",
  },
];

export function criarIdMensagemLocal() {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }
  return `msg-${Date.now()}-${Math.round(Math.random() * 100000)}`;
}

export function formatarLabelConsulta(consulta) {
  if (!consulta) return "Consulta";
  const pedacos = [`#${consulta.id}`];
  if (consulta.status) {
    pedacos.push(String(consulta.status).replaceAll("_", " "));
  }
  const dataRef = consulta.created_at || consulta.data_hora;
  if (dataRef) {
    pedacos.push(
      new Date(dataRef).toLocaleString("pt-BR", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      })
    );
  }
  if (consulta.motivo_consulta) {
    pedacos.push(consulta.motivo_consulta);
  }
  return pedacos.filter(Boolean).join(" • ");
}

export function getMemoriaAssistenteIABadge(memoriaAtiva) {
  if (memoriaAtiva === true) {
    return {
      className: "bg-emerald-100 text-emerald-700",
      label: "Memória ativa",
    };
  }
  if (memoriaAtiva === false) {
    return {
      className: "bg-red-100 text-red-700",
      label: "Memória indisponível",
    };
  }
  return {
    className: "bg-gray-100 text-gray-500",
    label: "Memória: verificando...",
  };
}
