import * as SecureStore from 'expo-secure-store';
import api from './api';
import { AppProfileType, AuthResponse, EcommerceUser } from '../types';

const ACCESS_TOKEN_KEY = 'auth_token';
const REFRESH_TOKEN_KEY = 'auth_refresh_token';

async function persistAuthTokens(data: AuthResponse): Promise<void> {
  if (data.access_token) {
    await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, data.access_token);
  }
  if (data.refresh_token) {
    await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, data.refresh_token);
  }
}

type EcommerceProfileUpdate = Partial<EcommerceUser> & {
  entrega_nome?: string | null;
  entrega_cep?: string | null;
  entrega_endereco?: string | null;
  entrega_numero?: string | null;
  entrega_complemento?: string | null;
  entrega_bairro?: string | null;
  entrega_cidade?: string | null;
  entrega_estado?: string | null;
};

export async function login(email: string, password: string): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/ecommerce/auth/login', { email, password });
  await persistAuthTokens(data);
  return data;
}

export async function register(
  email: string,
  password: string,
  nome?: string,
  cpf?: string,
  telefone?: string,
  acceptedTerms = true,
  acceptedPrivacy = true,
): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/ecommerce/auth/registrar', {
    email,
    password,
    nome,
    cpf: cpf || undefined,
    telefone: telefone || undefined,
    canal: 'app',
    accepted_terms: acceptedTerms,
    accepted_privacy: acceptedPrivacy,
  }, {
    headers: { 'X-Client-Channel': 'app' },
  });
  await persistAuthTokens(data);
  return data;
}

export async function selectProfile(profileType: AppProfileType): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/ecommerce/auth/select-profile', {
    profile_type: profileType,
  });
  await persistAuthTokens(data);
  return data;
}

export async function logout(): Promise<void> {
  try {
    await api.post('/ecommerce/auth/logout');
  } catch {
    // Logout local deve acontecer mesmo se a sessao remota ja expirou.
  }
  await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
  await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
}

export async function getProfile(): Promise<EcommerceUser> {
  const { data } = await api.get<EcommerceUser>('/ecommerce/auth/perfil');
  return data;
}

export async function updateProfile(updates: EcommerceProfileUpdate): Promise<EcommerceUser> {
  const { data } = await api.put<EcommerceUser>('/ecommerce/auth/perfil', updates);
  return data;
}

export async function requestPasswordReset(email: string): Promise<{ message: string; expires_in_minutes?: number }> {
  const { data } = await api.post<{ message: string; expires_in_minutes?: number }>(
    '/ecommerce/auth/esqueci-senha',
    { email, canal: 'app' },
  );
  return data;
}

export async function resetPassword(
  email: string,
  token: string,
  novaSenha: string,
): Promise<{ message: string }> {
  const { data } = await api.post<{ message: string }>('/ecommerce/auth/resetar-senha', {
    email,
    token,
    nova_senha: novaSenha,
  });
  return data;
}

export async function getStoredToken(): Promise<string | null> {
  return SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
}

export interface PushDeviceMetadata {
  platform?: string;
  device_name?: string | null;
  device_brand?: string | null;
  device_model?: string | null;
  os_name?: string | null;
  os_version?: string | null;
  app_version?: string | null;
}

export async function registerPushToken(
  pushToken: string,
  metadata: PushDeviceMetadata = {},
): Promise<void> {
  await api.post('/app/push-token', { token: pushToken, ...metadata });
}

export async function unregisterPushToken(pushToken?: string | null): Promise<void> {
  await api.delete('/app/push-token', {
    data: pushToken ? { token: pushToken } : {},
  });
}
