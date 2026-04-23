export function resolveMediaUrl(url) {
  if (!url) return null;

  const normalizedUrl = String(url).trim();
  if (!normalizedUrl) return null;

  if (/^https?:\/\//i.test(normalizedUrl)) {
    return normalizedUrl;
  }

  const apiBase = String(import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");
  const path = normalizedUrl.startsWith("/") ? normalizedUrl : `/${normalizedUrl}`;

  if (path.startsWith("/uploads/")) {
    return `${apiBase}${path}`;
  }

  return path;
}
