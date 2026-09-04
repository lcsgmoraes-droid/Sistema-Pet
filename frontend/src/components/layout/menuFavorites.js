export const MAX_MENU_FAVORITES = 8;
export const FAVORITE_DRAG_CLICK_SUPPRESSION_MS = 1000;
export const MENU_FAVORITES_RETRY_DELAYS_MS = [500, 1500];

const MENU_FAVORITES_CACHE_PREFIX = "corepet:menu-favorites:v1";

function cleanText(value) {
  return String(value ?? "").trim();
}

function toApiFavorite(item) {
  const path = cleanText(item?.path);
  const label = cleanText(item?.label);
  const iconKey = cleanText(item?.icon_key ?? item?.iconKey);
  if (!path || !label) return null;
  return {
    path,
    label,
    icon_key: iconKey || null,
  };
}

function toVisibleFavorite(item) {
  const apiFavorite = toApiFavorite(item);
  if (!apiFavorite) return null;
  return {
    path: apiFavorite.path,
    label: apiFavorite.label,
    iconKey: apiFavorite.icon_key,
    icon: item.icon || null,
  };
}

export function normalizeMenuFavorites(items = []) {
  if (!Array.isArray(items)) return [];
  const seen = new Set();
  const normalized = [];
  for (const item of items) {
    const favorite = toApiFavorite(item);
    if (!favorite || seen.has(favorite.path)) continue;
    seen.add(favorite.path);
    normalized.push(favorite);
  }
  return normalized;
}

export function buildMenuFavoritesCacheKey(user) {
  const userId = cleanText(user?.id);
  const tenantId = cleanText(user?.tenant?.id ?? user?.tenant_id);
  if (!userId || !tenantId) return null;
  return `${MENU_FAVORITES_CACHE_PREFIX}:${tenantId}:${userId}`;
}

function resolveStorage(storage) {
  if (storage !== undefined) return storage;
  try {
    return globalThis.localStorage || null;
  } catch {
    return null;
  }
}

export function readMenuFavoritesCache(user, storage) {
  const cacheKey = buildMenuFavoritesCacheKey(user);
  const resolvedStorage = resolveStorage(storage);
  if (!cacheKey || !resolvedStorage) return [];

  try {
    const cached = resolvedStorage.getItem(cacheKey);
    return cached ? normalizeMenuFavorites(JSON.parse(cached)) : [];
  } catch {
    return [];
  }
}

export function writeMenuFavoritesCache(user, favorites, storage) {
  const normalized = normalizeMenuFavorites(favorites);
  const cacheKey = buildMenuFavoritesCacheKey(user);
  const resolvedStorage = resolveStorage(storage);
  if (!cacheKey || !resolvedStorage) return normalized;

  try {
    resolvedStorage.setItem(cacheKey, JSON.stringify(normalized));
  } catch {
    // O cache local e apenas uma protecao contra falhas temporarias da API.
  }
  return normalized;
}

export function isTransientMenuFavoritesError(error) {
  const status = Number(error?.response?.status || 0);
  return !status || status === 408 || status === 425 || status === 429 || status >= 500;
}

export async function loadMenuFavoritesWithRetry(
  loadFavorites,
  {
    retryDelays = MENU_FAVORITES_RETRY_DELAYS_MS,
    wait = (delay) => new Promise((resolve) => setTimeout(resolve, delay)),
    shouldContinue = () => true,
    shouldRetry = () => true,
  } = {},
) {
  let retryIndex = 0;

  while (shouldContinue()) {
    try {
      return normalizeMenuFavorites(await loadFavorites());
    } catch (error) {
      if (retryIndex >= retryDelays.length || !shouldContinue() || !shouldRetry(error)) {
        throw error;
      }
      const retryDelay = retryDelays[retryIndex];
      retryIndex += 1;
      await wait(retryDelay);
    }
  }

  return null;
}

export function flattenMenuItemsForFavorites(menuItems = []) {
  const entries = [];
  const seen = new Set();

  const addEntry = (item, fallbackIcon) => {
    const visible = toVisibleFavorite({
      ...item,
      iconKey: item.iconKey ?? fallbackIcon?.iconKey,
      icon: item.icon ?? fallbackIcon?.icon,
    });
    if (!visible || seen.has(visible.path)) return;
    seen.add(visible.path);
    entries.push(visible);
  };

  for (const item of Array.isArray(menuItems) ? menuItems : []) {
    if (Array.isArray(item.submenu) && item.submenu.length > 0) {
      for (const subitem of item.submenu) {
        addEntry(subitem, item);
      }
      continue;
    }
    addEntry(item);
  }

  return entries;
}

export function buildVisibleMenuFavorites(savedFavorites = [], menuItems = []) {
  const allowedByPath = new Map(
    flattenMenuItemsForFavorites(menuItems).map((item) => [item.path, item]),
  );

  return normalizeMenuFavorites(savedFavorites)
    .map((favorite) => allowedByPath.get(favorite.path))
    .filter(Boolean);
}

export function toggleMenuFavorite(favorites = [], item) {
  const normalized = normalizeMenuFavorites(favorites);
  const target = toApiFavorite(item);
  if (!target) return normalized;

  const exists = normalized.some((favorite) => favorite.path === target.path);
  if (exists) {
    return normalized.filter((favorite) => favorite.path !== target.path);
  }

  if (normalized.length >= MAX_MENU_FAVORITES) {
    throw new Error(`Escolha no maximo ${MAX_MENU_FAVORITES} favoritos.`);
  }

  return [...normalized, target];
}

export function reorderMenuFavorites(favorites = [], activePath, overPath) {
  const normalized = normalizeMenuFavorites(favorites);
  const fromIndex = normalized.findIndex((favorite) => favorite.path === activePath);
  const toIndex = normalized.findIndex((favorite) => favorite.path === overPath);

  if (fromIndex < 0 || toIndex < 0 || fromIndex === toIndex) {
    return normalized;
  }

  const reordered = [...normalized];
  const [moved] = reordered.splice(fromIndex, 1);
  reordered.splice(toIndex, 0, moved);
  return reordered;
}

export function sameFavoritePathOrder(left = [], right = []) {
  if (left.length !== right.length) return false;
  return left.every((favorite, index) => favorite.path === right[index]?.path);
}

export function shouldBlockFavoriteShortcutClick({
  isDragging = false,
  suppressClickUntil = 0,
  now = Date.now(),
} = {}) {
  return Boolean(isDragging || suppressClickUntil > now);
}

export function createFavoriteDragClickGuard() {
  let dragActive = false;
  let suppressNextClick = false;

  return {
    pointerIntentStarted() {
      if (!dragActive) suppressNextClick = false;
    },
    dragStarted() {
      dragActive = true;
      suppressNextClick = true;
    },
    dragFinished() {
      dragActive = false;
      suppressNextClick = true;
    },
    consumeClick() {
      const shouldBlock = dragActive || suppressNextClick;
      if (shouldBlock) suppressNextClick = false;
      return shouldBlock;
    },
  };
}
