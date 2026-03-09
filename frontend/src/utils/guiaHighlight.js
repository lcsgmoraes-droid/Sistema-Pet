export const GUIA_HIGHLIGHT_INTENSITY_KEY = "guia_highlight_intensity";

const INTENSIDADES_VALIDAS = new Set(["suave", "media", "forte"]);

export function getGuiaAtiva(search) {
  try {
    return new URLSearchParams(search || "").get("guia") || "";
  } catch {
    return "";
  }
}

export function getGuiaHighlightIntensity() {
  try {
    const value = localStorage.getItem(GUIA_HIGHLIGHT_INTENSITY_KEY) || "media";
    return INTENSIDADES_VALIDAS.has(value) ? value : "media";
  } catch {
    return "media";
  }
}

export function setGuiaHighlightIntensity(value) {
  if (!INTENSIDADES_VALIDAS.has(value)) return;
  try {
    localStorage.setItem(GUIA_HIGHLIGHT_INTENSITY_KEY, value);
  } catch {
    // Ignora indisponibilidade de storage
  }
}

export function getGuiaClassNames(active) {
  if (!active) {
    return {
      box: "",
      action: "",
      input: "",
    };
  }

  const intensity = getGuiaHighlightIntensity();

  if (intensity === "suave") {
    return {
      box: "ring-2 ring-amber-200",
      action: "ring-2 ring-amber-200",
      input: "ring-1 ring-amber-300 bg-amber-50",
    };
  }

  if (intensity === "forte") {
    return {
      box: "ring-4 ring-amber-300 shadow-lg shadow-amber-100",
      action: "ring-4 ring-amber-300 shadow-lg shadow-amber-100 animate-pulse",
      input: "ring-2 ring-amber-400 bg-amber-50 animate-pulse",
    };
  }

  return {
    box: "ring-2 ring-amber-300",
    action: "ring-4 ring-amber-200 animate-pulse",
    input: "ring-2 ring-amber-400 bg-amber-50 animate-pulse",
  };
}

export function getGuiaInlineStyle(active) {
  if (!active) return {};

  const intensity = getGuiaHighlightIntensity();

  if (intensity === "suave") {
    return {
      border: "2px solid #fcd34d",
      boxShadow: "0 0 0 2px rgba(252, 211, 77, 0.22)",
    };
  }

  if (intensity === "forte") {
    return {
      border: "2px solid #f59e0b",
      boxShadow: "0 0 0 6px rgba(245, 158, 11, 0.28)",
    };
  }

  return {
    border: "2px solid #f59e0b",
    boxShadow: "0 0 0 4px rgba(245, 158, 11, 0.2)",
  };
}
