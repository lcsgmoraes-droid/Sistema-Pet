import { Route } from "react-router-dom";
import { Observabilidade, OpsDashboard, OpsIncidentes, OpsTenants, StyleGuide } from "../lazyPages";

export function createOpsRoutes() {
  return (
    <>
      <Route index element={<OpsDashboard />} />
      <Route path="incidentes" element={<OpsIncidentes />} />
      <Route path="tenants" element={<OpsTenants />} />
      <Route path="observabilidade" element={<Observabilidade />} />
      <Route path="styleguide" element={<StyleGuide />} />
    </>
  );
}
