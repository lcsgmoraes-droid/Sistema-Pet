import { Navigate, Route } from "react-router-dom";
import { BanhoTosaPage } from "../lazyPages";
import { ModuleGate } from "./RouteGates";

function banhoTosaView(view) {
  return (
    <ModuleGate modulo="banho_tosa">
      <BanhoTosaPage view={view} />
    </ModuleGate>
  );
}

export function createBathGroomingRoutes() {
  return (
    <>
      <Route path="banho-tosa" element={banhoTosaView("dashboard")} />
      <Route path="banho-tosa/servicos" element={banhoTosaView("servicos")} />
      <Route path="banho-tosa/parametros" element={banhoTosaView("parametros")} />
      <Route path="banho-tosa/recursos" element={banhoTosaView("recursos")} />
      <Route path="banho-tosa/agenda" element={banhoTosaView("agenda")} />
      <Route path="banho-tosa/fila" element={banhoTosaView("fila")} />
      <Route path="banho-tosa/fechamentos" element={<Navigate to="/banho-tosa/fila" replace />} />
      <Route path="banho-tosa/pacotes" element={banhoTosaView("pacotes")} />
      <Route path="banho-tosa/retornos" element={banhoTosaView("retornos")} />
      <Route path="banho-tosa/taxi-dog" element={banhoTosaView("taxi-dog")} />
      <Route path="banho-tosa/relatorios" element={banhoTosaView("relatorios")} />
    </>
  );
}
