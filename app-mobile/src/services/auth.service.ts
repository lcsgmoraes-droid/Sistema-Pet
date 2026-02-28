import * as SecureStore from 'expo-secure-store';
import api from './api';
import { AuthResponse, EcommerceUser } from '../types';

// ─────────────────────────────────────────────────────────────
// Todos os endpoints usam os mesmos do e-commerce (token_type = ecommerce_customer)
// Rota base: /ecommerce/auth/...
// ─────────────────────────────────────────────────────────────

export async function login(email: string, password: string): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/ecommerce/auth/login', { email, password });
  await SecureStore.setItemAsync('auth_token', data.access_token);
  return data;
}

export async function register(
  email: string,
  password: string,
  nome?: string
): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/ecommerce/auth/registrar', {
    email,
    password,
    nome,
  });
  await SecureStore.setItemAsync('auth_token', data.access_token);
  return data;
}

export async function logout(): Promise<void> {
  await SecureStore.deleteItemAsync('auth_token');
}

export async function getProfile(): Promise<EcommerceUser> {
  const { data } = await api.get<EcommerceUser>('/ecommerce/auth/perfil');
  return data;
}

export async function updateProfile(updates: Partial<EcommerceUser>): Promise<EcommerceUser> {
  const { data } = await api.put<EcommerceUser>('/ecommerce/auth/perfil', updates);
  return data;
}

export async function getStoredToken(): Promise<string | null> {
  return SecureStore.getItemAsync('auth_token');
}

// Registra o token de push notification para receber notificações
export async function registerPushToken(pushToken: string): Promise<void> {
  try {
    await api.post('/app/push-token', { token: pushToken });
  } catch (_) {
    // não bloqueia a experiência se falhar
  }
}
