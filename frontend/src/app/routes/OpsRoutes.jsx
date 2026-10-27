import { Route } from "react-router-dom";
import {
  Observabilidade,
  OpsDashboard,
  OpsIncidentes,
  OpsLojaDetalhe,
  OpsLojas,
  OpsTenants,
  StyleGuide,
} from "../lazyPages";

export function createOpsRoutes() {
  return (
    <>
      <Route index element={<OpsDashboard />} />
      <Route path="incidentes" element={<OpsIncidentes />} />
      <Route path="tenants" element={<OpsTenants />} />
      <Route path="lojas" element={<OpsLojas />} />
      <Route path="lojas/:lojaId" element={<OpsLojaDetalhe />} />
      <Route path="observabilidade" element={<Observabilidade />} />
      <Route path="styleguide" element={<StyleGuide />} />
    </>
  );
}
