export function criarAtualizadorSaldoCampanhas({
  buscarSaldo,
  onSaldo,
  onInicio,
  onErro,
  agendar = setTimeout,
  cancelarAgendamento = clearTimeout,
  intervaloMs = 1500,
  maxConsultas = 40,
}) {
  let geracao = 0;
  let timer = null;
  let requisicao = null;

  const cancelar = () => {
    geracao += 1;
    if (timer !== null) cancelarAgendamento(timer);
    timer = null;
    requisicao?.abort();
    requisicao = null;
  };

  const consultar = async (clienteId, versao, tentativa, erros = 0) => {
    requisicao = new AbortController();
    try {
      const saldo = await buscarSaldo(clienteId, { signal: requisicao.signal });
      if (versao !== geracao) return;
      const limiteAtingido = tentativa + 1 >= maxConsultas;
      onSaldo({
        ...saldo,
        beneficios_atualizando: false,
        beneficios_erro_atualizacao: false,
        beneficios_consulta_limite: Boolean(saldo.beneficios_em_processamento && limiteAtingido),
      });
      if (!saldo.beneficios_em_processamento || limiteAtingido) return;
    } catch (erro) {
      if (versao !== geracao) return;
      onErro?.(erro);
      if (erros + 1 >= 3 || tentativa + 1 >= maxConsultas) return;
      erros += 1;
    }
    timer = agendar(() => {
      timer = null;
      void consultar(clienteId, versao, tentativa + 1, erros);
    }, intervaloMs);
  };

  return {
    cancelar,
    atualizar: (clienteId) => {
      cancelar();
      if (!clienteId) return Promise.resolve();
      onInicio?.(clienteId);
      return consultar(clienteId, geracao, 0);
    },
  };
}
