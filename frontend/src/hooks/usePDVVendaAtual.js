import { usePDVVendaAcoes } from "./usePDVVendaAcoes";
import { usePDVVendaCarregamento } from "./usePDVVendaCarregamento";

export function usePDVVendaAtual({
  vendaAtual,
  setVendaAtual,
  searchVendaQuery,
  setSearchVendaQuery,
  setLoading,
  setModoVisualizacao,
  setMostrarModalPagamento,
  entregadorSelecionado,
  vendedorObrigatorio,
  vendaComissionada,
  funcionarioComissao,
  limparComissao,
  sincronizarComissaoDaVenda,
  sincronizarEntregadorDaVenda,
  recarregarContextoClientePorId,
}) {
  const { carregarVendaEspecifica, handleBuscarVenda, reabrirVenda } = usePDVVendaCarregamento({
    setVendaAtual,
    searchVendaQuery,
    setSearchVendaQuery,
    setLoading,
    setModoVisualizacao,
    setMostrarModalPagamento,
    sincronizarComissaoDaVenda,
    sincronizarEntregadorDaVenda,
    recarregarContextoClientePorId,
  });
  const { abrirModalPagamento, limparVenda } = usePDVVendaAcoes({
    vendaAtual,
    setVendaAtual,
    setModoVisualizacao,
    setMostrarModalPagamento,
    entregadorSelecionado,
    vendedorObrigatorio,
    vendaComissionada,
    funcionarioComissao,
    limparComissao,
  });

  return {
    carregarVendaEspecifica,
    handleBuscarVenda,
    abrirModalPagamento,
    limparVenda,
    reabrirVenda,
  };
}
