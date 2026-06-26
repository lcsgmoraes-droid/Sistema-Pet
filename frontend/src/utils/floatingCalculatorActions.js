export const FLOATING_CALCULATOR_ACTIONS = [
  {
    id: "calcular-racao",
    label: "Calcular Racao",
  },
  {
    id: "comparar-preco",
    label: "Comparar Preco",
  },
];

export function getFloatingCalculatorActions() {
  return FLOATING_CALCULATOR_ACTIONS.map((action) => ({ ...action }));
}
