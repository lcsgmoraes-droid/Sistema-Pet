import { Route } from "react-router-dom";
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

export function createVeterinaryRoutes() {
  return (
    <>
      <Route
        path="veterinario"
        element={
          <ModuleGate modulo="veterinario">
            <VetDashboard />
          </ModuleGate>
        }
      />
      <Route
        path="veterinario/agenda"
        element={
          <ModuleGate modulo="veterinario">
            <VetAgenda />
          </ModuleGate>
        }
      />
      <Route
        path="veterinario/consultas"
        element={
          <ModuleGate modulo="veterinario">
            <VetConsultas />
          </ModuleGate>
        }
      />
      <Route
        path="veterinario/consultas/nova"
        element={
          <ModuleGate modulo="veterinario">
            <VetConsultaForm />
          </ModuleGate>
        }
      />
      <Route
        path="veterinario/consultas/:consultaId"
        element={
          <ModuleGate modulo="veterinario">
            <VetConsultaForm />
          </ModuleGate>
        }
      />
      <Route
        path="veterinario/exames"
        element={
          <ModuleGate modulo="veterinario">
            <VetExamesAnexados />
          </ModuleGate>
        }
      />
      <Route
        path="veterinario/ia"
        element={
          <ModuleGate modulo="veterinario">
            <VetAssistenteIA />
          </ModuleGate>
        }
      />
      <Route
        path="veterinario/assistente-ia"
        element={
          <ModuleGate modulo="veterinario">
            <VetAssistenteIA />
          </ModuleGate>
        }
      />
      <Route
        path="veterinario/calculadora-doses"
        element={
          <ModuleGate modulo="veterinario">
            <VetCalculadoraDoses />
          </ModuleGate>
        }
      />
      <Route
        path="veterinario/vacinas"
        element={
          <ModuleGate modulo="veterinario">
            <VetVacinas />
          </ModuleGate>
        }
      />
      <Route
        path="veterinario/internacoes"
        element={
          <ModuleGate modulo="veterinario">
            <VetInternacoes />
          </ModuleGate>
        }
      />
      <Route
        path="veterinario/catalogo"
        element={
          <ModuleGate modulo="veterinario">
            <VetCatalogo />
          </ModuleGate>
        }
      />
      <Route
        path="veterinario/configuracoes"
        element={
          <ModuleGate modulo="veterinario">
            <VetConfiguracoes />
          </ModuleGate>
        }
      />
      <Route
        path="veterinario/repasse"
        element={
          <ModuleGate modulo="veterinario">
            <VetRepasse />
          </ModuleGate>
        }
      />
    </>
  );
}
