export async function recarregarPDVAposDevolucao({
  devolucao,
  vendaAtual,
  carregarVendaEspecifica,
  buscarClientePorId,
  setVendaAtual,
  recarregarContextoClientePorId,
  carregarVendasRecentes,
}) {
  if (vendaAtual.id && String(vendaAtual.id) === String(devolucao.venda_id)) {
    // O carregamento da venda já consulta pagamentos, cliente e contexto financeiro.
    await carregarVendaEspecifica(vendaAtual.id);
  } else if (
    vendaAtual.cliente?.id &&
    String(vendaAtual.cliente.id) === String(devolucao.cliente_id)
  ) {
    const cliente = await buscarClientePorId(devolucao.cliente_id);
    setVendaAtual((prev) =>
      String(prev.cliente?.id) === String(devolucao.cliente_id)
        ? { ...prev, cliente: { ...prev.cliente, ...cliente } }
        : prev,
    );
    await recarregarContextoClientePorId(devolucao.cliente_id);
  }
  await carregarVendasRecentes();
}
