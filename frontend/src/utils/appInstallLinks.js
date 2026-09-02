export const COREPET_STORE_URLS = {
  android: "https://play.google.com/store/apps/details?id=br.com.corepet.app",
  ios: "https://apps.apple.com/br/app/corepet/id6785267892",
};

export function getAppInstallPlatform({ userAgent = "", maxTouchPoints = 0 } = {}) {
  if (/Android/i.test(userAgent)) return "android";
  if (/iPhone|iPad|iPod/i.test(userAgent) || (/Macintosh/i.test(userAgent) && maxTouchPoints > 1)) {
    return "ios";
  }
  return null;
}

export function buildAppInstallLinks(slug, platform) {
  const query = `loja=${encodeURIComponent(String(slug || "").trim())}`;
  const deepLink = `corepet://app?${query}`;
  const storeUrl = COREPET_STORE_URLS[platform] || null;
  return {
    storeUrl,
    openUrl:
      platform === "android"
        ? `intent://app?${query}#Intent;scheme=corepet;package=br.com.corepet.app;S.browser_fallback_url=${encodeURIComponent(storeUrl)};end`
        : deepLink,
  };
}

// Run directly from a click so the browser allows opening an external app.
// Browsers cannot reliably detect installation, so direct download links remain visible.
export function openAppWithStoreFallback(links, browserWindow = window) {
  const { document } = browserWindow;
  let timer;
  let cancelled = false;

  function cancel() {
    cancelled = true;
    browserWindow.clearTimeout(timer);
    document.removeEventListener("visibilitychange", onVisibilityChange);
    browserWindow.removeEventListener("pagehide", cancel);
  }

  function onVisibilityChange() {
    if (document.visibilityState === "hidden") cancel();
  }

  function openStore() {
    const shouldOpen = !cancelled && document.visibilityState === "visible";
    cancel();
    if (shouldOpen) browserWindow.location.assign(links.storeUrl);
  }

  if (!links.storeUrl) return cancel;

  document.addEventListener("visibilitychange", onVisibilityChange);
  browserWindow.addEventListener("pagehide", cancel);
  timer = browserWindow.setTimeout(openStore, 2500);

  try {
    browserWindow.location.assign(links.openUrl);
  } catch {
    openStore();
  }
  return cancel;
}
