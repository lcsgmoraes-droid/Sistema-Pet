export const SITUACOES_ESTOQUE = {
  todos: { label: "Todos", cor: "border-slate-200 bg-slate-50 text-slate-800" },
  abaixo_minimo: { label: "Abaixo do mínimo", cor: "border-red-200 bg-red-50 text-red-800" },
  no_minimo: { label: "No mínimo", cor: "border-amber-200 bg-amber-50 text-amber-800" },
  dentro_limites: {
    label: "Dentro dos limites",
    cor: "border-emerald-200 bg-emerald-50 text-emerald-800",
  },
  acima_maximo: { label: "Acima do máximo", cor: "border-blue-200 bg-blue-50 text-blue-800" },
  sem_limites: { label: "Sem limites", cor: "border-slate-200 bg-slate-50 text-slate-700" },
  limites_invalidos: {
    label: "Revisar limites",
    cor: "border-orange-200 bg-orange-50 text-orange-800",
  },
};

export const FILTROS_INICIAIS = {
  busca: "",
  categoria_id: "",
  marca_id: "",
  fornecedor_id: "",
  situacao: "todos",
  saldo: "todos",
  ativo: "ativos",
  page: 1,
  page_size: 50,
};

export const formatarQuantidade = (valor) =>
  valor === null || valor === undefined
    ? "—"
    : Number(valor).toLocaleString("pt-BR", { maximumFractionDigits: 6 });

export function parametrosLimites(filtros) {
  return Object.fromEntries(Object.entries(filtros).filter(([, valor]) => valor !== ""));
}

export function montarPlanilhaLimites(itens) {
  const colunas = [
    ["Produto", "nome"],
    ["Código / SKU", "codigo"],
    ["Categoria", "categoria"],
    ["Marca", "marca"],
    ["Fornecedor principal", "fornecedor"],
    ["Unidade", "unidade"],
    ["Saldo atual", "estoque_atual"],
    ["Mínimo", "estoque_minimo"],
    ["Máximo", "estoque_maximo"],
    ["Situação", "situacao"],
    ["Falta até o mínimo", "falta_minimo"],
    ["Excesso sobre o máximo", "excesso_maximo"],
  ];
  const cabecalho = colunas.map(([titulo]) => ({
    value: titulo,
    type: String,
    fontWeight: "bold",
    backgroundColor: "#DBEAFE",
  }));
  const linhas = itens.map((item) =>
    colunas.map(([, chave]) => {
      const valor = chave === "situacao" ? SITUACOES_ESTOQUE[item.situacao].label : item[chave];
      return typeof valor === "number"
        ? { value: valor, type: Number, format: "#,##0.######" }
        : { value: valor ?? "", type: String };
    }),
  );
  return [cabecalho, ...linhas];
}
