import { Route } from "react-router-dom";
import {
  AppPaymentReturn,
  AppPublicEntry,
  EcommerceMVP,
  EmailVerification,
  ForgotPassword,
  LandingPage,
  LegalPage,
  Login,
  Planos,
  RastreioPublico,
  Register,
  VendasCanaisPreview,
} from "../lazyPages";

export function createPublicRoutes() {
  return (
    <>
      <Route path="/login" element={<Login />} />
      <Route path="/recuperar-senha" element={<ForgotPassword />} />
      <Route path="/register" element={<Register />} />
      <Route path="/verificar-email" element={<EmailVerification />} />
      <Route path="/termos" element={<LegalPage type="termos" />} />
      <Route path="/privacidade" element={<LegalPage type="privacidade" />} />
      <Route path="/landing" element={<LandingPage />} />
      <Route path="/planos" element={<Planos />} />
      <Route path="/rastreio/:token" element={<RastreioPublico />} />
      <Route path="/app" element={<AppPublicEntry />} />
      <Route path="/app/retorno-pagamento" element={<AppPaymentReturn />} />
      <Route path="/ecommerce" element={<EcommerceMVP />} />
      {VendasCanaisPreview && (
        <Route path="/dev/vendas-canais-preview" element={<VendasCanaisPreview />} />
      )}
      <Route path="/:tenantId" element={<EcommerceMVP />} />
    </>
  );
}
