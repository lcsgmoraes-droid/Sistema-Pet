import { normalizarTextoAutocomplete } from "../ui/autocompleteSelectUtils.js";

export function montarOpcoesCatalogoClinico({ medicamentos = [], procedimentos = [] } = {}) {
  const meds = medicamentos.map((item) => ({
    valor: `med:${item.id}`,
    tipo: "medicamento",
    label: item.nome || "Medicamento sem nome",
    meta: [item.principio_ativo, item.posologia_referencia, item.forma_farmaceutica].filter(Boolean).join(" - "),
    item,
  }));

  const procs = procedimentos.map((item) => ({
    valor: `proc:${item.id}`,
    tipo: "procedimento",
    label: item.nome || "Procedimento sem nome",
    meta: [item.descricao, item.duracao_minutos ? `${item.duracao_minutos} min` : null].filter(Boolean).join(" - "),
    item,
  }));

  return [...meds, ...procs];
}

export function filtrarCatalogoClinico(opcoes = [], termo = "", limite = 12) {
  const consulta = normalizarTextoAutocomplete(termo);
  if (!consulta || consulta.length < 2) return [];

  return opcoes
    .filter((opcao) => {
      const textoBusca = [
        opcao.label,
        opcao.meta,
        opcao.tipo,
        opcao.item?.nome_comercial,
        opcao.item?.principio_ativo,
        opcao.item?.descricao,
        opcao.item?.indicacoes,
      ]
        .filter(Boolean)
        .join(" ");

      return normalizarTextoAutocomplete(textoBusca).includes(consulta);
    })
    .slice(0, limite);
}
