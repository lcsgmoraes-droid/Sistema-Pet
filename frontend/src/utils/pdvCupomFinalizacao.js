export function concluirVendaComCupom({
  imprimirCupom = false,
  imprimir = () => globalThis.print?.(),
  onConcluir,
} = {}) {
  if (imprimirCupom) {
    imprimir();
  }

  onConcluir?.();
}
