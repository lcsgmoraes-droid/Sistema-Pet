/**
 * AuthContext - Gerenciamento de autenticação global
 */
import React, { createContext, useState, useContext, useEffect } from 'react';
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

  // Carregar usuário do localStorage ao iniciar
  useEffect(() => {
    const initAuth = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const savedUser = localStorage.getItem('user');
        
        if (token && savedUser) {
          setUser(JSON.parse(savedUser));
          // Validar token buscando dados do usuário
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
      console.error('Erro ao buscar usuário:', error);

      const status = error.response?.status;

      // Só descarta a sessão em erros de autenticação (401) ou acesso negado (403).
      // Erros 5xx (502, 503) são falhas TEMPORÁRIAS do servidor — não devem derrubar a sessão.
      if (status === 401 || status === 403) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('tenants');
        localStorage.removeItem('user');
        setUser(null);
      } else {
        // Servidor temporariamente indisponível: usa dados do localStorage como fallback
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

  const login = async (email, password) => {
    try {
      console.log('🔐 Iniciando login para:', email);
      
      // Fase 1: Login multi-tenant (retorna token + lista de tenants)
      const response = await api.post('/auth/login-multitenant', { email, password });
      const { access_token, tenants } = response.data;
      
      console.log('✅ Login fase 1 OK - Tenants:', tenants.length);
      
      // Se houver tenants, seleciona o primeiro automaticamente
      if (tenants && tenants.length > 0) {
        localStorage.setItem('tempToken', access_token);
        
        console.log('📍 Selecionando tenant:', tenants[0].name);
        
        // Fase 2: Selecionar tenant (sempre o primeiro)
        const selectResponse = await api.post('/auth/select-tenant', 
          { tenant_id: tenants[0].id },
          { headers: { Authorization: `Bearer ${access_token}` }}
        );
        
        const finalToken = selectResponse.data.access_token;
        localStorage.setItem('access_token', finalToken);
        localStorage.setItem('selectedTenant', JSON.stringify(tenants[0]));
        
        console.log('✅ Tenant selecionado OK');
        
        // Buscar dados do usuário
        const userResponse = await api.get('/auth/me-multitenant');
        setUser(userResponse.data);
        localStorage.setItem('user', JSON.stringify(userResponse.data));
        
        console.log('✅ Login completo! Redirecionando...');
        
        return { success: true };
      } else {
        // Sem tenants disponíveis
        console.error('❌ Nenhum tenant disponível');
        return { 
          success: false,
          error: 'Nenhuma empresa disponível para este usuário'
        };
      }
    } catch (error) {
      console.error('Erro no login:', error);
      return {
        success: false,
        error: error.response?.data?.detail || 'Erro ao fazer login'
      };
    }
  };

  const register = async (email, password, nome, organization_type = 'petshop') => {
    try {
      const response = await api.post('/auth/register', { email, password, nome, organization_type });
      const { access_token } = response.data;
      
      localStorage.setItem('access_token', access_token);
      
      // Buscar dados do usuário
      const userResponse = await api.get('/auth/me-multitenant');
      setUser(userResponse.data);
      localStorage.setItem('user', JSON.stringify(userResponse.data));
      
      return { success: true };
    } catch (error) {
      console.error('Erro no registro:', error);
      return {
        success: false,
        error: error.response?.data?.detail || 'Erro ao criar conta'
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
