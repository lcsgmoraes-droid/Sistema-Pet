const ACCESS_TOKEN_KEY = 'access_token';
const LEGACY_TOKEN_KEY = 'token';
const TEMP_TOKEN_KEY = 'tempToken';

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

const migrateLegacyToken = (key) => {
  const session = getSessionStorage();
  const local = getLocalStorage();
  if (!session || !local) {
    return null;
  }

  const token = local.getItem(key);
  if (token) {
    session.setItem(key, token);
    local.removeItem(key);
  }
  return token;
};

export const getAccessToken = () => {
  const session = getSessionStorage();
  const token = session?.getItem(ACCESS_TOKEN_KEY) || session?.getItem(LEGACY_TOKEN_KEY);
  if (token) {
    return token;
  }

  return migrateLegacyToken(ACCESS_TOKEN_KEY) || migrateLegacyToken(LEGACY_TOKEN_KEY);
};

export const setAccessToken = (token) => {
  const session = getSessionStorage();
  const local = getLocalStorage();
  if (!session) {
    return;
  }

  session.setItem(ACCESS_TOKEN_KEY, token);
  session.removeItem(LEGACY_TOKEN_KEY);
  local?.removeItem(ACCESS_TOKEN_KEY);
  local?.removeItem(LEGACY_TOKEN_KEY);
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
  session?.removeItem(LEGACY_TOKEN_KEY);
  session?.removeItem(TEMP_TOKEN_KEY);
  local?.removeItem(ACCESS_TOKEN_KEY);
  local?.removeItem(LEGACY_TOKEN_KEY);
  local?.removeItem(TEMP_TOKEN_KEY);
};
