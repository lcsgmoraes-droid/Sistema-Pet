const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";
const LEGACY_TOKEN_KEY = "token";
const TEMP_TOKEN_KEY = "tempToken";

const getSessionStorage = () => {
  try {
    return globalThis.sessionStorage || null;
  } catch {
    return null;
  }
};

const getLocalStorage = () => {
  try {
    return globalThis.localStorage || null;
  } catch {
    return null;
  }
};

const persistAccessToken = (token) => {
  const session = getSessionStorage();
  const local = getLocalStorage();

  session?.setItem(ACCESS_TOKEN_KEY, token);
  session?.removeItem(LEGACY_TOKEN_KEY);
  local?.setItem(ACCESS_TOKEN_KEY, token);
  local?.removeItem(LEGACY_TOKEN_KEY);
};

const persistRefreshToken = (token) => {
  const session = getSessionStorage();
  const local = getLocalStorage();

  session?.setItem(REFRESH_TOKEN_KEY, token);
  local?.setItem(REFRESH_TOKEN_KEY, token);
};

const hydrateTokenFromLocalStorage = (key) => {
  const local = getLocalStorage();
  if (!local) {
    return null;
  }

  const token = local.getItem(key);
  if (token) {
    persistAccessToken(token);
  }
  return token;
};

export const getAccessToken = () => {
  const session = getSessionStorage();
  const token = session?.getItem(ACCESS_TOKEN_KEY) || session?.getItem(LEGACY_TOKEN_KEY);
  if (token) {
    persistAccessToken(token);
    return token;
  }

  return (
    hydrateTokenFromLocalStorage(ACCESS_TOKEN_KEY) || hydrateTokenFromLocalStorage(LEGACY_TOKEN_KEY)
  );
};

export const setAccessToken = (token) => {
  persistAccessToken(token);
};

export const getRefreshToken = () => {
  const session = getSessionStorage();
  const token = session?.getItem(REFRESH_TOKEN_KEY);
  if (token) {
    persistRefreshToken(token);
    return token;
  }

  const local = getLocalStorage();
  const persistedToken = local?.getItem(REFRESH_TOKEN_KEY) || null;
  if (persistedToken) {
    persistRefreshToken(persistedToken);
  }
  return persistedToken;
};

export const setRefreshToken = (token) => {
  persistRefreshToken(token);
};

export const getTempToken = () => getSessionStorage()?.getItem(TEMP_TOKEN_KEY) || null;

export const setTempToken = (token) => {
  const session = getSessionStorage();
  const local = getLocalStorage();
  if (!session) {
    return;
  }

  session.setItem(TEMP_TOKEN_KEY, token);
  local?.removeItem(TEMP_TOKEN_KEY);
};

export const clearAuthTokens = () => {
  const session = getSessionStorage();
  const local = getLocalStorage();

  session?.removeItem(ACCESS_TOKEN_KEY);
  session?.removeItem(REFRESH_TOKEN_KEY);
  session?.removeItem(LEGACY_TOKEN_KEY);
  session?.removeItem(TEMP_TOKEN_KEY);
  local?.removeItem(ACCESS_TOKEN_KEY);
  local?.removeItem(REFRESH_TOKEN_KEY);
  local?.removeItem(LEGACY_TOKEN_KEY);
  local?.removeItem(TEMP_TOKEN_KEY);
};
