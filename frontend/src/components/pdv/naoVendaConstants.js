export const MOTIVOS_NAO_VENDA = [
  { value: "produto_sem_estoque", label: "Produto sem estoque" },
  { value: "produto_nao_trabalhado", label: "Produto não vendido pela loja" },
  {
    value: "variacao_indisponivel",
    label: "Tamanho, sabor ou variação indisponível",
  },
  { value: "preco", label: "Preço" },
  { value: "forma_pagamento", label: "Forma de pagamento" },
  { value: "cliente_pesquisando", label: "Cliente estava pesquisando" },
  { value: "demora_atendimento", label: "Demora ou atendimento" },
  { value: "comprou_concorrente", label: "Comprou no concorrente" },
  { value: "outro", label: "Outro motivo" },
];

export const MOTIVO_NAO_VENDA_LABEL = Object.fromEntries(
  MOTIVOS_NAO_VENDA.map((item) => [item.value, item.label]),
);
