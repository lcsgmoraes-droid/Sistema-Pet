import { usePDVCarrinhoItens } from "./usePDVCarrinhoItens";
import { usePDVProdutoBusca } from "./usePDVProdutoBusca";

export function usePDVProdutos({
  vendaAtual,
  setVendaAtual,
  modoVisualizacao,
  temCaixaAberto,
  recalcularTotais,
}) {
  const {
    copiadoCodigoItem,
    itensKitExpandidos,
    adicionarProdutoAoCarrinho,
    alterarQuantidade,
    atualizarPetDoItem,
    atualizarQuantidadeItem,
    copiarCodigoProdutoCarrinho,
    removerItem,
    toggleKitExpansion,
  } = usePDVCarrinhoItens({
    vendaAtual,
    setVendaAtual,
    temCaixaAberto,
    recalcularTotais,
  });

  const {
    buscaProduto,
    buscaProdutoContainerRef,
    inputProdutoRef,
    mostrarSugestoesProduto,
    produtosSugeridos,
    adicionarProduto,
    handleBuscarProdutoChange,
    handleBuscarProdutoFocus,
    handleBuscarProdutoKeyDown,
    limparBuscaProduto,
    selecionarProdutoSugerido,
  } = usePDVProdutoBusca({
    modoVisualizacao,
    adicionarProdutoAoCarrinho,
  });

  return {
    buscaProduto,
    buscaProdutoContainerRef,
    copiadoCodigoItem,
    inputProdutoRef,
    itensKitExpandidos,
    mostrarSugestoesProduto,
    produtosSugeridos,
    adicionarProduto,
    alterarQuantidade,
    atualizarPetDoItem,
    atualizarQuantidadeItem,
    copiarCodigoProdutoCarrinho,
    handleBuscarProdutoChange,
    handleBuscarProdutoFocus,
    handleBuscarProdutoKeyDown,
    limparBuscaProduto,
    removerItem,
    selecionarProdutoSugerido,
    toggleKitExpansion,
  };
}
