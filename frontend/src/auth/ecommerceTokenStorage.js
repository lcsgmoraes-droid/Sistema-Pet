const ECOMMERCE_ACCESS_TOKEN_KEY = "ecommerce_customer_token";
const ECOMMERCE_REFRESH_TOKEN_KEY = "ecommerce_customer_refresh_token";
const ECOMMERCE_SESSION_EVENT = "corepet:ecommerce-session-changed";

function getLocalStorage() {
  try {
    return globalThis.localStorage || null;
  } catch {
    return null;
  }
}

function notifySessionChanged() {
  if (typeof globalThis.dispatchEvent !== "function" || typeof globalThis.Event !== "function") {
    return;
  }
  globalThis.dispatchEvent(new globalThis.Event(ECOMMERCE_SESSION_EVENT));
}

export function getEcommerceAccessToken() {
  return getLocalStorage()?.getItem(ECOMMERCE_ACCESS_TOKEN_KEY) || "";
}

export function getEcommerceRefreshToken() {
  return getLocalStorage()?.getItem(ECOMMERCE_REFRESH_TOKEN_KEY) || "";
}

export function setEcommerceAccessToken(token) {
  const storage = getLocalStorage();
  if (!storage) return;

  if (token) {
    storage.setItem(ECOMMERCE_ACCESS_TOKEN_KEY, token);
  } else {
    storage.removeItem(ECOMMERCE_ACCESS_TOKEN_KEY);
  }
  notifySessionChanged();
}

export function setEcommerceRefreshToken(token) {
  const storage = getLocalStorage();
  if (!storage) return;

  if (token) {
    storage.setItem(ECOMMERCE_REFRESH_TOKEN_KEY, token);
  } else {
    storage.removeItem(ECOMMERCE_REFRESH_TOKEN_KEY);
  }
}

export function setEcommerceTokens({ accessToken, refreshToken }) {
  const storage = getLocalStorage();
  if (!storage) return;

  if (accessToken) {
    storage.setItem(ECOMMERCE_ACCESS_TOKEN_KEY, accessToken);
  } else {
    storage.removeItem(ECOMMERCE_ACCESS_TOKEN_KEY);
  }

  if (refreshToken) {
    storage.setItem(ECOMMERCE_REFRESH_TOKEN_KEY, refreshToken);
  } else {
    storage.removeItem(ECOMMERCE_REFRESH_TOKEN_KEY);
  }
  notifySessionChanged();
}

export function clearEcommerceTokens() {
  const storage = getLocalStorage();
  storage?.removeItem(ECOMMERCE_ACCESS_TOKEN_KEY);
  storage?.removeItem(ECOMMERCE_REFRESH_TOKEN_KEY);
  notifySessionChanged();
}

export function subscribeEcommerceSession(listener) {
  if (typeof globalThis.addEventListener !== "function") {
    return () => {};
  }

  const handleSessionChanged = () => listener(getEcommerceAccessToken());
  globalThis.addEventListener(ECOMMERCE_SESSION_EVENT, handleSessionChanged);
  return () => globalThis.removeEventListener(ECOMMERCE_SESSION_EVENT, handleSessionChanged);
}

export { ECOMMERCE_ACCESS_TOKEN_KEY, ECOMMERCE_REFRESH_TOKEN_KEY, ECOMMERCE_SESSION_EVENT };
