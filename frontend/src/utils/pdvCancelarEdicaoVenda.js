export async function cancelarEdicaoVenda({
  vendaAtual,
  restauracao,
  restaurarStatus,
  recarregarContextoCliente,
  limparRestauracao,
  limparVenda,
  carregarVendasRecentes,
}) {
  const deveRestaurar =
    vendaAtual.id != null &&
    restauracao?.vendaId === vendaAtual.id &&
    vendaAtual.status !== restauracao.status;

  if (deveRestaurar) {
    await restaurarStatus(vendaAtual.id, restauracao.status);
    await recarregarContextoCliente?.();
  }

  // Em falha na restauracao, a tela e a referencia permanecem disponiveis
  // para tentar de novo. Uma referencia de outra venda jamais e aplicada.
  limparRestauracao();
  limparVenda();
  carregarVendasRecentes?.();
}
