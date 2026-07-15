import { Plus, Wallet } from "lucide-react";

import ModalNovaContaPagar from "../ModalNovaContaPagar";
import ActionButton from "../ui/ActionButton";
import LoadingState from "../ui/LoadingState";
import PageHeader from "../ui/PageHeader";
import ContasPagarAnalise from "./ContasPagarAnalise";
import ContasPagarFilters from "./ContasPagarFilters";
import ContasPagarTable from "./ContasPagarTable";
import ContasPagarModals from "./ContasPagarModals";
import ContasPagarPagamentoLoteModal from "./ContasPagarPagamentoLoteModal";

export default function ContasPagarView({
  loading,
  abaAtivaContasPagar,
  setAbaAtivaContasPagar,
  setContaEdicao,
  setMostrarModalNovaConta,
  filtros,
  setFiltros,
  fornecedores,
  fornecedorFiltroSelecionado,
  tiposDespesaOrdenados,
  aplicarPeriodoRapido,
  filtrarDespesasCaixa,
  filtrarTaxasCartao,
  alternarOcultarTaxasCartao,
  limparFiltros,
  aplicarFiltros,
  handleFiltrosSubmit,
  contasVisiveis,
  contasSelecionadas,
  contasSelecionadasObjetos,
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
  abrirPagamentoEmLote,
  editarContaSelecionada,
  estornarContasSelecionadas,
  cancelarContasSelecionadas,
  excluirContasSelecionadas,
  limparSelecaoContas,
  haContaPagavelSelecionada,
  haContaPagaSelecionada,
  haContaCancelavelSelecionada,
  haContaExcluivelSelecionada,
  mostrarModalPagamento,
  contaSelecionada,
  setMostrarModalPagamento,
  formatarMoeda,
  dadosPagamento,
  setDadosPagamento,
  mostrarModalPagamentoLote,
  setMostrarModalPagamentoLote,
  dadosPagamentoLote,
  setDadosPagamentoLote,
  handleFormaPagamentoLoteChange,
  registrarPagamentoEmLote,
  saldoTotalPagamentoLote,
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

      <div className="mb-5 flex flex-wrap gap-2 border-b border-slate-200">
        {[
          { id: "lancamentos", label: "Lancamentos" },
          { id: "analise", label: "Analise" },
        ].map((aba) => {
          const ativa = abaAtivaContasPagar === aba.id;
          return (
            <button
              key={aba.id}
              type="button"
              onClick={() => setAbaAtivaContasPagar(aba.id)}
              className={[
                "border-b-2 px-4 py-2 text-sm font-semibold transition",
                ativa
                  ? "border-blue-600 text-blue-700"
                  : "border-transparent text-slate-500 hover:text-slate-800",
              ].join(" ")}
            >
              {aba.label}
            </button>
          );
        })}
      </div>

      {abaAtivaContasPagar === "analise" ? (
        <ContasPagarAnalise
          fornecedores={fornecedores}
          formatarMoeda={formatarMoeda}
          tiposDespesaOrdenados={tiposDespesaOrdenados}
        />
      ) : (
        <>
          <ContasPagarFilters
            filtros={filtros}
            setFiltros={setFiltros}
            fornecedores={fornecedores}
            fornecedorFiltroSelecionado={fornecedorFiltroSelecionado}
            tiposDespesaOrdenados={tiposDespesaOrdenados}
            aplicarPeriodoRapido={aplicarPeriodoRapido}
            filtrarDespesasCaixa={filtrarDespesasCaixa}
            filtrarTaxasCartao={filtrarTaxasCartao}
            alternarOcultarTaxasCartao={alternarOcultarTaxasCartao}
            limparFiltros={limparFiltros}
            aplicarFiltros={aplicarFiltros}
            handleFiltrosSubmit={handleFiltrosSubmit}
          />

          <ContasPagarTable
            contasVisiveis={contasVisiveis}
            contasSelecionadas={contasSelecionadas}
            contasSelecionadasObjetos={contasSelecionadasObjetos}
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
            abrirPagamentoEmLote={abrirPagamentoEmLote}
            editarContaSelecionada={editarContaSelecionada}
            estornarContasSelecionadas={estornarContasSelecionadas}
            cancelarContasSelecionadas={cancelarContasSelecionadas}
            excluirContasSelecionadas={excluirContasSelecionadas}
            limparSelecaoContas={limparSelecaoContas}
            haContaPagavelSelecionada={haContaPagavelSelecionada}
            haContaPagaSelecionada={haContaPagaSelecionada}
            haContaCancelavelSelecionada={haContaCancelavelSelecionada}
            haContaExcluivelSelecionada={haContaExcluivelSelecionada}
          />
        </>
      )}

      <ContasPagarPagamentoLoteModal
        aberto={mostrarModalPagamentoLote}
        contasSelecionadasObjetos={contasSelecionadasObjetos}
        contasBancarias={contasBancarias}
        dadosPagamentoLote={dadosPagamentoLote}
        formasPagamento={formasPagamento}
        formatarMoeda={formatarMoeda}
        handleFormaPagamentoLoteChange={handleFormaPagamentoLoteChange}
        onClose={() => setMostrarModalPagamentoLote(false)}
        onConfirmar={registrarPagamentoEmLote}
        saldoTotalPagamentoLote={saldoTotalPagamentoLote}
        setDadosPagamentoLote={setDadosPagamentoLote}
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
