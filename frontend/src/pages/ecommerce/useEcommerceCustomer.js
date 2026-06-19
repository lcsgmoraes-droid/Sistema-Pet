import { useEffect, useMemo, useState } from "react";
import ecommerceApi from "../../services/ecommerceApi";
import {
  STORAGE_TOKEN_KEY,
  buildCustomerProfileForm,
  extractApiErrorMessage,
  fetchAddressByCep,
  isCustomerProfileComplete,
} from "./ecommerceMvpUtils";

const EMPTY_PROFILE_FORM = {
  nome: "",
  telefone: "",
  cpf: "",
  cep: "",
  endereco: "",
  numero: "",
  complemento: "",
  bairro: "",
  cidade: "",
  estado: "",
  endereco_entrega: "",
  usar_endereco_entrega_diferente: false,
  entrega_nome: "",
  entrega_cep: "",
  entrega_endereco: "",
  entrega_numero: "",
  entrega_complemento: "",
  entrega_bairro: "",
  entrega_cidade: "",
  entrega_estado: "",
};

const EMPTY_REGISTER_FORM = {
  email: "",
  password: "",
  nome: "",
  cpf: "",
  telefone: "",
  accepted_terms: false,
  accepted_privacy: false,
};

const EMPTY_LOGIN_FORM = { email: "", password: "" };

const EMPTY_RECOVERY_FORM = {
  email: "",
  token: "",
  novaSenha: "",
  confirmarSenha: "",
};

const EMPTY_FIELD_ERROR = { field: "", message: "" };

function isFullName(value) {
  return (
    String(value || "")
      .trim()
      .split(/\s+/)
      .filter(Boolean).length >= 2
  );
}

