export const ERRO_SEM_ORIGEM_FRACIONAMENTO =
  "Estoque clinico insuficiente e nenhuma embalagem fechada vinculada possui saldo. Abra o produto da loja em Estoque > Destinar a clinica.";

export async function garantirSaldoClinicoParaInsumo({
  api,
  confirmar,
  documento,
  observacao,
  produto,
  quantidade,
}) {
  const respostaSugestao = await api.obterSugestaoFracionamentoClinico(produto.id, quantidade);
  const contexto = respostaSugestao.data;
  if (!contexto?.necessita_fracionamento) {
    return { cancelado: false, conversao: null };
  }

  const sugestao = contexto.sugestao;
  if (!sugestao) throw new Error(ERRO_SEM_ORIGEM_FRACIONAMENTO);

  const origem = sugestao.produto_origem;
  const destino = sugestao.produto_destino;
  const confirmado = await confirmar({
    titulo: "Abrir embalagem para uso clinico?",
    mensagem:
      `O saldo de ${destino.nome} e ${Number(contexto.estoque_atual || 0).toLocaleString("pt-BR")} ${destino.unidade}, mas este atendimento precisa de ${Number(quantidade).toLocaleString("pt-BR")} ${destino.unidade}. ` +
      `Deseja baixar ${Number(sugestao.quantidade_origem).toLocaleString("pt-BR")} ${origem.unidade} de ${origem.nome} da loja e adicionar ${Number(sugestao.quantidade_destino).toLocaleString("pt-BR")} ${destino.unidade} ao estoque clinico?`,
    confirmarTexto: "Abrir e lancar insumo",
    variante: "question",
  });
  if (!confirmado) return { cancelado: true, conversao: null };

  const respostaConversao = await api.converterFracionamentoClinico({
    produto_origem_id: origem.id,
    produto_destino_id: destino.id,
    quantidade_origem: sugestao.quantidade_origem,
    fator_conversao: sugestao.fator_conversao,
    validade_apos_abertura_dias: sugestao.validade_apos_abertura_dias,
    documento,
    observacao,
  });
  return { cancelado: false, conversao: respostaConversao.data };
}
