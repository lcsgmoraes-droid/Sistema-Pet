import { Route } from "react-router-dom";
import ProtectedRoute from "../../components/ProtectedRoute";
import {
  AlertasRacao,
  ChatIA,
  DashEntregasFinanceiro,
  EntregasAbertas,
  HistoricoEntregas,
  IAFluxoCaixa,
  OpcoesRacao,
  RotasEntrega,
  WhatsAppDashboard,
} from "../lazyPages";
import { ModuleGate } from "./RouteGates";

function entregasPage(children) {
  return <ModuleGate modulo="entregas">{children}</ModuleGate>;
}

export function createDeliveryAiRoutes() {
  return (
    <>
      <Route path="entregas/abertas" element={entregasPage(<EntregasAbertas />)} />
      <Route path="entregas/rotas" element={entregasPage(<RotasEntrega />)} />
      <Route path="entregas/historico" element={entregasPage(<HistoricoEntregas />)} />
      <Route path="entregas/financeiro" element={entregasPage(<DashEntregasFinanceiro />)} />
      <Route
        path="ia/fluxo-caixa"
        element={
          <ModuleGate modulo="financeiro_erp">
            <ProtectedRoute permission="ia.fluxo_caixa">
              <IAFluxoCaixa />
            </ProtectedRoute>
          </ModuleGate>
        }
      />
      <Route
        path="ia/chat"
        element={
          <ModuleGate modulo="financeiro_erp">
            <ChatIA />
          </ModuleGate>
        }
      />
      <Route
        path="ia/whatsapp"
        element={
          <ProtectedRoute permission="ia.whatsapp">
            <ModuleGate modulo="whatsapp">
              <WhatsAppDashboard />
            </ModuleGate>
          </ProtectedRoute>
        }
      />
      <Route
        path="ia/alertas-racao"
        element={
          <ProtectedRoute permission="produtos.editar">
            <AlertasRacao />
          </ProtectedRoute>
        }
      />
      <Route
        path="cadastros/opcoes-racao"
        element={
          <ProtectedRoute permission="produtos.editar">
            <OpcoesRacao />
          </ProtectedRoute>
        }
      />
    </>
  );
}
