import AutocompleteSelect from "../ui/AutocompleteSelect";

export function getCategoriaProdutoLabel(categoria) {
  if (!categoria) return "";
  if (categoria.nomeFormatado) return categoria.nomeFormatado;
  return `${categoria.categoria_pai_id ? "-> " : ""}${categoria.nome || ""}`;
}

export function getCategoriaProdutoSearchText(categoria) {
  return [categoria?.nome, categoria?.nomeFormatado, categoria?.descricao]
    .filter(Boolean)
    .join(" ");
}

export function getMarcaProdutoLabel(marca) {
  return marca?.nome || "";
}

export function CategoriaProdutoSelector({
  categorias = [],
  emptyLabel = "Nenhuma categoria encontrada",
  placeholder = "Todas as categorias",
  searchPlaceholder = "Buscar categoria...",
  ...props
}) {
  return (
    <AutocompleteSelect
      emptyLabel={emptyLabel}
      getOptionLabel={getCategoriaProdutoLabel}
      getOptionSearchText={getCategoriaProdutoSearchText}
      options={categorias}
      placeholder={placeholder}
      searchPlaceholder={searchPlaceholder}
      {...props}
    />
  );
}

export function MarcaProdutoSelector({
  emptyLabel = "Nenhuma marca encontrada",
  marcas = [],
  placeholder = "Todas as marcas",
  searchPlaceholder = "Buscar marca...",
  ...props
}) {
  return (
    <AutocompleteSelect
      emptyLabel={emptyLabel}
      getOptionLabel={getMarcaProdutoLabel}
      options={marcas}
      placeholder={placeholder}
      searchPlaceholder={searchPlaceholder}
      {...props}
    />
  );
}
