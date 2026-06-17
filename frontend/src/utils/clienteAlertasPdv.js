const VALID_PRIORITIES = new Set(["aviso", "importante", "info"]);

function cleanText(value, maxLength) {
  const text = String(value || "").trim();
  return text.length > maxLength ? text.slice(0, maxLength).trim() : text;
}

function normalizePriority(value) {
  const prioridade = cleanText(value || "aviso", 20).toLowerCase();
  return VALID_PRIORITIES.has(prioridade) ? prioridade : "aviso";
}

function normalizeActive(value) {
  if (typeof value === "boolean") return value;
  if (typeof value === "string") {
    return !["0", "false", "nao", "não", "no"].includes(value.trim().toLowerCase());
  }
  return value !== false;
}

export function buildEmptyClienteAlertaPdv() {
  return {
    titulo: "",
    mensagem: "",
    prioridade: "aviso",
    ativo: true,
  };
}

export function normalizeClienteAlertasPdv(value) {
  const source = Array.isArray(value) ? value : [];

  return source
    .filter((item) => item && typeof item === "object")
    .map((item) => {
      const titulo = cleanText(item.titulo || item.tag || item.label, 80);
      const mensagem = cleanText(item.mensagem || item.observacao || item.descricao, 500);

      if (!titulo && !mensagem) return null;

      return {
        titulo: titulo || "Observacao",
        mensagem,
        prioridade: normalizePriority(item.prioridade),
        ativo: normalizeActive(item.ativo ?? true),
      };
    })
    .filter(Boolean);
}

export function getClienteAlertasPdvAtivos(cliente) {
  return normalizeClienteAlertasPdv(cliente?.alertas_pdv).filter((alerta) => alerta.ativo);
}

export function clienteTemAlertasPdv(cliente) {
  return getClienteAlertasPdvAtivos(cliente).length > 0;
}
