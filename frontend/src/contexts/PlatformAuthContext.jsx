import { createContext, useContext, useEffect, useState } from "react";

import {
  clearPlatformAuthTokens,
  getPlatformAccessToken,
  setPlatformAccessToken,
  setPlatformRefreshToken,
} from "../auth/platformTokenStorage";
import platformApi from "../platformApi";

const PlatformAuthContext = createContext(null);

export function usePlatformAuth() {
  const context = useContext(PlatformAuthContext);
  if (!context) throw new Error("usePlatformAuth requer PlatformAuthProvider");
  return context;
}

export function PlatformAuthProvider({ children }) {
  const [admin, setAdmin] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function initialize() {
      if (!getPlatformAccessToken()) {
        localStorage.removeItem("platform_admin");
        setLoading(false);
        return;
      }
      try {
        const response = await platformApi.get("/platform-auth/me");
        setAdmin(response.data);
        localStorage.setItem("platform_admin", JSON.stringify(response.data));
      } catch {
        clearPlatformAuthTokens();
        localStorage.removeItem("platform_admin");
        setAdmin(null);
      } finally {
        setLoading(false);
      }
    }
    initialize();
  }, []);

  async function login(email, password) {
    try {
      const response = await platformApi.post("/platform-auth/login", { email, password });
      setPlatformAccessToken(response.data.access_token);
      setPlatformRefreshToken(response.data.refresh_token);
      setAdmin(response.data.admin);
      localStorage.setItem("platform_admin", JSON.stringify(response.data.admin));
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || "Não foi possível entrar no CorePet Ops",
      };
    }
  }

  async function logout() {
    try {
      await platformApi.post("/platform-auth/logout");
    } catch {
      // A limpeza local deve ocorrer mesmo se a sessão já tiver expirado.
    } finally {
      clearPlatformAuthTokens();
      localStorage.removeItem("platform_admin");
      setAdmin(null);
      globalThis.location.href = "/ops/login";
    }
  }

  return (
    <PlatformAuthContext.Provider
      value={{ admin, loading, login, logout, isAuthenticated: Boolean(admin) }}
    >
      {children}
    </PlatformAuthContext.Provider>
  );
}
