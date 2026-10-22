// Regras de apresentação da tela "Lojas e módulos" do OPS (sem React, para testar em Node).

export function nomeDoModulo(codigo, info = {}) {
  return info[codigo]?.nome || codigo;
}

/**
 * Agrupa as lojas por agrupamento (grupo comercial), em ordem alfabética.
 * Loja sem grupo cai em "Sem agrupamento" no fim.
 */
export function agruparPorGrupo(lojas) {
  const grupos = new Map();
  for (const loja of lojas) {
    const chave = loja.grupo ? `g${loja.grupo.id}` : "sem-grupo";
    if (!grupos.has(chave)) {
      grupos.set(chave, {
        chave,
        nome: loja.grupo ? loja.grupo.nome : "Sem agrupamento",
        semGrupo: !loja.grupo,
        lojas: [],
      });
    }
    grupos.get(chave).lojas.push(loja);
  }
  return [...grupos.values()].sort((a, b) => {
    if (a.semGrupo !== b.semGrupo) return a.semGrupo ? 1 : -1;
    return a.nome.localeCompare(b.nome, "pt-BR");
  });
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

export function formatarQuando(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "medium" });
}

function valorLegivel(valor) {
  if (valor === null || valor === undefined || valor === "") return "—";
  return String(valor).charAt(0).toLocaleUpperCase("pt-BR") + String(valor).slice(1);
}

/** Texto de uma linha do histórico: { titulo, antes, depois }. */
export function descreverAlteracao(item, infoDeModulos = {}) {
  const titulo =
    item.categoria === "modulo"
      ? `Módulo ${nomeDoModulo(item.campo, infoDeModulos)}`
      : ROTULO_DE_CAMPO[item.campo] || item.campo;
  return { titulo, antes: valorLegivel(item.antes), depois: valorLegivel(item.depois) };
}

export function modulosAtivos(loja) {
  return (loja.modulos || []).filter((modulo) => modulo.ativo).map((modulo) => modulo.codigo);
}

/** Módulos ativos que vêm do plano ou do teste grátis (não se desligam na tela). */
export function modulosDoPlano(loja) {
  return (loja.modulos || [])
    .filter(
      (modulo) =>
        modulo.ativo &&
        !modulo.origens.includes("manual") &&
        !modulo.origens.includes("assinatura"),
    )
    .map((modulo) => modulo.codigo);
}

/** Qual módulo mudou entre a seleção antiga e a nova: { modulo, ativar } ou null. */
export function modulosAlterados(antes, depois) {
  const antigos = new Set(antes);
  const novos = new Set(depois);
  for (const modulo of novos) if (!antigos.has(modulo)) return { modulo, ativar: true };
  for (const modulo of antigos) if (!novos.has(modulo)) return { modulo, ativar: false };
  return null;
}
