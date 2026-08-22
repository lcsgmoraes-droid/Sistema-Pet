const ACCESS_TOKEN_KEY = "platform_access_token";
const REFRESH_TOKEN_KEY = "platform_refresh_token";

const storage = (kind) => {
  try {
    return kind === "session" ? globalThis.sessionStorage : globalThis.localStorage;
  } catch {
    return null;
  }
};

const read = (key) => storage("session")?.getItem(key) || storage("local")?.getItem(key) || null;

const write = (key, value) => {
  storage("session")?.setItem(key, value);
  storage("local")?.setItem(key, value);
};

export const getPlatformAccessToken = () => read(ACCESS_TOKEN_KEY);
export const getPlatformRefreshToken = () => read(REFRESH_TOKEN_KEY);
export const setPlatformAccessToken = (token) => write(ACCESS_TOKEN_KEY, token);
export const setPlatformRefreshToken = (token) => write(REFRESH_TOKEN_KEY, token);

export const clearPlatformAuthTokens = () => {
  for (const kind of ["session", "local"]) {
    const current = storage(kind);
    current?.removeItem(ACCESS_TOKEN_KEY);
    current?.removeItem(REFRESH_TOKEN_KEY);
  }
};
