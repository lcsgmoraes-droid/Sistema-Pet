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
  limparComissao,
}) {
  const abrirModalPagamento = () => {
    if (vendaAtual.itens.length === 0) {
      alert("Adicione pelo menos um produto ou servico");
      return;
    }

    if (vendaAtual.status === "finalizada" || vendaAtual.status === "pago_nf") {
      alert(
        'Esta venda esta finalizada. Clique em "Reabrir Venda" para modificar.',
      );
      return;
    }

    setMostrarModalPagamento(true);
  };

  const limparVenda = () => {
    setVendaAtual({
      cliente: null,
      pet: null,
      itens: [],
      subtotal: 0,
      desconto_valor: 0,
      desconto_percentual: 0,
      total: 0,
      observacoes: "",
      funcionario_id: null,
      entregador_id: entregadorSelecionado?.id || null,
      tem_entrega: false,
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
