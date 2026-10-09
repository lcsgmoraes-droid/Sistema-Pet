export const TAMANHO_PAGINA_CAIXAS = 25;

export function parametrosHistoricoCaixas(filtros = {}, pagina = 0) {
  const params = {
    compact: true,
    limit: TAMANHO_PAGINA_CAIXAS + 1,
    offset: pagina * TAMANHO_PAGINA_CAIXAS,
  };
  if (filtros.data_inicio) params.data_inicio = filtros.data_inicio;
  if (filtros.data_fim) params.data_fim = filtros.data_fim;
  if (filtros.status) params.status_filter = filtros.status;
  return params;
}

export function separarPaginaCaixas(resposta) {
  if (!Array.isArray(resposta)) throw new Error("Resposta inválida do histórico de caixas.");
  return {
    caixas: resposta.slice(0, TAMANHO_PAGINA_CAIXAS),
    temProximaPagina: resposta.length > TAMANHO_PAGINA_CAIXAS,
  };
}

export function podeReabrirCaixa(statusConsulta, caixaAberto) {
  return statusConsulta === "pronto" && !caixaAberto;
}

export function mensagemErroConsultaCaixas(erro, mensagemPadrao) {
  const detalhe = erro.response?.data?.detail;
  return typeof detalhe === "string" ? detalhe : mensagemPadrao;
}

export function iniciarConsultaCaixas({ consultar, onIniciar, onSucesso, onErro, onFim }) {
  const controller = new AbortController();
  let vigente = true;
  onIniciar?.();
  const finalizado = (async () => {
    try {
      const resposta = await consultar(controller.signal);
      if (vigente) onSucesso(resposta);
    } catch (erro) {
      if (vigente && !controller.signal.aborted) onErro(erro);
    } finally {
      if (vigente) onFim?.();
    }
  })();
  return {
    finalizado,
    cancelar() {
      vigente = false;
      controller.abort();
    },
  };
}
