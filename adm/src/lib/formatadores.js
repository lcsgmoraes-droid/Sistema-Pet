// Formatacao e regras de apresentacao do painel (sem React, para testar em Node).

export const ROTULO_DE_STATUS = {
  active: "Ativa",
  ativo: "Ativa",
  trial: "Em teste",
  inactive: "Inativa",
  suspended: "Suspensa",
};

export function rotuloDoStatus(status) {
  return ROTULO_DE_STATUS[String(status || "").toLowerCase()] || status || "Sem status";
}

export function formatarData(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("pt-BR");
}

export function formatarQuando(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

export function formatarReaisDeCentavos(centavos) {
  if (centavos === null || centavos === undefined) return "—";
  return (Number(centavos) / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

/** "Hoje", "Ontem", "Há 12 dias" ou "Nunca acessou". */
export function rotuloDoUltimoAcesso(iso, agora = new Date()) {
  if (!iso) return "Nunca acessou";
  const dias = Math.floor((agora.getTime() - new Date(iso).getTime()) / 86_400_000);
  if (dias <= 0) return "Hoje";
  if (dias === 1) return "Ontem";
  if (dias < 60) return `Há ${dias} dias`;
  return formatarData(iso);
}

export const ROTULO_DE_ORIGEM = {
  manual: "Ativado manualmente",
  assinatura: "Assinatura",
  plano: "Incluído no plano",
  trial: "Teste grátis",
};

export function origensEmTexto(origens = []) {
  return origens.map((origem) => ROTULO_DE_ORIGEM[origem] || origem).join(" · ");
}

/** Só o que foi ativado manualmente ou por assinatura pode ser desligado pelo painel. */
export function podeDesligar(modulo) {
  return !modulo.ativo || modulo.origens.some((o) => o === "manual" || o === "assinatura");
}

export function nomeDoModulo(codigo, catalogo = []) {
  return catalogo.find((item) => item.codigo === codigo)?.nome || codigo;
}

export function nomesDosModulosAtivos(loja, catalogo = []) {
  return (loja.modulos || [])
    .filter((modulo) => modulo.ativo)
    .map((modulo) => nomeDoModulo(modulo.codigo, catalogo))
    .sort((a, b) => a.localeCompare(b, "pt-BR"));
}

/** Ordena por agrupamento e depois por nome, para lojas do mesmo cliente ficarem juntas. */
export function ordenarLojas(lojas) {
  return [...lojas].sort((a, b) => {
    const grupoA = a.grupo?.nome || "￿";
    const grupoB = b.grupo?.nome || "￿";
    return grupoA.localeCompare(grupoB, "pt-BR") || a.nome.localeCompare(b.nome, "pt-BR");
  });
}

export function situacaoDoUsuario(usuario) {
  if (!usuario.ativo) {
    return usuario.acesso_ativo_na_loja ? "Usuário inativo" : "Sem acesso a esta loja";
  }
  return "Ativo";
}

export function totaisDasLojas(lojas) {
  return {
    lojas: lojas.length,
    usuarios: lojas.reduce((soma, loja) => soma + (loja.usuarios?.total || 0), 0),
    semUsuarioAtivo: lojas.filter((loja) => !(loja.usuarios?.ativos > 0)).length,
  };
}

const ROTULO_DE_CAMPO = {
  status: "Status da loja",
  plan: "Plano",
  billing_status: "Situação da cobrança",
  subscription_source: "Origem da assinatura",
  onboarding_owner_name: "Responsável pelo acompanhamento",
  onboarding_unblocked_on: "Data de desbloqueio",
  onboarding_next_contact_on: "Próximo contato",
  onboarding_satisfaction: "Satisfação inicial",
};

function valorLegivel(valor) {
  if (valor === null || valor === undefined || valor === "") return "—";
  return String(valor).charAt(0).toLocaleUpperCase("pt-BR") + String(valor).slice(1);
}

export function descreverAlteracao(item, catalogo = []) {
  const titulo =
    item.categoria === "modulo"
      ? `Módulo ${nomeDoModulo(item.campo, catalogo)}`
      : ROTULO_DE_CAMPO[item.campo] || item.campo;
  return { titulo, antes: valorLegivel(item.antes), depois: valorLegivel(item.depois) };
}

/** Dicas da senha nova, em tempo real (o servidor continua sendo quem decide). */
export function checarSenhaNova(nova, atual = "") {
  return [
    { ok: nova.length >= 12, texto: "Pelo menos 12 caracteres" },
    { ok: /[A-Za-z]/.test(nova) && /[\d\W_]/.test(nova), texto: "Letras e também números ou símbolos" },
    { ok: nova.length > 0 && nova !== atual, texto: "Diferente da senha atual" },
  ];
}
