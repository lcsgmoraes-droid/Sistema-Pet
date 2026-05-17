function criarParamsContexto(contextoConsultaParams) {
  if (!contextoConsultaParams) return null;

  const params = new URLSearchParams(contextoConsultaParams);
  const petId = params.get("pet_id") || params.get("novo_pet_id");
  if (!petId) return null;

  params.delete("pet_id");
  params.set("novo_pet_id", String(petId));
  return params;
}

function textoLimpo(valor) {
  return String(valor || "").trim();
}

function resumoClinico(form = {}) {
  return [form.diagnostico, form.tratamento, form.queixa_principal]
    .map(textoLimpo)
    .find(Boolean);
}

function limitarResumo(texto, limite = 80) {
  if (!texto || texto.length <= limite) return texto;
  return `${texto.slice(0, limite - 3).trim()}...`;
}

export function buildAgendarRetornoConsultaLink({
  contextoConsultaParams,
  form = {},
  consultaIdAtual,
} = {}) {
  const params = criarParamsContexto(contextoConsultaParams);
  if (!params) return null;

  if (consultaIdAtual && !params.get("consulta_id")) {
    params.set("consulta_id", String(consultaIdAtual));
  }

  const consultaOrigemId = consultaIdAtual || params.get("consulta_id");
  if (consultaOrigemId) {
    params.set("consulta_origem_id", String(consultaOrigemId));
  }

  const baseMotivo = limitarResumo(resumoClinico(form));
  params.set("abrir_novo", "1");
  params.set("tipo", "retorno");
  if (consultaOrigemId) {
    params.set("return_to", `/veterinario/consultas/${consultaOrigemId}?etapa=2`);
  }
  params.set(
    "motivo",
    baseMotivo
      ? `Retorno - ${baseMotivo}`
      : `Retorno da consulta #${consultaOrigemId || ""}`.trim()
  );

  return `/veterinario/agenda?${params.toString()}`;
}

export function buildInternacaoConsultaLink({
  contextoConsultaParams,
  form = {},
  consultaIdAtual,
} = {}) {
  const params = criarParamsContexto(contextoConsultaParams);
  if (!params) return null;

  const consultaId = consultaIdAtual || params.get("consulta_id");
  if (consultaId) {
    params.set("consulta_id", String(consultaId));
  }

  const baseMotivo = limitarResumo(resumoClinico(form));
  params.set("abrir_nova", "1");
  params.set(
    "motivo",
    baseMotivo && consultaId
      ? `Internacao apos consulta #${consultaId} - ${baseMotivo}`
      : baseMotivo || "Internacao apos consulta"
  );

  return `/veterinario/internacoes?${params.toString()}`;
}
