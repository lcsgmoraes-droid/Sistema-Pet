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
import { ModuleGate } from "./RouteGates";

function comissoesPage(children) {
  return <ModuleGate modulo="comissoes">{children}</ModuleGate>;
}

export function createCommissionRoutes() {
  return (
    <>
      <Route path="comissoes" element={comissoesPage(<Comissoes />)} />
      <Route path="comissoes/demonstrativo" element={comissoesPage(<ComissoesListagem />)} />
      <Route path="comissoes/relatorios" element={comissoesPage(<RelatoriosComissoes />)} />
      <Route path="comissoes/abertas" element={comissoesPage(<ComissoesAbertas />)} />
      <Route
        path="comissoes/fechamento/:funcionario_id"
        element={comissoesPage(<ConferenciaAvancada />)}
      />
      <Route
        path="comissoes/fechamentos"
        element={comissoesPage(<ComissoesHistoricoFechamentos />)}
      />
      <Route
        path="comissoes/fechamentos/detalhe"
        element={comissoesPage(<ComissoesFechamentoDetalhe />)}
      />
      <Route path="subcategorias" element={<Subcategorias />} />
    </>
  );
}
