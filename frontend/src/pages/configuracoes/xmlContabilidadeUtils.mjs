const FUSO = "America/Sao_Paulo";

export const CONFIG_CONTABILIDADE_INICIAL = {
  email_contador: "",
  envio_automatico: false,
  envio_mensal: false,
  dia_envio_mensal: 1,
  hora_envio_mensal: "08:00",
  smtp_configurado: false,
};

export function normalizarConfigContabilidade(dados) {
  return {
    ...CONFIG_CONTABILIDADE_INICIAL,
    ...dados,
    email_contador: dados?.email_contador || "",
  };
}

export function payloadConfigContabilidade(config) {
  return {
    email_contador: config.email_contador.trim(),
    envio_automatico: config.envio_automatico,
    envio_mensal: config.envio_mensal,
    dia_envio_mensal: Number(config.dia_envio_mensal),
    hora_envio_mensal: config.hora_envio_mensal,
  };
}

export function periodoMesAnterior(agora = new Date()) {
  const partes = new Intl.DateTimeFormat("en-CA", {
    timeZone: FUSO,
    year: "numeric",
    month: "2-digit",
  }).formatToParts(agora);
  const ano = Number(partes.find((parte) => parte.type === "year").value);
  const mes = Number(partes.find((parte) => parte.type === "month").value);
  return {
    inicio: new Date(Date.UTC(ano, mes - 2, 1)).toISOString().slice(0, 10),
    fim: new Date(Date.UTC(ano, mes - 1, 0)).toISOString().slice(0, 10),
  };
}

function dataValida(valor) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(valor || "")) return false;
  const data = new Date(`${valor}T12:00:00Z`);
  return !Number.isNaN(data.getTime()) && data.toISOString().slice(0, 10) === valor;
}

export function erroPeriodo({ inicio, fim }) {
  if (!dataValida(inicio) || !dataValida(fim)) return "Escolha a data inicial e a final.";
  if (inicio > fim) return "A data final deve ser igual ou posterior à inicial.";
  return "";
}

export function formatarDataContabilidade(valor, incluirHora = false) {
  if (!valor) return "—";
  const normalizado = /^\d{4}-\d{2}-\d{2}$/.test(valor) ? `${valor}T12:00:00-03:00` : valor;
  const data = new Date(normalizado);
  if (Number.isNaN(data.getTime())) return "—";
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: FUSO,
    dateStyle: "short",
    ...(incluirHora ? { timeStyle: "short" } : {}),
  }).format(data);
}

export async function mensagemErroContabilidade(erro, padrao) {
  let dados = erro.response?.data;
  if (typeof Blob !== "undefined" && dados instanceof Blob) {
    try {
      dados = JSON.parse(await dados.text());
    } catch {
      dados = null;
    }
  }
  return typeof dados?.detail === "string" ? dados.detail : padrao;
}
