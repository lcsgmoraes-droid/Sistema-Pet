import { Navigate, Route } from "react-router-dom";
import ProtectedRoute from "../../components/ProtectedRoute";
import {
  Campanhas,
  CanalDescontos,
  CentralNFSaida,
  EcommerceAnalytics,
  EcommerceAparencia,
  EcommerceConfig,
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
        path="ecommerce/aparencia"
        element={
          <ModuleGate modulo="ecommerce">
            <EcommerceAparencia />
          </ModuleGate>
        }
      />
      <Route
        path="ecommerce/configuracoes"
        element={
          <ModuleGate modulo="ecommerce">
            <EcommerceConfig />
          </ModuleGate>
        }
      />
      <Route
        path="ecommerce/analytics"
        element={
          <ModuleGate modulo="ecommerce">
            <EcommerceAnalytics />
          </ModuleGate>
        }
      />
    </>
  );
}
