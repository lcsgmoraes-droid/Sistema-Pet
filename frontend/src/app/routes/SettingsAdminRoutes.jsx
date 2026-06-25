import { Navigate, Route } from "react-router-dom";
import ProtectedRoute from "../../components/ProtectedRoute";
import {
  Ajuda,
  AuditoriaMensal,
  ConfiguracaoEstoque,
  ConfiguracaoFiscalEmpresa,
  ConfiguracaoGeralNegocio,
  Configuracoes,
  CustosMoto,
  EntregasConfig,
  Funcionarios,
  Integracoes,
  LGPDOperacional,
  ProjecaoCaixa,
  RolesPage,
  SimulacaoContratacao,
  UsuariosPage,
} from "../lazyPages";
import { ModuleGate } from "./RouteGates";

export function createSettingsAdminRoutes() {
  return (
    <>
      <Route
        path="admin/usuarios"
        element={
          <ProtectedRoute permission="usuarios.manage">
            <UsuariosPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="configuracoes"
        element={
          <ProtectedRoute permission="configuracoes.editar">
            <Configuracoes />
          </ProtectedRoute>
        }
      />
      <Route
        path="configuracoes/fiscal"
        element={
          <ProtectedRoute anyOfPermissions={["configuracoes.empresa", "configuracoes.editar"]}>
            <ConfiguracaoFiscalEmpresa />
          </ProtectedRoute>
        }
      />
      <Route
        path="configuracoes/geral"
        element={
          <ProtectedRoute permission="configuracoes.editar">
            <ConfiguracaoGeralNegocio />
          </ProtectedRoute>
        }
      />
      <Route
        path="configuracoes/entregas"
        element={
          <ModuleGate modulo="entregas">
            <EntregasConfig />
          </ModuleGate>
        }
      />
      <Route
        path="configuracoes/custos-moto"
        element={
          <ModuleGate modulo="entregas">
            <CustosMoto />
          </ModuleGate>
        }
      />
      <Route
        path="configuracoes/estoque"
        element={
          <ProtectedRoute permission="configuracoes.editar">
            <ConfiguracaoEstoque />
          </ProtectedRoute>
        }
      />
      <Route
        path="configuracoes/integracoes"
        element={
          <ModuleGate modulo="integracoes">
            <Integracoes />
          </ModuleGate>
        }
      />
      {/* <Route path="configuracoes/simples/fechamento" element={<FechamentoSimples />} /> */}
      <Route
        path="auditoria/provisoes"
        element={
          <ModuleGate modulo="financeiro_erp">
            <AuditoriaMensal />
          </ModuleGate>
        }
      />
      <Route
        path="projecao-caixa"
        element={
          <ModuleGate modulo="financeiro_erp">
            <ProjecaoCaixa />
          </ModuleGate>
        }
      />
      <Route
        path="simulacao-contratacao"
        element={
          <ModuleGate modulo="rh">
            <SimulacaoContratacao />
          </ModuleGate>
        }
      />
      <Route
        path="rh/funcionarios"
        element={
          <ModuleGate modulo="rh">
            <Funcionarios />
          </ModuleGate>
        }
      />
      <Route
        path="admin/roles"
        element={
          <ProtectedRoute permission="usuarios.manage">
            <RolesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="admin/lgpd"
        element={
          <ProtectedRoute permission="usuarios.manage">
            <LGPDOperacional />
          </ProtectedRoute>
        }
      />
      <Route path="lgpd" element={<Navigate to="/admin/lgpd" replace />} />
      <Route
        path="admin/observabilidade"
        element={<Navigate to="/ops/observabilidade" replace />}
      />
      <Route path="ajuda" element={<Ajuda />} />
    </>
  );
}
