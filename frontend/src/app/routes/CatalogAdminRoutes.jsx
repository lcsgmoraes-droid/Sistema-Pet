import { Route } from "react-router-dom";
import ProtectedRoute from "../../components/ProtectedRoute";
import {
  Cargos,
  Categorias,
  CategoriasFinanceiras,
  ContasBancarias,
  Departamentos,
  EspeciesRacas,
  FormasPagamento,
  Marcas,
  OperadorasCartao,
  Subcategorias,
  TipoDespesa,
} from "../lazyPages";
import { ModuleGate } from "./RouteGates";

export function createCatalogAdminRoutes() {
  return (
    <>
      <Route
        path="cadastros/departamentos"
        element={
          <ProtectedRoute permission="cadastros.categorias_produtos">
            <Departamentos />
          </ProtectedRoute>
        }
      />
      <Route
        path="cadastros/marcas"
        element={
          <ProtectedRoute permission="cadastros.categorias_produtos">
            <Marcas />
          </ProtectedRoute>
        }
      />
      <Route
        path="cadastros/categorias"
        element={
          <ProtectedRoute permission="cadastros.categorias_produtos">
            <Categorias />
          </ProtectedRoute>
        }
      />
      <Route
        path="cadastros/tipos-despesa"
        element={
          <ProtectedRoute permission="cadastros.categorias_financeiras">
            <TipoDespesa />
          </ProtectedRoute>
        }
      />
      <Route
        path="cadastros/despesas-rapidas"
        element={
          <ProtectedRoute permission="cadastros.categorias_financeiras">
            <TipoDespesa />
          </ProtectedRoute>
        }
      />
      <Route
        path="cadastros/categorias-financeiras"
        element={
          <ModuleGate modulo="financeiro_erp">
            <CategoriasFinanceiras />
          </ModuleGate>
        }
      />
      <Route
        path="cadastros/especies-racas"
        element={
          <ProtectedRoute permission="cadastros.especies_racas">
            <EspeciesRacas />
          </ProtectedRoute>
        }
      />
      <Route
        path="cadastros/cargos"
        element={
          <ModuleGate modulo="rh">
            <Cargos />
          </ModuleGate>
        }
      />
      <Route
        path="cadastros/financeiro/bancos"
        element={
          <ModuleGate modulo="financeiro_erp">
            <ProtectedRoute permission="configuracoes.editar">
              <ContasBancarias />
            </ProtectedRoute>
          </ModuleGate>
        }
      />
      <Route
        path="cadastros/financeiro/formas-pagamento"
        element={
          <ProtectedRoute permission="configuracoes.editar">
            <FormasPagamento />
          </ProtectedRoute>
        }
      />
      <Route
        path="cadastros/financeiro/operadoras"
        element={
          <ProtectedRoute permission="configuracoes.editar">
            <OperadorasCartao />
          </ProtectedRoute>
        }
      />
      <Route path="subcategorias" element={<Subcategorias />} />
    </>
  );
}
