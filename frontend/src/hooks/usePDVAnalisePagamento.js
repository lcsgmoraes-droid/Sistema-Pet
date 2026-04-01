import { usePDVVendaAnalise } from "./usePDVVendaAnalise";
import { usePDVVendaFinalizacao } from "./usePDVVendaFinalizacao";

export function usePDVAnalisePagamento({
  vendaAtual,
  setVendaAtual,
  setLoading,
  modoVisualizacao,
  setModoVisualizacao,
  setMostrarModalPagamento,
  limparVenda,
  carregarVendaEspecifica,
  carregarVendasRecentes,
}) {
  const analiseState = usePDVVendaAnalise(vendaAtual);
  const finalizacaoState = usePDVVendaFinalizacao({
    vendaAtual,
    setVendaAtual,
    setLoading,
    modoVisualizacao,
    setModoVisualizacao,
    setMostrarModalPagamento,
    limparVenda,
    carregarVendaEspecifica,
    carregarVendasRecentes,
  });

  return {
    ...analiseState,
    ...finalizacaoState,
  };
}
