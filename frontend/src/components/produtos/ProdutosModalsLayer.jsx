import React from "react";
import ModalImportacaoProdutos from "../ModalImportacaoProdutos";
import ProdutosColunasModal from "./ProdutosColunasModal";
import ProdutosConflitoExclusaoModal from "./ProdutosConflitoExclusaoModal";
import ProdutosEdicaoLoteModal from "./ProdutosEdicaoLoteModal";
import ProdutosRelatorioModal from "./ProdutosRelatorioModal";

export default function ProdutosModalsLayer({
  autoSelecionarConflito,
  bloqueiosExclusao,
  categorias,
  colunasRelatorio,
  colunasRelatorioProdutos,
  colunasTabela,
  colunasTemporarias,
  corrigirTextoQuebrado,
  dadosEdicaoLote,
  departamentos,
  marcas,
  modalColunas,
  modalConflitoExclusao,
  modalEdicaoLote,
  modalImportacao,
  modalRelatorioPersonalizado,
  onCancelarConflito,
  onCloseImportacao,
  onCloseModalColunas,
  onCloseModalConflito,
  onCloseModalEdicaoLote,
  onCloseModalRelatorio,
  onGerarRelatorioPersonalizado,
  onImportacaoSucesso,
  onRestaurarColunasPadrao,
  onSalvarColunas,
  onSalvarEdicaoLote,
  onSelecionarTodasVariacoesDoPai,
  onSelecionarVariacaoConflito,
  onToggleAutoSelecionarConflito,
  onToggleColuna,
  onToggleColunaRelatorio,
  onTogglePularConfirmacaoConflito,
  ordenacaoRelatorio,
  pularConfirmacaoConflito,
  resolvendoConflitoExclusao,
  selecionadosCount,
  setDadosEdicaoLote,
  setOrdenacaoRelatorio,
  variacoesSelecionadasConflito,
}) {
  return (
    <>
      <ProdutosConflitoExclusaoModal
        autoSelecionarConflito={autoSelecionarConflito}
        bloqueiosExclusao={bloqueiosExclusao}
        corrigirTextoQuebrado={corrigirTextoQuebrado}
        isOpen={modalConflitoExclusao}
        onCancelarConflito={onCancelarConflito}
        onClose={onCloseModalConflito}
        onSelecionarTodasVariacoesDoPai={onSelecionarTodasVariacoesDoPai}
        onSelecionarVariacaoConflito={onSelecionarVariacaoConflito}
        onToggleAutoSelecionarConflito={onToggleAutoSelecionarConflito}
        onTogglePularConfirmacaoConflito={onTogglePularConfirmacaoConflito}
        pularConfirmacaoConflito={pularConfirmacaoConflito}
        resolvendoConflitoExclusao={resolvendoConflitoExclusao}
        variacoesSelecionadasConflito={variacoesSelecionadasConflito}
      />

      <ProdutosEdicaoLoteModal
        categorias={categorias}
        dadosEdicaoLote={dadosEdicaoLote}
        departamentos={departamentos}
        isOpen={modalEdicaoLote}
        marcas={marcas}
        onClose={onCloseModalEdicaoLote}
        onSalvar={onSalvarEdicaoLote}
        selecionadosCount={selecionadosCount}
        setDadosEdicaoLote={setDadosEdicaoLote}
      />

      <ProdutosColunasModal
        colunasTabela={colunasTabela}
        colunasTemporarias={colunasTemporarias}
        isOpen={modalColunas}
        onClose={onCloseModalColunas}
        onRestaurarColunasPadrao={onRestaurarColunasPadrao}
        onSalvarColunas={onSalvarColunas}
        onToggleColuna={onToggleColuna}
      />

      <ProdutosRelatorioModal
        colunasRelatorio={colunasRelatorio}
        colunasRelatorioProdutos={colunasRelatorioProdutos}
        isOpen={modalRelatorioPersonalizado}
        onClose={onCloseModalRelatorio}
        onGerarRelatorioPersonalizado={onGerarRelatorioPersonalizado}
        onToggleColunaRelatorio={onToggleColunaRelatorio}
        ordenacaoRelatorio={ordenacaoRelatorio}
        setOrdenacaoRelatorio={setOrdenacaoRelatorio}
      />

      <ModalImportacaoProdutos
        isOpen={modalImportacao}
        onClose={onCloseImportacao}
        onSuccess={onImportacaoSucesso}
      />
    </>
  );
}
