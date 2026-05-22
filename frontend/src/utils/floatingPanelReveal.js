function obterAlturaViewport(viewportHeight) {
  if (Number.isFinite(viewportHeight) && viewportHeight > 0) {
    return viewportHeight;
  }

  if (
    typeof window !== "undefined" &&
    Number.isFinite(window.innerHeight) &&
    window.innerHeight > 0
  ) {
    return window.innerHeight;
  }

  if (
    typeof document !== "undefined" &&
    Number.isFinite(document.documentElement?.clientHeight) &&
    document.documentElement.clientHeight > 0
  ) {
    return document.documentElement.clientHeight;
  }

  return 0;
}

function deveReduzirMovimento() {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

export function painelFlutuantePrecisaRevelar(
  rect,
  { margin = 24, viewportHeight } = {},
) {
  const alturaViewport = obterAlturaViewport(viewportHeight);

  if (!rect || !alturaViewport) {
    return false;
  }

  return rect.bottom > alturaViewport - margin || rect.top < margin;
}

export function revelarPainelFlutuante(
  elemento,
  { behavior = "smooth", block = "nearest", margin = 24, viewportHeight } = {},
) {
  if (
    !elemento ||
    typeof elemento.getBoundingClientRect !== "function" ||
    typeof elemento.scrollIntoView !== "function"
  ) {
    return false;
  }

  const rect = elemento.getBoundingClientRect();
  if (!painelFlutuantePrecisaRevelar(rect, { margin, viewportHeight })) {
    return false;
  }

  elemento.scrollIntoView({
    behavior: deveReduzirMovimento() ? "auto" : behavior,
    block,
    inline: "nearest",
  });

  return true;
}
