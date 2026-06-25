import { Navigate, Route } from "react-router-dom";
import ProtectedRoute from "../../components/ProtectedRoute";
import {
  BlingFlowMonitor,
  ComprasPendencias,
  EntradaXML,
  EstoqueBling,
  PedidosBling,
  PedidosCompra,
} from "../lazyPages";
import { ModuleGate } from "./RouteGates";

function comprasPage(children) {
  return (
    <ModuleGate modulo="compras">
      <ProtectedRoute permission="compras.gerenciar">{children}</ProtectedRoute>
    </ModuleGate>
  );
}

function blingPage(children) {
  return (
    <ModuleGate modulo="bling">
      <ProtectedRoute permission="compras.gerenciar">{children}</ProtectedRoute>
    </ModuleGate>
  );
}

export function createPurchasingBlingRoutes() {
  return (
    <>
      <Route path="compras/pedidos" element={comprasPage(<PedidosCompra />)} />
      <Route path="compras/entrada-xml" element={comprasPage(<EntradaXML />)} />
      <Route path="compras/pendencias" element={comprasPage(<ComprasPendencias />)} />
      <Route path="produtos/sinc-bling" element={blingPage(<EstoqueBling />)} />
      <Route path="compras/bling" element={<Navigate to="/produtos/sinc-bling" replace />} />
      <Route path="vendas/bling-pedidos" element={blingPage(<PedidosBling />)} />
      <Route path="vendas/bling-monitor" element={blingPage(<BlingFlowMonitor />)} />
    </>
  );
}
