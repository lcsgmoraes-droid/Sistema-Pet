export function normalizarTextoAutocomplete(valor) {
  return String(valor || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("pt-BR");
}

export function filtrarOpcoesAutocomplete({
  termo,
  options = [],
  getOptionLabel = (option) => option?.label || option?.nome || "",
  getOptionMeta,
  getOptionSearchText,
  maxOptions = 30,
} = {}) {
  const consulta = normalizarTextoAutocomplete(termo);
  const base = consulta
    ? options.filter((option) => {
        const textoBusca =
          getOptionSearchText?.(option) ||
          [getOptionLabel(option), getOptionMeta?.(option)].filter(Boolean).join(" ");
        return normalizarTextoAutocomplete(textoBusca).includes(consulta);
      })
    : options;

  return base.slice(0, maxOptions);
}
