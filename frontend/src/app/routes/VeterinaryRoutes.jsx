import { Route } from "react-router-dom";
import ProtectedRoute from "../../components/ProtectedRoute";
import {
  VetAgenda,
  VetAssistenteIA,
  VetCalculadoraDoses,
  VetCatalogo,
  VetConfiguracoes,
  VetConsultaForm,
  VetConsultas,
  VetDashboard,
  VetExamesAnexados,
  VetInternacoes,
  VetRepasse,
  VetVacinas,
} from "../lazyPages";
import { ModuleGate } from "./RouteGates";

function veterinaryPage(children) {
  return (
    <ModuleGate modulo="veterinario">
      <ProtectedRoute permission="veterinario.acessar">{children}</ProtectedRoute>
    </ModuleGate>
  );
}

export function createVeterinaryRoutes() {
  return (
    <>
      <Route path="veterinario" element={veterinaryPage(<VetDashboard />)} />
      <Route path="veterinario/agenda" element={veterinaryPage(<VetAgenda />)} />
      <Route path="veterinario/consultas" element={veterinaryPage(<VetConsultas />)} />
      <Route path="veterinario/consultas/nova" element={veterinaryPage(<VetConsultaForm />)} />
      <Route
        path="veterinario/consultas/:consultaId"
        element={veterinaryPage(<VetConsultaForm />)}
      />
      <Route path="veterinario/exames" element={veterinaryPage(<VetExamesAnexados />)} />
      <Route path="veterinario/ia" element={veterinaryPage(<VetAssistenteIA />)} />
      <Route path="veterinario/assistente-ia" element={veterinaryPage(<VetAssistenteIA />)} />
      <Route
        path="veterinario/calculadora-doses"
        element={veterinaryPage(<VetCalculadoraDoses />)}
      />
      <Route path="veterinario/vacinas" element={veterinaryPage(<VetVacinas />)} />
      <Route path="veterinario/internacoes" element={veterinaryPage(<VetInternacoes />)} />
      <Route path="veterinario/catalogo" element={veterinaryPage(<VetCatalogo />)} />
      <Route path="veterinario/configuracoes" element={veterinaryPage(<VetConfiguracoes />)} />
      <Route path="veterinario/repasse" element={veterinaryPage(<VetRepasse />)} />
    </>
  );
}
