import { Navigate, Route } from "react-router-dom";
import ProtectedRoute from "../../components/ProtectedRoute";
import {
  Campanhas,
  CanalDescontos,
  CentralNFSaida,
  EcommerceAnalytics,
  EcommerceCatalogHealth,
  EcommerceAparencia,
  EcommerceConfig,
  EcommerceDivulgacao,
  EcommercePreview,
  EstudioOfertas,
  MeusCaixas,
  NFEntrada,
  PDV,
} from "../lazyPages";
import { ModuleGate } from "./RouteGates";

export function createSalesMarketingRoutes() {
  return (
    <>
      <Route
        path="pdv"
        element={
          <ProtectedRoute permission="vendas.criar">
            <PDV />
          </ProtectedRoute>
        }
      />
      <Route
        path="meus-caixas"
        element={
          <ProtectedRoute permission="vendas.criar">
            <MeusCaixas />
          </ProtectedRoute>
        }
      />
      <Route path="notas-fiscais" element={<Navigate to="/notas-fiscais/saida" replace />} />
      <Route path="notas-fiscais/vendas" element={<Navigate to="/notas-fiscais/saida" replace />} />
      <Route
        path="notas-fiscais/saida"
        element={
          <ModuleGate modulo="fiscal">
            <CentralNFSaida />
          </ModuleGate>
        }
      />
      <Route
        path="notas-fiscais/entrada"
        element={
          <ModuleGate modulo="compras">
            <NFEntrada />
          </ModuleGate>
        }
      />
      <Route
        path="campanhas"
        element={
          <ModuleGate modulo="campanhas">
            <Campanhas />
          </ModuleGate>
        }
      />
      <Route
        path="campanhas/canais"
        element={
          <ModuleGate modulo="campanhas">
            <CanalDescontos />
          </ModuleGate>
        }
      />
      <Route
        path="campanhas/estudio-ofertas"
        element={
          <ModuleGate modulo="campanhas">
            <ProtectedRoute permission="vendas.criar">
              <EstudioOfertas />
            </ProtectedRoute>
          </ModuleGate>
        }
      />
      <Route
        path="ecommerce/preview"
        element={
          <ModuleGate modulo="ecommerce">
            <ProtectedRoute permission="configuracoes.editar">
              <EcommercePreview />
            </ProtectedRoute>
          </ModuleGate>
        }
      />
      <Route
        path="ecommerce/divulgacao"
        element={
          <ModuleGate modulo="ecommerce">
            <ProtectedRoute permission="configuracoes.editar">
              <EcommerceDivulgacao />
            </ProtectedRoute>
          </ModuleGate>
        }
      />
      <Route
        path="ecommerce/aparencia"
        element={
          <ModuleGate modulo="ecommerce">
            <ProtectedRoute permission="configuracoes.editar">
              <EcommerceAparencia />
            </ProtectedRoute>
          </ModuleGate>
        }
      />
      <Route
        path="ecommerce/configuracoes"
        element={
          <ModuleGate modulo="ecommerce">
            <ProtectedRoute permission="configuracoes.editar">
              <EcommerceConfig />
            </ProtectedRoute>
          </ModuleGate>
        }
      />
      <Route
        path="ecommerce/catalogo-saude"
        element={
          <ModuleGate modulo="ecommerce">
            <ProtectedRoute anyOfPermissions={["relatorios.gerencial", "vendas.visualizar"]}>
              <EcommerceCatalogHealth />
            </ProtectedRoute>
          </ModuleGate>
        }
      />
      <Route
        path="ecommerce/analytics"
        element={
          <ModuleGate modulo="ecommerce">
            <ProtectedRoute anyOfPermissions={["relatorios.gerencial", "vendas.visualizar"]}>
              <EcommerceAnalytics />
            </ProtectedRoute>
          </ModuleGate>
        }
      />
    </>
  );
}
