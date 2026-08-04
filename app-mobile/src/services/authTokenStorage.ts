import * as SecureStore from "expo-secure-store";
import { AuthTokens, EcommerceUser } from "../types";

const ACCESS_TOKEN_KEY = "auth_token";
const REFRESH_TOKEN_KEY = "auth_refresh_token";
const USER_CACHE_KEY = "auth_user_cache";

export async function storeAuthTokens(tokens: AuthTokens): Promise<void> {
  const accessToken = tokens.access_token?.trim();
  const refreshToken = tokens.refresh_token?.trim();

  if (accessToken) {
    await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, accessToken);
  }

  if (refreshToken) {
    await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refreshToken);
  } else if (accessToken) {
    await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
  }
}

export function getAccessToken(): Promise<string | null> {
  return SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): Promise<string | null> {
  return SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
}

export async function cacheAuthenticatedUser(
  user: EcommerceUser,
): Promise<void> {
  await SecureStore.setItemAsync(USER_CACHE_KEY, JSON.stringify(user));
}

export async function getCachedAuthenticatedUser(): Promise<EcommerceUser | null> {
  const raw = await SecureStore.getItemAsync(USER_CACHE_KEY);
  if (!raw) return null;

  try {
    const user = JSON.parse(raw) as EcommerceUser;
    if (!user?.id || !user.email) {
      await SecureStore.deleteItemAsync(USER_CACHE_KEY);
      return null;
    }
    return user;
  } catch {
    await SecureStore.deleteItemAsync(USER_CACHE_KEY);
    return null;
  }
}

export async function hasStoredAuthSession(): Promise<boolean> {
  const [accessToken, refreshToken] = await Promise.all([
    getAccessToken(),
    getRefreshToken(),
  ]);
  return Boolean(accessToken || refreshToken);
}

export async function clearAuthSession(): Promise<void> {
  await Promise.all([
    SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY),
    SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY),
    SecureStore.deleteItemAsync(USER_CACHE_KEY),
  ]);
}
