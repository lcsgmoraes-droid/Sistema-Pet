const criarEntregaVazia = () => ({
  endereco_completo: "",
  taxa_entrega_total: 0,
  taxa_loja: 0,
  taxa_entregador: 0,
  observacoes_entrega: "",
});

const recalcularTotalComEntrega = (subtotal, taxaEntrega) =>
  parseFloat((Number(subtotal || 0) + Number(taxaEntrega || 0)).toFixed(2));

export function usePDVEntregaForm(
  vendaAtual,
  setVendaAtual,
  { entregadores, selecionarEntregador },
) {
  const handleToggleTemEntrega = (temEntrega) => {
    setVendaAtual((prev) => {
      const taxaEntrega = temEntrega ? prev.entrega?.taxa_entrega_total || 0 : 0;

      return {
        ...prev,
        tem_entrega: temEntrega,
        total: recalcularTotalComEntrega(prev.subtotal, taxaEntrega),
        entrega: temEntrega ? prev.entrega : criarEntregaVazia(),
      };
    });
  };

  const handleSelecionarEnderecoEntrega = (enderecoCompleto) => {
    setVendaAtual((prev) => ({
      ...prev,
      entrega: {
        ...prev.entrega,
        endereco_completo: enderecoCompleto,
      },
    }));
  };

  const handleEnderecoEntregaChange = (valor) => {
    setVendaAtual((prev) => ({
      ...prev,
      entrega: {
        ...prev.entrega,
        endereco_completo: valor,
      },
    }));
  };

  const handleSelecionarEntregador = (entregadorId) => {
    const entregador = entregadores.find(
      (item) => item.id === parseInt(entregadorId, 10),
    );

    selecionarEntregador(entregador || null);
  };

  const handleTaxaEntregaTotalChange = (valor) => {
    const total = parseFloat(valor) || 0;
    const totalArredondado = parseFloat(total.toFixed(2));

    setVendaAtual((prev) => {
      const taxaLojaAtual = prev.entrega?.taxa_loja || 0;
      const taxaEntregadorCalculada = parseFloat(
        (totalArredondado - taxaLojaAtual).toFixed(2),
      );

      return {
        ...prev,
        total: recalcularTotalComEntrega(
          prev.subtotal,
          prev.tem_entrega ? totalArredondado : 0,
        ),
        entrega: {
          ...prev.entrega,
          taxa_entrega_total: totalArredondado,
          taxa_loja: parseFloat(taxaLojaAtual.toFixed(2)),
          taxa_entregador: taxaEntregadorCalculada,
        },
      };
    });
  };

  const handleTaxaLojaChange = (valor) => {
    const taxaLoja = parseFloat(valor) || 0;
    const taxaLojaArredondada = parseFloat(taxaLoja.toFixed(2));

    setVendaAtual((prev) => {
      const total = prev.entrega?.taxa_entrega_total || 0;
      const taxaEntregadorArredondada = parseFloat(
        (total - taxaLojaArredondada).toFixed(2),
      );

      return {
        ...prev,
        entrega: {
          ...prev.entrega,
          taxa_loja: taxaLojaArredondada,
          taxa_entregador: taxaEntregadorArredondada,
        },
      };
    });
  };

  const handleTaxaEntregadorChange = (valor) => {
    const taxaEntregador = parseFloat(valor) || 0;
    const taxaEntregadorArredondada = parseFloat(taxaEntregador.toFixed(2));

    setVendaAtual((prev) => {
      const total = prev.entrega?.taxa_entrega_total || 0;
      const taxaLojaArredondada = parseFloat(
        (total - taxaEntregadorArredondada).toFixed(2),
      );

      return {
        ...prev,
        entrega: {
          ...prev.entrega,
          taxa_entregador: taxaEntregadorArredondada,
          taxa_loja: taxaLojaArredondada,
        },
      };
    });
  };

  const handleObservacoesEntregaChange = (valor) => {
    setVendaAtual((prev) => ({
      ...prev,
      entrega: {
        ...prev.entrega,
        observacoes_entrega: valor,
      },
    }));
  };

  return {
    handleToggleTemEntrega,
    handleSelecionarEnderecoEntrega,
    handleEnderecoEntregaChange,
    handleSelecionarEntregador,
    handleTaxaEntregaTotalChange,
    handleTaxaLojaChange,
    handleTaxaEntregadorChange,
    handleObservacoesEntregaChange,
  };
}
