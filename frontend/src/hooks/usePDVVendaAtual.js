import { usePDVVendaAcoes } from "./usePDVVendaAcoes";
import { usePDVVendaCarregamento } from "./usePDVVendaCarregamento";
import { usePDVSituacaoFiscal } from "./usePDVSituacaoFiscal";

export function usePDVVendaAtual({
  vendaAtual,
  modoVisualizacao,
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
  usePDVSituacaoFiscal({ vendaAtual, modoVisualizacao, setVendaAtual });
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
