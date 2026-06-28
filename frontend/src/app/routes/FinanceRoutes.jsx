import { Route } from "react-router-dom";
import ProtectedRoute from "../../components/ProtectedRoute";
import {
  ConciliacaoBancaria,
  ConciliacaoCartoesTabs,
  ContasPagar,
  ContasReceber,
  DRE,
  DashboardFinanceiro,
  FluxoCaixa,
  HistoricoConciliacoes,
  PontoEquilibrio,
  RelatorioVendas,
  VendasFinanceiro,
} from "../lazyPages";
import { ModuleGate } from "./RouteGates";

function financeiroPage(children) {
  return (
    <ModuleGate modulo="financeiro_erp">
      <ProtectedRoute permission="relatorios.financeiro">{children}</ProtectedRoute>
    </ModuleGate>
  );
}

export function createFinanceRoutes() {
  return (
    <>
      <Route path="financeiro" element={financeiroPage(<DashboardFinanceiro />)} />
      <Route
        path="financeiro/vendas"
        element={
          <ProtectedRoute
            anyOfPermissions={[
              "relatorios.financeiro",
              "financeiro.vendas",
              "clientes.visualizar",
              "vendas.criar",
            ]}
          >
            <VendasFinanceiro />
          </ProtectedRoute>
        }
      />
      <Route
        path="financeiro/relatorio-vendas"
        element={
          <ProtectedRoute permission="relatorios.financeiro">
            <RelatorioVendas />
          </ProtectedRoute>
        }
      />
      <Route path="financeiro/ponto-equilibrio" element={financeiroPage(<PontoEquilibrio />)} />
      <Route path="financeiro/contas-pagar" element={financeiroPage(<ContasPagar />)} />
      <Route path="financeiro/contas-receber" element={financeiroPage(<ContasReceber />)} />
      <Route
        path="financeiro/conciliacao-3abas"
        element={financeiroPage(<ConciliacaoCartoesTabs />)}
      />
      <Route
        path="financeiro/historico-conciliacoes"
        element={financeiroPage(<HistoricoConciliacoes />)}
      />
      <Route
        path="financeiro/conciliacao-bancaria"
        element={financeiroPage(<ConciliacaoBancaria />)}
      />
      <Route path="financeiro/fluxo-caixa" element={financeiroPage(<FluxoCaixa />)} />
      <Route path="financeiro/dre" element={financeiroPage(<DRE />)} />
    </>
  );
}
