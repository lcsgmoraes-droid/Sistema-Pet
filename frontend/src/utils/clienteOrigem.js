export const ORIGENS_CLIENTE = [
  { value: "loja_fisica", label: "Loja Física" },
  { value: "ecommerce", label: "E-commerce" },
  { value: "app", label: "App" },
  { value: "ifood", label: "iFood" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "instagram", label: "Instagram" },
  { value: "indicacao", label: "Indicação" },
];

export function nomeOrigemCliente(origem) {
  if (!origem) return "Não identificada";
  return (
    ORIGENS_CLIENTE.find((item) => item.value === origem)?.label ||
    origem.replaceAll("_", " ").replace(/^./, (char) => char.toUpperCase())
  );
}
