import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "../components/Layout";
import OpsLayout from "../components/OpsLayout";
import ProtectedRoute from "../components/ProtectedRoute";
import { createBathGroomingRoutes } from "./routes/BathGroomingRoutes";
import { createCatalogAdminRoutes } from "./routes/CatalogAdminRoutes";
import { createCommissionRoutes } from "./routes/CommissionRoutes";
import { createCoreProtectedRoutes } from "./routes/CoreProtectedRoutes";
import { createDeliveryAiRoutes } from "./routes/DeliveryAiRoutes";
import { createFinanceRoutes } from "./routes/FinanceRoutes";
import { createOpsRoutes } from "./routes/OpsRoutes";
import { createProductInventoryRoutes } from "./routes/ProductInventoryRoutes";
import { createPublicRoutes } from "./routes/PublicRoutes";
import { createPurchasingBlingRoutes } from "./routes/PurchasingBlingRoutes";
import { createSalesMarketingRoutes } from "./routes/SalesMarketingRoutes";
import { createSettingsAdminRoutes } from "./routes/SettingsAdminRoutes";
import { createVeterinaryRoutes } from "./routes/VeterinaryRoutes";

export default function AppRoutes() {
  return (
    <Routes>
      {createPublicRoutes()}

      <Route
        path="/ops"
        element={
          <ProtectedRoute permission="usuarios.manage">
            <OpsLayout />
          </ProtectedRoute>
        }
      >
        {createOpsRoutes()}
      </Route>

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        {createCoreProtectedRoutes()}
        {createVeterinaryRoutes()}
        {createBathGroomingRoutes()}
        {createProductInventoryRoutes()}
        {createSalesMarketingRoutes()}
        {createPurchasingBlingRoutes()}
        {createFinanceRoutes()}
        {createCommissionRoutes()}
        {createCatalogAdminRoutes()}
        {createSettingsAdminRoutes()}
        {createDeliveryAiRoutes()}
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
