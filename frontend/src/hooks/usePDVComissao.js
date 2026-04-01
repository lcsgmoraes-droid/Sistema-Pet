import { usePDVComissaoEstado } from "./usePDVComissaoEstado";
import { usePDVFuncionariosBusca } from "./usePDVFuncionariosBusca";

export function usePDVComissao(setVendaAtual, modoVisualizacao) {
  const {
    funcionariosSugeridos,
    setFuncionariosSugeridos,
    buscaFuncionario,
    setBuscaFuncionario,
    carregarFuncionariosComissao,
  } = usePDVFuncionariosBusca();

  return usePDVComissaoEstado({
    setVendaAtual,
    modoVisualizacao,
    funcionariosSugeridos,
    setFuncionariosSugeridos,
    buscaFuncionario,
    setBuscaFuncionario,
    carregarFuncionariosComissao,
  });
}
