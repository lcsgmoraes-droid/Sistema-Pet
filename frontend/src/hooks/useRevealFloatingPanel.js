import { useEffect } from "react";

import { revelarPainelFlutuante } from "../utils/floatingPanelReveal";

export default function useRevealFloatingPanel({
  behavior = "smooth",
  block = "nearest",
  enabled,
  margin = 24,
  panelRef,
  refreshKey = "",
}) {
  useEffect(() => {
    if (!enabled) {
      return undefined;
    }

    const revelar = () => {
      revelarPainelFlutuante(panelRef?.current, { behavior, block, margin });
    };

    if (
      typeof window !== "undefined" &&
      typeof window.requestAnimationFrame === "function"
    ) {
      let primeiroFrame = 0;
      let segundoFrame = 0;

      primeiroFrame = window.requestAnimationFrame(() => {
        segundoFrame = window.requestAnimationFrame(revelar);
      });

      return () => {
        window.cancelAnimationFrame?.(primeiroFrame);
        window.cancelAnimationFrame?.(segundoFrame);
      };
    }

    if (typeof window !== "undefined" && typeof window.setTimeout === "function") {
      const timeoutId = window.setTimeout(revelar, 0);
      return () => window.clearTimeout(timeoutId);
    }

    revelar();
    return undefined;
  }, [behavior, block, enabled, margin, panelRef, refreshKey]);
}
