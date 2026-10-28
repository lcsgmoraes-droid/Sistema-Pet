// Regras de apresentação das telas de lojas do OPS (sem React, para testar em Node).

export function nomeDoModulo(codigo, info = {}) {
  return info[codigo]?.nome || codigo;
}

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

export function formatarData(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("pt-BR");
}

/** "há 3 dias", "hoje", "nunca acessou" — para a coluna de último acesso. */
export function rotuloDoUltimoAcesso(iso, agora = new Date()) {
  if (!iso) return "Nunca acessou";
  const dias = Math.floor((agora.getTime() - new Date(iso).getTime()) / 86_400_000);
  if (dias <= 0) return "Hoje";
  if (dias === 1) return "Ontem";
  if (dias < 60) return `Há ${dias} dias`;
  return formatarData(iso);
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

/** Nomes dos módulos ativos em ordem alfabética (para a coluna de módulos da lista). */
export function nomesDosModulosAtivos(loja, info = {}) {
  return modulosAtivos(loja)
    .map((codigo) => nomeDoModulo(codigo, info))
    .sort((a, b) => a.localeCompare(b, "pt-BR"));
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

/** Situação do usuário em palavras (nunca só cor). */
export function situacaoDoUsuario(usuario) {
  if (!usuario.ativo) {
    return usuario.acesso_ativo_na_loja ? "Usuário inativo" : "Sem acesso a esta loja";
  }
  return "Ativo";
}

/** Contadores para a barra de resumo da lista de lojas. */
export function totaisDasLojas(lojas) {
  return {
    lojas: lojas.length,
    usuarios: lojas.reduce((soma, loja) => soma + (loja.usuarios?.total || 0), 0),
    semUsuarioAtivo: lojas.filter((loja) => !(loja.usuarios?.ativos > 0)).length,
  };
}
