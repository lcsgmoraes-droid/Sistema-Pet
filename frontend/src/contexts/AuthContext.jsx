/**
 * AuthContext - gerenciamento global de autenticacao.
 */
import { createContext, useContext, useEffect, useState } from "react";
import api from "../api";
import {
  clearTempToken,
  clearAuthTokens,
  getAccessToken,
  getTempToken,
  setAccessToken,
  setRefreshToken,
  setTempToken,
} from "../auth/tokenStorage";
import { findTenantOption, normalizeTenantOptions } from "../auth/tenantSelection";

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth deve ser usado dentro de AuthProvider");
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      try {
        const token = getAccessToken();
        const savedUser = localStorage.getItem("user");

        if (token && savedUser) {
          await fetchUser();
        } else {
          if (!token) {
            localStorage.removeItem("user");
            localStorage.removeItem("tenants");
            localStorage.removeItem("selectedTenant");
          }
          setLoading(false);
        }
      } catch (error) {
        console.error("Erro ao inicializar auth:", error);
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  const fetchUser = async () => {
    try {
      const response = await api.get("/auth/me-multitenant");
      setUser(response.data);
      localStorage.setItem("user", JSON.stringify(response.data));
      setLoading(false);
    } catch (error) {
      const status = error.response?.status;
      if (status === 401 || status === 403) {
        console.warn("Sessao expirada ou tenant invalido. Limpando autenticacao local.");
        clearAuthTokens();
        localStorage.removeItem("tenants");
        localStorage.removeItem("user");
        localStorage.removeItem("selectedTenant");
        setUser(null);
      } else {
        console.error("Erro ao buscar usuario:", error);
        const savedUser = localStorage.getItem("user");
        if (savedUser) {
          try {
            setUser(JSON.parse(savedUser));
          } catch {
            setUser(null);
          }
        } else {
          setUser(null);
        }
      }
      setLoading(false);
    }
  };

  const completeTenantSelection = async (accessToken, tenant) => {
    if (!accessToken || !tenant?.id) {
      return {
        success: false,
        error: "Nenhuma empresa disponivel para este usuario",
      };
    }

    setTempToken(accessToken);

    const selectResponse = await api.post(
      "/auth/select-tenant",
      { tenant_id: tenant.id },
      { headers: { Authorization: `Bearer ${accessToken}` } },
    );

    const finalToken = selectResponse.data.access_token;
    const finalRefreshToken = selectResponse.data.refresh_token;
    setAccessToken(finalToken);
    if (finalRefreshToken) {
      setRefreshToken(finalRefreshToken);
    }
    localStorage.setItem("selectedTenant", JSON.stringify(tenant));
    localStorage.removeItem("tenants");
    clearTempToken();

    const userResponse = await api.get("/auth/me-multitenant");
    setUser(userResponse.data);
    localStorage.setItem("user", JSON.stringify(userResponse.data));

    return { success: true };
  };

  const prepareTenantSelection = async (accessToken, tenants) => {
    const tenantOptions = normalizeTenantOptions(tenants);

    if (!accessToken || tenantOptions.length === 0) {
      return {
        success: false,
        error: "Nenhuma empresa disponivel para este usuario",
      };
    }

    setTempToken(accessToken);

    if (tenantOptions.length === 1) {
      return completeTenantSelection(accessToken, tenantOptions[0]);
    }

    localStorage.setItem("tenants", JSON.stringify(tenantOptions));
    return {
      success: true,
      requiresTenantSelection: true,
      tenants: tenantOptions,
    };
  };

  const selectTenant = async (tenantId) => {
    try {
      const accessToken = getTempToken();
      const savedTenants = JSON.parse(localStorage.getItem("tenants") || "[]");
      const tenant = findTenantOption(savedTenants, tenantId);

      if (!accessToken || !tenant) {
        return {
          success: false,
          error: "A selecao de empresa expirou. Faca login novamente.",
        };
      }

      return await completeTenantSelection(accessToken, tenant);
    } catch (error) {
      console.error("Erro ao selecionar empresa:", error);
      return {
        success: false,
        error: error.response?.data?.detail || "Erro ao selecionar empresa",
      };
    }
  };

  const cancelTenantSelection = async () => {
    const accessToken = getTempToken();

    try {
      if (accessToken) {
        await api.post(
          "/auth/logout-multitenant",
          {},
          { headers: { Authorization: `Bearer ${accessToken}` } },
        );
      }
    } catch (error) {
      console.warn("Nao foi possivel encerrar a selecao de empresa:", error);
    } finally {
      clearTempToken();
      localStorage.removeItem("tenants");
    }
  };

  const login = async (identifier, password, tenant = null) => {
    try {
      const response = await api.post("/auth/login-multitenant", {
        identifier,
        password,
        tenant,
      });
      const { access_token, tenants } = response.data;
      return await prepareTenantSelection(access_token, tenants);
    } catch (error) {
      console.error("Erro no login:", error);
      return {
        success: false,
        error: error.response?.data?.detail || "Erro ao fazer login",
      };
    }
  };

  const register = async ({
    email,
    password,
    nome,
    nome_loja,
    plan = "basico",
    organization_type = "petshop",
    accepted_terms,
    accepted_privacy,
  }) => {
    try {
      const response = await api.post("/auth/register", {
        email,
        password,
        nome,
        nome_loja,
        plan,
        organization_type,
        accepted_terms,
        accepted_privacy,
      });

      if (response.data?.requires_email_verification) {
        return {
          success: true,
          requiresEmailVerification: true,
          email,
        };
      }

      const { access_token, tenants } = response.data;
      return await prepareTenantSelection(access_token, tenants);
    } catch (error) {
      console.error("Erro no registro:", error);
      return {
        success: false,
        error: error.response?.data?.detail || "Erro ao criar conta",
      };
    }
  };

  const logout = async () => {
    try {
      await api.post("/auth/logout-multitenant");
    } catch (error) {
      console.error("Erro ao fazer logout:", error);
    } finally {
      clearAuthTokens();
      localStorage.removeItem("tenants");
      localStorage.removeItem("user");
      localStorage.removeItem("selectedTenant");
      setUser(null);
      window.location.href = "/login";
    }
  };

  const value = {
    user,
    loading,
    login,
    selectTenant,
    cancelTenantSelection,
    register,
    logout,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
