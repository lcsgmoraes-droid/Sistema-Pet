import { useEffect } from "react";
import {
  preloadDashboardFinanceiro,
  preloadLembretes,
  preloadPDV,
  preloadPessoas,
  preloadProdutos,
} from "./lazyPages";

export default function AppRoutePreloader() {
  useEffect(() => {
    let cancelled = false;
    let idleId;
    let timerId;
    let delayedTimerId;

    const connection =
      navigator.connection || navigator.mozConnection || navigator.webkitConnection;

    const shouldSkipPreload =
      Boolean(connection?.saveData) ||
      (typeof connection?.effectiveType === "string" && /(^|-)2g$/.test(connection.effectiveType));

    if (shouldSkipPreload) {
      return () => {};
    }

    const runPreload = () => {
      if (cancelled) {
        return;
      }

      preloadLembretes();
      preloadDashboardFinanceiro();
      preloadPessoas();
      preloadProdutos();

      delayedTimerId = window.setTimeout(() => {
        if (!cancelled) {
          preloadPDV();
        }
      }, 4500);
    };

    if (typeof window.requestIdleCallback === "function") {
      idleId = window.requestIdleCallback(runPreload, { timeout: 2200 });
    } else {
      timerId = window.setTimeout(runPreload, 1200);
    }

    return () => {
      cancelled = true;

      if (typeof window.cancelIdleCallback === "function" && typeof idleId === "number") {
        window.cancelIdleCallback(idleId);
      }

      if (typeof timerId === "number") {
        window.clearTimeout(timerId);
      }

      if (typeof delayedTimerId === "number") {
        window.clearTimeout(delayedTimerId);
      }
    };
  }, []);

  return null;
}
