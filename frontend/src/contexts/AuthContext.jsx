/**
 * AuthContext - gerenciamento global de autenticacao.
 */
import React, { createContext, useContext, useEffect, useState } from 'react';
import api from '../api';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth deve ser usado dentro de AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const savedUser = localStorage.getItem('user');

        if (token && savedUser) {
          setUser(JSON.parse(savedUser));
          await fetchUser();
        } else {
          setLoading(false);
        }
      } catch (error) {
        console.error('Erro ao inicializar auth:', error);
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  const fetchUser = async () => {
    try {
      const response = await api.get('/auth/me-multitenant');
      setUser(response.data);
      localStorage.setItem('user', JSON.stringify(response.data));
      setLoading(false);
    } catch (error) {
      console.error('Erro ao buscar usuario:', error);

      const status = error.response?.status;
      if (status === 401 || status === 403) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('tenants');
        localStorage.removeItem('user');
        setUser(null);
      } else {
        const savedUser = localStorage.getItem('user');
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
        error: 'Nenhuma empresa disponivel para este usuario',
      };
    }

    localStorage.setItem('tempToken', accessToken);

    const selectResponse = await api.post(
      '/auth/select-tenant',
      { tenant_id: tenants[0].id },
      { headers: { Authorization: `Bearer ${accessToken}` } }
    );

    const finalToken = selectResponse.data.access_token;
    localStorage.setItem('access_token', finalToken);
    localStorage.setItem('selectedTenant', JSON.stringify(tenants[0]));

    const userResponse = await api.get('/auth/me-multitenant');
    setUser(userResponse.data);
    localStorage.setItem('user', JSON.stringify(userResponse.data));

    return { success: true };
  };

  const login = async (email, password) => {
    try {
      const response = await api.post('/auth/login-multitenant', { email, password });
      const { access_token, tenants } = response.data;
      return await completeTenantSelection(access_token, tenants);
    } catch (error) {
      console.error('Erro no login:', error);
      return {
        success: false,
        error: error.response?.data?.detail || 'Erro ao fazer login',
      };
    }
  };

  const register = async ({
    email,
    password,
    nome,
    nome_loja,
    organization_type = 'petshop',
    accepted_terms,
    accepted_privacy,
  }) => {
    try {
      const response = await api.post('/auth/register', {
        email,
        password,
        nome,
        nome_loja,
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
      console.error('Erro no registro:', error);
      return {
        success: false,
        error: error.response?.data?.detail || 'Erro ao criar conta',
      };
    }
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout-multitenant');
    } catch (error) {
      console.error('Erro ao fazer logout:', error);
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('tenants');
      localStorage.removeItem('user');
      localStorage.removeItem('selectedTenant');
      localStorage.removeItem('tempToken');
      setUser(null);
      window.location.href = '/login';
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
