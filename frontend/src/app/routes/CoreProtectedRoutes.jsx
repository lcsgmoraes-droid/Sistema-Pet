import { Navigate, Route } from "react-router-dom";
import ProtectedRoute from "../../components/ProtectedRoute";
import {
  ClienteFinanceiro,
  ClienteTimelinePage,
  DashboardFinanceiro,
  GerenciamentoPets,
  MeuPlano,
  Pessoas,
  PetDetalhes,
  PetForm,
} from "../lazyPages";
import { DefaultProtectedHomeRedirect } from "./RouteGates";

export function createCoreProtectedRoutes() {
  return (
    <>
      <Route index element={<DefaultProtectedHomeRedirect />} />
      <Route path="meu-plano" element={<MeuPlano />} />
      <Route
        path="dashboard"
        element={
          <ProtectedRoute permission="relatorios.gerencial">
            <DashboardFinanceiro />
          </ProtectedRoute>
        }
      />
      <Route path="dashboard-gerencial" element={<Navigate to="/dashboard" replace />} />
      <Route
        path="clientes"
        element={
          <ProtectedRoute permission="clientes.visualizar">
            <Pessoas />
          </ProtectedRoute>
        }
      />
      <Route
        path="clientes/:clienteId/financeiro"
        element={
          <ProtectedRoute permission="clientes.visualizar">
            <ClienteFinanceiro />
          </ProtectedRoute>
        }
      />
      <Route
        path="clientes/:clienteId/timeline"
        element={
          <ProtectedRoute permission="clientes.visualizar">
            <ClienteTimelinePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="pets"
        element={
          <ProtectedRoute permission="clientes.visualizar">
            <GerenciamentoPets />
          </ProtectedRoute>
        }
      />
      <Route
        path="pets/novo"
        element={
          <ProtectedRoute permission="clientes.visualizar">
            <PetForm />
          </ProtectedRoute>
        }
      />
      <Route
        path="pets/:petId"
        element={
          <ProtectedRoute permission="clientes.visualizar">
            <PetDetalhes />
          </ProtectedRoute>
        }
      />
      <Route
        path="pets/:petId/editar"
        element={
          <ProtectedRoute permission="clientes.visualizar">
            <PetForm />
          </ProtectedRoute>
        }
      />
    </>
  );
}
