import { usePDVEntregadores } from "./usePDVEntregadores";
import { usePDVEntregaForm } from "./usePDVEntregaForm";

export function usePDVEntrega(vendaAtual, setVendaAtual) {
  const {
    entregadores,
    entregadorSelecionado,
    custoOperacionalEntrega,
    sincronizarEntregadorDaVenda,
    selecionarEntregador,
  } = usePDVEntregadores(vendaAtual, setVendaAtual);
  const {
    handleToggleTemEntrega,
    handleSelecionarEnderecoEntrega,
    handleEnderecoEntregaChange,
    handleSelecionarEntregador,
    handleTaxaEntregaTotalChange,
    handleTaxaLojaChange,
    handleTaxaEntregadorChange,
    handleObservacoesEntregaChange,
  } = usePDVEntregaForm(vendaAtual, setVendaAtual, {
    entregadores,
    selecionarEntregador,
  });

  return {
    entregadores,
    entregadorSelecionado,
    custoOperacionalEntrega,
    sincronizarEntregadorDaVenda,
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
