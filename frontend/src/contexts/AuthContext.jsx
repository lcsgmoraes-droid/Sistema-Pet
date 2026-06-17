/**
 * AuthContext - gerenciamento global de autenticacao.
 */
import { createContext, useContext, useEffect, useState } from "react";
import api from "../api";
import {
  clearAuthTokens,
  getAccessToken,
  setAccessToken,
  setRefreshToken,
  setTempToken,
} from "../auth/tokenStorage";

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

  const completeTenantSelection = async (accessToken, tenants) => {
    if (!accessToken || !tenants || tenants.length === 0) {
      return {
        success: false,
        error: "Nenhuma empresa disponivel para este usuario",
      };
    }

    setTempToken(accessToken);

    const selectResponse = await api.post(
      "/auth/select-tenant",
      { tenant_id: tenants[0].id },
      { headers: { Authorization: `Bearer ${accessToken}` } },
    );

    const finalToken = selectResponse.data.access_token;
    const finalRefreshToken = selectResponse.data.refresh_token;
    setAccessToken(finalToken);
    if (finalRefreshToken) {
      setRefreshToken(finalRefreshToken);
    }
    localStorage.setItem("selectedTenant", JSON.stringify(tenants[0]));

    const userResponse = await api.get("/auth/me-multitenant");
    setUser(userResponse.data);
    localStorage.setItem("user", JSON.stringify(userResponse.data));

    return { success: true };
  };

  const login = async (email, password) => {
    try {
      const response = await api.post("/auth/login-multitenant", { email, password });
      const { access_token, tenants } = response.data;
      return await completeTenantSelection(access_token, tenants);
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
      return await completeTenantSelection(access_token, tenants);
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
    register,
    logout,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
