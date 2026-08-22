export function desfocarInputNumericoAoRolar(event) {
  const elemento = event?.target;

  if (!elemento?.matches?.('input[type="number"]')) return false;
  if (elemento.ownerDocument?.activeElement !== elemento) return false;

  elemento.blur();
  return true;
}

export function instalarProtecaoRodaInputsNumericos(documento = document) {
  documento.addEventListener("wheel", desfocarInputNumericoAoRolar, {
    capture: true,
    passive: true,
  });

  return () => {
    documento.removeEventListener("wheel", desfocarInputNumericoAoRolar, true);
  };
}
