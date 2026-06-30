export const MAX_MENU_FAVORITES = 8;

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
