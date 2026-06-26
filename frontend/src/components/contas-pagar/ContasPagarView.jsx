import { Plus, Wallet } from "lucide-react";

import ModalNovaContaPagar from "../ModalNovaContaPagar";
import ActionButton from "../ui/ActionButton";
import LoadingState from "../ui/LoadingState";
import PageHeader from "../ui/PageHeader";
import ContasPagarFilters from "./ContasPagarFilters";
import ContasPagarTable from "./ContasPagarTable";
import ContasPagarModals from "./ContasPagarModals";

export default function ContasPagarView({
  loading,
  setContaEdicao,
  setMostrarModalNovaConta,
  filtros,
  setFiltros,
  fornecedores,
  fornecedorFiltroSelecionado,
  tiposDespesaOrdenados,
  aplicarPeriodoRapido,
  filtrarDespesasCaixa,
  limparFiltros,
  aplicarFiltros,
  handleFiltrosSubmit,
  contasVisiveis,
  contasSelecionadas,
  todasVisiveisSelecionadas,
  algumasVisiveisSelecionadas,
  selecionarTodasContasVisiveis,
  alternarSelecaoConta,
  getContaTooltip,
  getDescricaoPrincipal,
  getStatusBadge,
  formatarData,
  abrirModalEdicao,
  abrirModalPagamento,
  precisaClassificacao,
  abrirModalClassificacao,
  excluirContaPagar,
  contaTemPagamento,
  totalSelecionadas,
  editarContaSelecionada,
  estornarContasSelecionadas,
  cancelarContasSelecionadas,
  excluirContasSelecionadas,
  limparSelecaoContas,
  haContaPagaSelecionada,
  haContaCancelavelSelecionada,
  haContaExcluivelSelecionada,
  mostrarModalPagamento,
  contaSelecionada,
  setMostrarModalPagamento,
  formatarMoeda,
  dadosPagamento,
  setDadosPagamento,
  handleFormaChange,
  formasPagamento,
  setMostrarModalNovaForma,
  contasBancarias,
  registrarPagamento,
  mostrarModalNovaForma,
  novaFormaData,
  setNovaFormaData,
  salvarNovaForma,
  mostrarModalClassificacao,
  setMostrarModalClassificacao,
  dadosClassificacao,
  setDadosClassificacao,
  salvarClassificacao,
  categoriasFinanceiras,
  subcategoriasDre,
  modalExclusaoRecorrencia,
  setModalExclusaoRecorrencia,
  recorrenciasSelecionadasExclusao,
  setRecorrenciasSelecionadasExclusao,
  alternarRecorrenciaExclusao,
  confirmarExclusaoRecorrencia,
  mostrarModalNovaConta,
  contaEdicao,
  carregarDados,
}) {
  if (loading) {
    return <LoadingState label="Carregando contas a pagar..." />;
  }

  return (
    <div className="p-6">
      <PageHeader
        actions={
          <ActionButton
            onClick={() => {
              setContaEdicao(null);
              setMostrarModalNovaConta(true);
            }}
            intent="create"
            size="md"
            icon={Plus}
          >
            Nova Conta
          </ActionButton>
        }
        className="mb-6"
        icon={Wallet}
        subtitle="Gerencie vencimentos, despesas e pagamentos"
        title="Contas a Pagar"
      />

      <ContasPagarFilters
        filtros={filtros}
        setFiltros={setFiltros}
        fornecedores={fornecedores}
        fornecedorFiltroSelecionado={fornecedorFiltroSelecionado}
        tiposDespesaOrdenados={tiposDespesaOrdenados}
        aplicarPeriodoRapido={aplicarPeriodoRapido}
        filtrarDespesasCaixa={filtrarDespesasCaixa}
        limparFiltros={limparFiltros}
        aplicarFiltros={aplicarFiltros}
        handleFiltrosSubmit={handleFiltrosSubmit}
      />

      <ContasPagarTable
        contasVisiveis={contasVisiveis}
        contasSelecionadas={contasSelecionadas}
        todasVisiveisSelecionadas={todasVisiveisSelecionadas}
        algumasVisiveisSelecionadas={algumasVisiveisSelecionadas}
        selecionarTodasContasVisiveis={selecionarTodasContasVisiveis}
        alternarSelecaoConta={alternarSelecaoConta}
        getContaTooltip={getContaTooltip}
        getDescricaoPrincipal={getDescricaoPrincipal}
        getStatusBadge={getStatusBadge}
        formatarData={formatarData}
        abrirModalEdicao={abrirModalEdicao}
        abrirModalPagamento={abrirModalPagamento}
        precisaClassificacao={precisaClassificacao}
        abrirModalClassificacao={abrirModalClassificacao}
        excluirContaPagar={excluirContaPagar}
        contaTemPagamento={contaTemPagamento}
        totalSelecionadas={totalSelecionadas}
        editarContaSelecionada={editarContaSelecionada}
        estornarContasSelecionadas={estornarContasSelecionadas}
        cancelarContasSelecionadas={cancelarContasSelecionadas}
        excluirContasSelecionadas={excluirContasSelecionadas}
        limparSelecaoContas={limparSelecaoContas}
        haContaPagaSelecionada={haContaPagaSelecionada}
        haContaCancelavelSelecionada={haContaCancelavelSelecionada}
        haContaExcluivelSelecionada={haContaExcluivelSelecionada}
      />

      <ContasPagarModals
        mostrarModalPagamento={mostrarModalPagamento}
        contaSelecionada={contaSelecionada}
        setMostrarModalPagamento={setMostrarModalPagamento}
        formatarMoeda={formatarMoeda}
        dadosPagamento={dadosPagamento}
        setDadosPagamento={setDadosPagamento}
        handleFormaChange={handleFormaChange}
        formasPagamento={formasPagamento}
        setMostrarModalNovaForma={setMostrarModalNovaForma}
        contasBancarias={contasBancarias}
        registrarPagamento={registrarPagamento}
        mostrarModalNovaForma={mostrarModalNovaForma}
        novaFormaData={novaFormaData}
        setNovaFormaData={setNovaFormaData}
        salvarNovaForma={salvarNovaForma}
        mostrarModalClassificacao={mostrarModalClassificacao}
        setMostrarModalClassificacao={setMostrarModalClassificacao}
        dadosClassificacao={dadosClassificacao}
        setDadosClassificacao={setDadosClassificacao}
        categoriasFinanceiras={categoriasFinanceiras}
        subcategoriasDre={subcategoriasDre}
        tiposDespesaOrdenados={tiposDespesaOrdenados}
        salvarClassificacao={salvarClassificacao}
        modalExclusaoRecorrencia={modalExclusaoRecorrencia}
        setModalExclusaoRecorrencia={setModalExclusaoRecorrencia}
        recorrenciasSelecionadasExclusao={recorrenciasSelecionadasExclusao}
        setRecorrenciasSelecionadasExclusao={setRecorrenciasSelecionadasExclusao}
        formatarData={formatarData}
        alternarRecorrenciaExclusao={alternarRecorrenciaExclusao}
        confirmarExclusaoRecorrencia={confirmarExclusaoRecorrencia}
      />

      {/* Modal Nova Conta */}
      <ModalNovaContaPagar
        isOpen={mostrarModalNovaConta}
        contaEdicao={contaEdicao}
        onClose={() => {
          setMostrarModalNovaConta(false);
          setContaEdicao(null);
        }}
        onSave={carregarDados}
      />
    </div>
  );
}
