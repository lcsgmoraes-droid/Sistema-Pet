import { AlertTriangle } from "lucide-react";
import ModuleTabs from "../../components/ui/ModuleTabs";
import AnaliseCustosPanel from "./AnaliseCustosPanel";
import DetalhamentoMargemPanel from "./DetalhamentoMargemPanel";
import DetalhesPontoEquilibrioDrawer from "./DetalhesPontoEquilibrioDrawer";
import { ABAS_PONTO_EQUILIBRIO } from "./pontoEquilibrioConstants";
import PontoEquilibrioHeaderFilters from "./PontoEquilibrioHeaderFilters";
import PontoEquilibrioResumoTab from "./PontoEquilibrioResumoTab";
import PontoEquilibrioStatusSummary from "./PontoEquilibrioStatusSummary";
import SimuladorImpactoPanel from "./SimuladorImpactoPanel";
import usePontoEquilibrioController from "./usePontoEquilibrioController";

export default function PontoEquilibrioPage() {
  const controller = usePontoEquilibrioController();
  const {
    abaAtiva,
    abrirDetalhesPontoEquilibrio,
    analiseCustos,
    carregarDados,
    dados,
    detalhesLinha,
    erro,
    fecharDetalhesPontoEquilibrio,
    filtros,
    impactoForm,
    impactoSimulado,
    impactoValor,
    linhaDetalhe,
    loading,
    loadingDetalhes,
    margemPeriodoPercentual,
    margemUsadaPercentual,
    percentualAtingido,
    porteAnalise,
    setAbaAtiva,
    setFiltros,
    setImpactoForm,
    setPorteAnalise,
    statusResumo,
  } = controller;

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <PontoEquilibrioHeaderFilters
          carregarDados={carregarDados}
          filtros={filtros}
          loading={loading}
          setFiltros={setFiltros}
        />

        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">
          <p className="font-semibold">Formula usada</p>
          <p className="mt-1">
            Ponto de equilibrio = custos fixos / margem de contribuicao. A margem de contribuicao
            pode vir do periodo atual ou de meses fechados. Ela usa o snapshot financeiro das
            vendas: receita, descontos, campanhas, taxas, entrega, comissoes, custo gerencial, CMV e
            outros custos variaveis sem duplicar contas geradas pela propria venda.
          </p>
        </div>

        {erro && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {erro}
          </div>
        )}

        {dados && statusResumo && (
          <>
            <PontoEquilibrioStatusSummary
              dados={dados}
              percentualAtingido={percentualAtingido}
              statusResumo={statusResumo}
            />

            <ModuleTabs
              active={abaAtiva}
              ariaLabel="Abas do ponto de equilibrio"
              onChange={setAbaAtiva}
              tabs={ABAS_PONTO_EQUILIBRIO}
            />

            {abaAtiva === "resumo" && (
              <PontoEquilibrioResumoTab
                dados={dados}
                margemPeriodoPercentual={margemPeriodoPercentual}
                margemUsadaPercentual={margemUsadaPercentual}
                onAbrirDetalhes={abrirDetalhesPontoEquilibrio}
              />
            )}

            {abaAtiva === "detalhamento" && (
              <DetalhamentoMargemPanel
                dados={dados}
                onAbrirDetalhes={abrirDetalhesPontoEquilibrio}
              />
            )}

            {abaAtiva === "simulador" && (
              <SimuladorImpactoPanel
                dados={dados}
                impactoForm={impactoForm}
                impactoSimulado={impactoSimulado}
                impactoValor={impactoValor}
                setImpactoForm={setImpactoForm}
              />
            )}

            {abaAtiva === "graficos" && analiseCustos && (
              <AnaliseCustosPanel
                analise={analiseCustos}
                porteAnalise={porteAnalise}
                setPorteAnalise={setPorteAnalise}
              />
            )}

            {(dados.produtos_sem_custo > 0 || dados.quantidade_contas_sem_classificacao > 0) && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="mt-0.5 h-5 w-5" />
                  <div>
                    <p className="font-semibold">Atencao na precisao do calculo</p>
                    <p className="mt-1">
                      {dados.produtos_sem_custo > 0 &&
                        `${dados.produtos_sem_custo} produto(s) vendido(s) estao sem custo cadastrado. `}
                      {dados.quantidade_contas_sem_classificacao > 0 &&
                        `${dados.quantidade_contas_sem_classificacao} conta(s) a pagar estao sem classificacao fixo/variavel. `}
                      Esses pontos podem subestimar ou superestimar o ponto de equilibrio.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
      <DetalhesPontoEquilibrioDrawer
        linha={linhaDetalhe}
        detalhes={detalhesLinha}
        loading={loadingDetalhes}
        onClose={fecharDetalhesPontoEquilibrio}
        onPageChange={(page) => abrirDetalhesPontoEquilibrio(linhaDetalhe, page)}
      />
    </div>
  );
}
