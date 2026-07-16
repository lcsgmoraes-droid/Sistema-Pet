export const LAYOUT_MENU_GROUPS = [
  {
    label: "Visão geral",
    paths: ["/dashboard", "/lembretes"],
  },
  {
    label: "Atendimento",
    paths: ["/clientes", "/pets", "/veterinario", "/banho-tosa", "/calculadora-racao"],
  },
  {
    label: "Vendas e relacionamento",
    paths: ["/pdv", "/ecommerce", "/campanhas", "/vendas/bling", "/entregas"],
  },
  {
    label: "Estoque e suprimentos",
    paths: ["/produtos", "/compras", "/notas-fiscais/saida"],
  },
  {
    label: "Financeiro",
    paths: ["/financeiro", "/comissoes"],
  },
  {
    label: "Gestão",
    paths: ["/cadastros", "/rh", "/ia", "/admin", "/configuracoes"],
  },
];

const MENU_POSITION_BY_PATH = new Map(
  LAYOUT_MENU_GROUPS.flatMap((group, groupIndex) =>
    group.paths.map((path, itemIndex) => [
      path,
      {
        section: group.label,
        position: groupIndex * 100 + itemIndex,
      },
    ]),
  ),
);

export function applyLayoutMenuStructure(items = []) {
  return items
    .map((item) => ({
      ...item,
      section: MENU_POSITION_BY_PATH.get(item.path)?.section || "Outros",
    }))
    .sort(
      (left, right) =>
        (MENU_POSITION_BY_PATH.get(left.path)?.position ?? Number.MAX_SAFE_INTEGER) -
        (MENU_POSITION_BY_PATH.get(right.path)?.position ?? Number.MAX_SAFE_INTEGER),
    );
}
