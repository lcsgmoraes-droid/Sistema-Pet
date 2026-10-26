export const DADOS_ADICIONAIS_NOTA_INICIAIS = {
  canal: "loja_fisica",
  numero_pedido: "",
  codigo_rastreamento: "",
  informacoes_complementares: "",
  intermediador_cnpj: "",
  intermediador_identificacao: "",
};

export const CANAIS_DADOS_NOTA = [
  { value: "loja_fisica", label: "PDV / loja física" },
  { value: "venda_direta_online", label: "Venda direta pela internet" },
  { value: "amazon", label: "Amazon" },
];

export function validarDadosAdicionaisNota(dados) {
  if (!CANAIS_DADOS_NOTA.some((canal) => canal.value === dados.canal))
    return "Selecione o canal desta operação.";
  if (dados.canal !== "amazon") return "";
  if (!dados.numero_pedido.trim()) return "Informe o número do pedido da Amazon.";
  if (dados.intermediador_cnpj.replace(/\D/g, "").length !== 14)
    return "Informe o CNPJ do intermediador com 14 dígitos.";
  if (!dados.intermediador_identificacao.trim())
    return "Informe a identificação da sua loja ou vendedor na Amazon. Esse dado é diferente do número do pedido.";
  if (
    dados.intermediador_identificacao.trim().toLowerCase() ===
    dados.numero_pedido.trim().toLowerCase()
  )
    return "A identificação da sua loja ou vendedor na Amazon não pode ser o número do pedido.";
  return "";
}