function normalizeFieldMessage(message) {
  return String(message || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function focusEcommerceField(prefix, field) {
  if (!field || typeof document === "undefined") return;

  window.setTimeout(() => {
    const element = document.querySelector(`[name="${prefix}${field}"]`);
    if (!element) return;

    element.scrollIntoView({ behavior: "smooth", block: "center" });
    if (typeof element.focus === "function") {
      element.focus({ preventScroll: true });
    }
  }, 40);
}

function inferRegisterFieldFromMessage(message) {
  const normalized = normalizeFieldMessage(message);
  if (normalized.includes("nome")) return "nome";
  if (normalized.includes("cpf")) return "cpf";
  if (normalized.includes("telefone") || normalized.includes("celular")) return "telefone";
  if (normalized.includes("senha")) return "password";
  if (normalized.includes("email") || normalized.includes("e-mail")) return "email";
  if (normalized.includes("termo")) return "accepted_terms";
  if (normalized.includes("privacidade")) return "accepted_privacy";
  return "";
}

function inferProfileFieldFromMessage(message) {
  const normalized = normalizeFieldMessage(message);
  if (normalized.includes("entrega") && normalized.includes("nome")) return "entrega_nome";
  if (normalized.includes("entrega")) return "entrega_endereco";
  if (normalized.includes("endereco")) return "endereco";
  return inferRegisterFieldFromMessage(message);
}

export default function useEcommerceCustomer({
  authHeaders,
  customerToken,
  loadCart,
  location,
  navigate,
  restoreGuestCart,
  setCustomerToken,
  setView,
  syncGuestCartToServer,
  tenantContext,
  tenantHeaders,
  onError,
  onSuccess,
}) {
  const [showRegisterPassword, setShowRegisterPassword] = useState(false);
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [showRecoveryPassword, setShowRecoveryPassword] = useState(false);
  const [showRecoveryConfirmPassword, setShowRecoveryConfirmPassword] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const [recoveryLoading, setRecoveryLoading] = useState(false);
  const [customer, setCustomer] = useState(null);
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileForm, setProfileForm] = useState(EMPTY_PROFILE_FORM);
  const [registerForm, setRegisterForm] = useState(EMPTY_REGISTER_FORM);
  const [loginForm, setLoginForm] = useState(EMPTY_LOGIN_FORM);
  const [passwordRecoveryMode, setPasswordRecoveryMode] = useState(false);
  const [recoveryStep, setRecoveryStep] = useState("request");
  const [recoveryTokenFromLink, setRecoveryTokenFromLink] = useState(false);
  const [recoveryForm, setRecoveryForm] = useState(EMPTY_RECOVERY_FORM);
  const [registerFieldError, setRegisterFieldError] = useState(EMPTY_FIELD_ERROR);
  const [profileFieldError, setProfileFieldError] = useState(EMPTY_FIELD_ERROR);

  const isProfileComplete = useMemo(() => {
    return isCustomerProfileComplete(customer);
  }, [customer]);

  const customerDisplayName = customer?.nome || customer?.email || "";

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const recoveryFlag = params.get("recovery");
    const emailParam = params.get("email") || "";
    const tokenParam = params.get("token") || "";

    if (recoveryFlag !== "1" && !emailParam && !tokenParam) {
      return;
    }

    setView("conta");
    setPasswordRecoveryMode(true);
    setRecoveryStep(tokenParam ? "reset" : "request");
    setRecoveryTokenFromLink(Boolean(tokenParam));
    setRecoveryForm((prev) => ({
      ...prev,
      email: emailParam || prev.email,
      token: tokenParam || prev.token,
    }));
  }, [location.search]);

  useEffect(() => {
    if (customerToken) {
      loadMe();
      loadCart();
    }
  }, [customerToken]);

  useEffect(() => {
    if (!customer) return;
    setProfileForm(buildCustomerProfileForm(customer));
  }, [customer]);

  function clearRecoveryParamsFromUrl() {
    const params = new URLSearchParams(location.search);
    params.delete("recovery");
    params.delete("email");
    params.delete("token");
    const nextSearch = params.toString();
    navigate(`${location.pathname}${nextSearch ? `?${nextSearch}` : ""}`, { replace: true });
  }

  function clearCustomerSession() {
    setCustomer(null);
    setCustomerToken("");
    localStorage.removeItem(STORAGE_TOKEN_KEY);
  }

  function clearRegisterFieldError(field) {
    if (!field || registerFieldError.field === field) {
      setRegisterFieldError(EMPTY_FIELD_ERROR);
    }
  }

  function clearProfileFieldError(field) {
    if (!field || profileFieldError.field === field) {
      setProfileFieldError(EMPTY_FIELD_ERROR);
    }
  }

  function showRegisterFieldError(field, message) {
    onError(message);
    onSuccess("");
    setRegisterFieldError({ field, message });
    focusEcommerceField("ecommerce_register_", field);
  }

  function showProfileFieldError(field, message) {
    onError(message);
    onSuccess("");
    setProfileFieldError({ field, message });
    focusEcommerceField("ecommerce_profile_", field);
  }

  async function loadMe() {
    if (!customerToken) return;
    try {
      const response = await ecommerceApi.get("/api/ecommerce/auth/perfil", {
        headers: authHeaders,
      });
      setCustomer(response.data);
    } catch {
      clearCustomerSession();
      restoreGuestCart();
    }
  }

  async function saveProfile(e) {
    e.preventDefault();
    if (!customerToken) {
      onError("Fa\u00e7a login para atualizar seus dados.");
      return;
    }

    const fullName = String(profileForm.nome || "").trim();
    if (!isFullName(fullName)) {
      showProfileFieldError("nome", "Informe nome completo (nome e sobrenome).");
      return;
    }

    const phoneDigits = String(profileForm.telefone || "").replace(/\D/g, "");
    if (phoneDigits.length < 10) {
      showProfileFieldError("telefone", "Informe um telefone/celular valido.");
      return;
    }

    if (profileForm.usar_endereco_entrega_diferente) {
      const requiredDelivery = [
        profileForm.entrega_nome,
        profileForm.entrega_endereco,
        profileForm.entrega_numero,
        profileForm.entrega_bairro,
        profileForm.entrega_cidade,
        profileForm.entrega_estado,
      ].every((item) => String(item || "").trim());

      if (!requiredDelivery) {
        showProfileFieldError(
          "entrega_endereco",
          "Preencha o endereco de entrega completo para continuar.",
        );
        return;
      }
    }

    setProfileSaving(true);
    onError("");
    onSuccess("");
    setProfileFieldError(EMPTY_FIELD_ERROR);
    try {
      const response = await ecommerceApi.put("/api/ecommerce/auth/perfil", profileForm, {
        headers: authHeaders,
      });
      setCustomer(response.data);
      onSuccess("Dados cadastrais atualizados com sucesso.");
    } catch (err) {
      const message = extractApiErrorMessage(err, "Erro ao salvar dados cadastrais");
      const field = inferProfileFieldFromMessage(message);
      if (field) {
        showProfileFieldError(field, message);
      } else {
        onError(message);
      }
    } finally {
      setProfileSaving(false);
    }
  }

  async function handleProfileCepBlur() {
    const data = await fetchAddressByCep(profileForm.cep);
    if (!data) return;
    setProfileForm((prev) => ({
      ...prev,
      cep: data.cep || prev.cep,
      endereco: data.endereco || prev.endereco,
      bairro: data.bairro || prev.bairro,
      cidade: data.cidade || prev.cidade,
      estado: data.estado || prev.estado,
    }));
  }

  async function handleDeliveryCepBlur() {
    const data = await fetchAddressByCep(profileForm.entrega_cep);
    if (!data) return;
    setProfileForm((prev) => ({
      ...prev,
      entrega_cep: data.cep || prev.entrega_cep,
      entrega_endereco: data.endereco || prev.entrega_endereco,
      entrega_bairro: data.bairro || prev.entrega_bairro,
      entrega_cidade: data.cidade || prev.entrega_cidade,
      entrega_estado: data.estado || prev.entrega_estado,
    }));
  }

  function openPasswordRecovery(nextStep = "request") {
    setView("conta");
    setPasswordRecoveryMode(true);
    setRecoveryStep(nextStep);
    setRecoveryTokenFromLink(false);
    onError("");
    onSuccess("");
    setRecoveryForm((prev) => ({
      ...prev,
      email: prev.email || loginForm.email || registerForm.email || customer?.email || "",
      token: nextStep === "request" ? "" : prev.token,
      novaSenha: "",
      confirmarSenha: "",
    }));
  }

  function closePasswordRecovery() {
    setPasswordRecoveryMode(false);
    setRecoveryStep("request");
    setRecoveryTokenFromLink(false);
    setShowRecoveryPassword(false);
    setShowRecoveryConfirmPassword(false);
    setRecoveryForm((prev) => ({
      ...prev,
      token: "",
      novaSenha: "",
      confirmarSenha: "",
    }));
    clearRecoveryParamsFromUrl();
  }

  async function handlePasswordRecoveryRequest(e) {
    e.preventDefault();
    if (!tenantContext?.id) {
      onError("Loja n\u00e3o identificada na URL.");
      return;
    }

    const normalizedEmail = recoveryForm.email.trim().toLowerCase();
    if (!normalizedEmail) {
      onError("Informe o e-mail da conta para continuar.");
      return;
    }

    setRecoveryLoading(true);
    onError("");
    onSuccess("");
    try {
      const response = await ecommerceApi.post(
        "/api/ecommerce/auth/esqueci-senha",
        { email: normalizedEmail, canal: "site" },
        { headers: tenantHeaders },
      );
      const minutes = response?.data?.expires_in_minutes;
      setRecoveryStep("request");
      setRecoveryForm((prev) => ({
        ...prev,
        email: normalizedEmail,
        token: "",
        novaSenha: "",
        confirmarSenha: "",
      }));
      setRecoveryTokenFromLink(false);
      onSuccess(
        minutes
          ? `Se o e-mail existir, enviamos um link e um codigo de recuperacao. Abra o ultimo e-mail recebido ou clique em "Ja tenho o codigo". Eles expiram em ${minutes} minutos.`
          : "Se o e-mail existir, enviamos as instru\u00e7\u00f5es de recupera\u00e7\u00e3o.",
      );
    } catch (err) {
      onError(
        extractApiErrorMessage(
          err,
          "N\u00e3o foi poss\u00edvel iniciar a recupera\u00e7\u00e3o agora.",
        ),
      );
    } finally {
      setRecoveryLoading(false);
    }
  }

  async function handlePasswordRecoveryReset(e) {
    e.preventDefault();
    if (!tenantContext?.id) {
      onError("Loja n\u00e3o identificada na URL.");
      return;
    }

    const normalizedEmail = recoveryForm.email.trim().toLowerCase();
    const token = recoveryForm.token.trim();

    if (!normalizedEmail || !token) {
      onError(
        recoveryTokenFromLink
          ? "Link de recuperacao invalido. Solicite um novo link."
          : "Preencha o e-mail e o codigo recebido.",
      );
      return;
    }

    if ((recoveryForm.novaSenha || "").length < 8) {
      onError("A nova senha deve ter pelo menos 8 caracteres.");
      return;
    }

    if (recoveryForm.novaSenha !== recoveryForm.confirmarSenha) {
      onError("A confirma\u00e7\u00e3o da senha n\u00e3o confere.");
      return;
    }

    setRecoveryLoading(true);
    onError("");
    onSuccess("");
    try {
      await ecommerceApi.post(
        "/api/ecommerce/auth/resetar-senha",
        {
          email: normalizedEmail,
          token,
          nova_senha: recoveryForm.novaSenha,
        },
        { headers: tenantHeaders },
      );
      setLoginForm({ email: normalizedEmail, password: "" });
      setRecoveryForm({
        email: normalizedEmail,
        token: "",
        novaSenha: "",
        confirmarSenha: "",
      });
      setPasswordRecoveryMode(false);
      setRecoveryStep("request");
      setRecoveryTokenFromLink(false);
      setShowRecoveryPassword(false);
      setShowRecoveryConfirmPassword(false);
      clearRecoveryParamsFromUrl();
      onSuccess("Senha atualizada com sucesso. Agora \u00e9 s\u00f3 entrar com a nova senha.");
    } catch (err) {
      onError(extractApiErrorMessage(err, "N\u00e3o foi poss\u00edvel redefinir a senha."));
    } finally {
      setRecoveryLoading(false);
    }
  }

  async function handleRegister(e) {
    e.preventDefault();
    if (!tenantContext?.id) {
      onError("Loja n\u00e3o identificada na URL.");
      return;
    }
    if (!isFullName(registerForm.nome)) {
      showRegisterFieldError("nome", "Informe nome completo (nome e sobrenome).");
      return;
    }
    const cpfDigits = (registerForm.cpf || "").replace(/\D/g, "");
    if (cpfDigits.length !== 11) {
      showRegisterFieldError("cpf", "Informe um CPF valido com 11 digitos.");
      return;
    }
    const phoneDigits = (registerForm.telefone || "").replace(/\D/g, "");
    if (phoneDigits.length < 10) {
      showRegisterFieldError("telefone", "Informe um telefone/celular valido.");
      return;
    }
    const normalizedEmail = registerForm.email.trim().toLowerCase();
    if (!normalizedEmail) {
      showRegisterFieldError("email", "Informe seu e-mail.");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
      showRegisterFieldError("email", "Informe um e-mail valido.");
      return;
    }
    if ((registerForm.password || "").length < 8) {
      showRegisterFieldError("password", "A senha deve ter pelo menos 8 caracteres.");
      return;
    }
    if (!registerForm.accepted_terms) {
      showRegisterFieldError("accepted_terms", "Aceite os Termos de Uso para criar a conta.");
      return;
    }
    if (!registerForm.accepted_privacy) {
      showRegisterFieldError(
        "accepted_privacy",
        "Aceite a Politica de Privacidade para criar a conta.",
      );
      return;
    }
    setAuthLoading(true);
    onError("");
    onSuccess("");
    setRegisterFieldError(EMPTY_FIELD_ERROR);
    try {
      const response = await ecommerceApi.post(
        "/api/ecommerce/auth/registrar",
        { ...registerForm, email: normalizedEmail },
        {
          headers: tenantHeaders,
        },
      );
      if (response?.data?.requires_email_verification) {
        setRegisterForm(EMPTY_REGISTER_FORM);
        setRegisterFieldError(EMPTY_FIELD_ERROR);
        setPasswordRecoveryMode(false);
        setRecoveryStep("request");
        clearRecoveryParamsFromUrl();
        onSuccess(
          "Cadastro realizado. Enviamos um link de confirmacao para o seu e-mail antes do primeiro acesso.",
        );
        return;
      }
      const token = response?.data?.access_token;
      if (!token) throw new Error("Token n\u00e3o retornado");
      if (response?.data?.user) {
        setCustomer(response.data.user);
      }
      localStorage.setItem(STORAGE_TOKEN_KEY, token);
      setCustomerToken(token);
      await syncGuestCartToServer(token);
      setRegisterForm(EMPTY_REGISTER_FORM);
      setRegisterFieldError(EMPTY_FIELD_ERROR);
      setPasswordRecoveryMode(false);
      setRecoveryStep("request");
      clearRecoveryParamsFromUrl();
      onSuccess("Cadastro realizado com sucesso!");
      setView("conta");
    } catch (err) {
      const message = extractApiErrorMessage(err, "Erro ao cadastrar cliente");
      const field = inferRegisterFieldFromMessage(message);
      if (field) {
        showRegisterFieldError(field, message);
      } else {
        onError(message);
      }
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleLogin(e) {
    e.preventDefault();
    if (!tenantContext?.id) {
      onError("Loja n\u00e3o identificada na URL.");
      return;
    }
    setAuthLoading(true);
    onError("");
    onSuccess("");
    try {
      const response = await ecommerceApi.post("/api/ecommerce/auth/login", loginForm, {
        headers: tenantHeaders,
      });
      const token = response?.data?.access_token;
      if (!token) throw new Error("Token n\u00e3o retornado");
      if (response?.data?.user) {
        setCustomer(response.data.user);
      }
      localStorage.setItem(STORAGE_TOKEN_KEY, token);
      setCustomerToken(token);
      await syncGuestCartToServer(token);
      setLoginForm(EMPTY_LOGIN_FORM);
      setPasswordRecoveryMode(false);
      setRecoveryStep("request");
      clearRecoveryParamsFromUrl();
      onSuccess("Login realizado com sucesso. Confira seus dados cadastrais.");
      setView("conta");
    } catch (err) {
      onError(extractApiErrorMessage(err, "Erro ao realizar login"));
    } finally {
      setAuthLoading(false);
    }
  }

  return {
    authLoading,
    clearCustomerSession,
    clearProfileFieldError,
    clearRegisterFieldError,
    closePasswordRecovery,
    customer,
    customerDisplayName,
    handleDeliveryCepBlur,
    handleLogin,
    handlePasswordRecoveryRequest,
    handlePasswordRecoveryReset,
    handleProfileCepBlur,
    handleRegister,
    isProfileComplete,
    loginForm,
    openPasswordRecovery,
    passwordRecoveryMode,
    profileFieldError,
    profileForm,
    profileSaving,
    recoveryForm,
    recoveryLoading,
    recoveryStep,
    recoveryTokenFromLink,
    registerFieldError,
    registerForm,
    saveProfile,
    setLoginForm,
    setProfileForm,
    setRecoveryForm,
    setRecoveryStep,
    setRecoveryTokenFromLink,
    setRegisterForm,
    setShowLoginPassword,
    setShowRecoveryConfirmPassword,
    setShowRecoveryPassword,
    setShowRegisterPassword,
    showLoginPassword,
    showRecoveryConfirmPassword,
    showRecoveryPassword,
    showRegisterPassword,
  };
}
