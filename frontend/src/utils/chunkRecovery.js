const STORAGE_KEY = "corepet:chunk-recovery";
const RETRY_PARAM = "__corepet_chunk_retry";
const RETRY_INTERVAL_MS = 10_000;
const attemptedWindows = new WeakSet();

export function isDynamicImportError(error) {
  const message = String(error?.message || error || "").toLowerCase();
  return [
    "failed to fetch dynamically imported module",
    "importing a module script failed",
    "error loading dynamically imported module",
    "chunkloaderror",
    "loading chunk",
    "unable to preload css",
  ].some((fragment) => message.includes(fragment));
}

// Called only for a failed rendered route, never for background prefetches.
// Retained deployment assets are the primary protection for open forms.
export function recoverFromChunkError(error, runtime = window, now = Date.now()) {
  if (
    !isDynamicImportError(error) ||
    runtime.navigator?.onLine === false ||
    attemptedWindows.has(runtime)
  ) {
    return false;
  }

  try {
    const url = new URL(runtime.location.href);
    const entry = runtime.document?.querySelector('script[type="module"][src]')?.src;
    const version = entry ? new URL(entry, url).pathname : "unknown";
    const retryVersion = url.searchParams.get(RETRY_PARAM);
    if (retryVersion === version) return false;

    let storageAvailable = true;
    let previous;
    try {
      previous = JSON.parse(runtime.sessionStorage.getItem(STORAGE_KEY) || "null");
    } catch {
      storageAvailable = false;
    }

    if (!storageAvailable && retryVersion) return false;
    if (previous?.version === version) return false;
    const elapsed = now - Number(previous?.at);
    if (previous?.at && elapsed >= 0 && elapsed < RETRY_INTERVAL_MS) return false;

    try {
      runtime.sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ version, at: now }));
    } catch {
      // The URL also guards against a reload loop when storage is unavailable.
      if (retryVersion) return false;
    }

    attemptedWindows.add(runtime);
    // A fresh navigation avoids reusing a cached HTML response. Preserve the
    // route, existing search parameters and hash, without adding a back entry.
    url.searchParams.set(RETRY_PARAM, version);
    runtime.location.replace(url.href);
    return true;
  } catch {
    return false;
  }
}
