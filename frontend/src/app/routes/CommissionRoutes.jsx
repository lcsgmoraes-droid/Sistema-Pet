import { Route } from "react-router-dom";
import {
  Comissoes,
  ComissoesAbertas,
  ComissoesFechamentoDetalhe,
  ComissoesHistoricoFechamentos,
  ComissoesListagem,
  ConferenciaAvancada,
  RelatoriosComissoes,
  Subcategorias,
} from "../lazyPages";
import ProtectedRoute from "../../components/ProtectedRoute";
import { ModuleGate } from "./RouteGates";

function comissoesPage(children, permission) {
  return (
    <ModuleGate modulo="comissoes">
      <ProtectedRoute permission={permission}>{children}</ProtectedRoute>
    </ModuleGate>
  );
}

export function createCommissionRoutes() {
  return (
    <>
      <Route path="comissoes" element={comissoesPage(<Comissoes />, "comissoes.configurar")} />
      <Route
        path="comissoes/demonstrativo"
        element={comissoesPage(<ComissoesListagem />, "comissoes.demonstrativo")}
      />
      <Route
        path="comissoes/relatorios"
        element={comissoesPage(<RelatoriosComissoes />, "comissoes.relatorios")}
      />
      <Route
        path="comissoes/abertas"
        element={comissoesPage(<ComissoesAbertas />, "comissoes.abertas")}
      />
      <Route
        path="comissoes/fechamento/:funcionario_id"
        element={comissoesPage(<ConferenciaAvancada />, "comissoes.fechamentos")}
      />
      <Route
        path="comissoes/fechamentos"
        element={comissoesPage(<ComissoesHistoricoFechamentos />, "comissoes.fechamentos")}
      />
      <Route
        path="comissoes/fechamentos/detalhe"
        element={comissoesPage(<ComissoesFechamentoDetalhe />, "comissoes.fechamentos")}
      />
      <Route path="subcategorias" element={<Subcategorias />} />
    </>
  );
}
