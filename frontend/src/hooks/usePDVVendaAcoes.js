import { podeRegistrarRecebimentoVenda } from "../utils/pdvReturnEligibility";

function criarEntregaVazia() {
  return {
    endereco_completo: "",
    taxa_entrega_total: 0,
    taxa_loja: 0,
    taxa_entregador: 0,
    observacoes_entrega: "",
  };
}

export function usePDVVendaAcoes({
  vendaAtual,
  setVendaAtual,
  setModoVisualizacao,
  setMostrarModalPagamento,
  entregadorSelecionado,
  vendedorObrigatorio,
  vendaComissionada,
  funcionarioComissao,
  limparComissao,
}) {
  const abrirModalPagamento = () => {
    if (vendaAtual.itens.length === 0) {
      alert("Adicione pelo menos um produto ou servico");
      return;
    }

    if (vendedorObrigatorio === null) {
      alert("Aguarde o carregamento das regras do PDV.");
      return;
    }

    if ((vendaComissionada || vendedorObrigatorio) && !funcionarioComissao) {
      alert("Selecione o vendedor antes de receber a venda.");
      return;
    }

    if (!podeRegistrarRecebimentoVenda(vendaAtual)) {
      alert("Esta venda não permite novos recebimentos no estado atual.");
      return;
    }

    setMostrarModalPagamento(true);
  };

  const limparVenda = () => {
    setVendaAtual({
      cliente: null,
      pet: null,
      canal: "loja_fisica",
      itens: [],
      subtotal: 0,
      desconto_valor: 0,
      desconto_venda_valor: 0,
      desconto_percentual: 0,
      cupom_code: null,
      cupom_discount_applied: null,
      total: 0,
      observacoes: "",
      funcionario_id: null,
      vendedor_funcionario_id: null,
      entregador_id: entregadorSelecionado?.id || null,
      tem_entrega: false,
      pagamento_entrega_previsto: null,
      entrega: criarEntregaVazia(),
    });
    limparComissao();
    setModoVisualizacao(false);
  };

  return {
    abrirModalPagamento,
    limparVenda,
  };
}
