export const criarEstadoCaixaAberto = () => ({
  caixa: null,
  status: "carregando",
  atualizando: false,
});

export function publicarEventoCaixa(tipo, { contextoCaixa, caixaId } = {}) {
  try {
    localStorage.setItem(
      "petshop_caixa_sync_event",
      JSON.stringify({
        tipo,
        tenant_id: contextoCaixa?.split(":").at(-1),
        caixa_id: caixaId,
        timestamp: Date.now(),
      }),
    );
  } catch {
    // A consulta da própria tela funciona mesmo sem storage.
  }
}

export function opcoesSincronizacaoCaixa(serializado, { contextoCaixa, caixaId } = {}) {
  if (!serializado) return null;
  let evento;
  try {
    evento = JSON.parse(serializado);
  } catch {
    return null;
  }
  if (!evento || typeof evento !== "object") return null;
  const tenantId = contextoCaixa?.split(":").at(-1);
  if (evento.tenant_id && tenantId && evento.tenant_id !== tenantId) return null;
  if (evento.tipo !== "abertura" && evento.caixa_id && caixaId && evento.caixa_id !== caixaId)
    return null;
  return { invalidar: ["abertura", "fechamento"].includes(evento.tipo) };
}

export function precisaConsultarResumoCaixa({ menuAberto, mostrarSaldoTopo, modalAtivo }) {
  return Boolean(menuAberto || mostrarSaldoTopo || modalAtivo === "sangria");
}

export function mensagemCaixaIndisponivel(status = "pronto") {
  if (status === "carregando") return "Verificando o caixa. Aguarde um instante.";
  if (status === "erro") return "Não foi possível verificar o caixa. Tente novamente.";
  return "Caixa fechado. Abra o caixa para continuar.";
}

function erroTransitorio(erro) {
  if (erro?.code === "ERR_CANCELED") return false;
  if (erro?.code === "ERR_CAIXA_RESPOSTA_AMBIGUA") return true;
  if ([502, 503, 504].includes(erro?.response?.status)) return true;
  return !erro?.response && ["ERR_NETWORK", "ECONNABORTED", "ETIMEDOUT"].includes(erro?.code);
}

export function validarRespostaCaixaAberto(resposta) {
  if (
    resposta.status !== 200 ||
    (resposta.data !== null && (!resposta.data?.id || resposta.data.status !== "aberto"))
  ) {
    const erro = new Error("Não foi possível confirmar o estado do caixa.");
    erro.code = "ERR_CAIXA_RESPOSTA_AMBIGUA";
    throw erro;
  }
  return resposta.data;
}

function aguardarNovaTentativa(signal) {
  return new Promise((resolve) => {
    if (signal.aborted) return resolve();
    const terminar = () => {
      clearTimeout(timer);
      signal.removeEventListener("abort", terminar);
      resolve();
    };
    const timer = setTimeout(terminar, 700);
    signal.addEventListener("abort", terminar, { once: true });
  });
}

// Um monitor por PDV: menu e venda compartilham a mesma confirmação do servidor.
export function criarMonitorCaixaAberto({ consultar, onEstado, esperar = aguardarNovaTentativa }) {
  let estado = criarEstadoCaixaAberto();
  let vigente = true;
  let controller = null;
  let emAndamento = null;

  const publicar = (novo) => {
    estado = novo;
    if (vigente) onEstado(estado);
  };

  const atualizar = ({ invalidar = false } = {}) => {
    if (!vigente) return Promise.resolve();
    if (emAndamento && !invalidar) return emAndamento;
    if (invalidar) {
      controller?.abort();
      estado = criarEstadoCaixaAberto();
    }
    const atual = new AbortController();
    controller = atual;
    publicar({ ...estado, atualizando: true });

    const requisicao = (async () => {
      try {
        let caixa;
        for (let tentativa = 0; tentativa < 2; tentativa += 1) {
          try {
            caixa = await Promise.resolve().then(() =>
              consultar({ compact: true, signal: atual.signal }),
            );
            break;
          } catch (erro) {
            if (atual.signal.aborted || tentativa > 0 || !erroTransitorio(erro)) throw erro;
            await esperar(atual.signal);
            if (atual.signal.aborted) return;
          }
        }
        if (caixa !== null && (!caixa?.id || caixa.status !== "aberto")) {
          throw new Error("Resposta inválida da consulta do caixa.");
        }
        if (!atual.signal.aborted && vigente) {
          publicar({ caixa, status: "pronto", atualizando: false });
        }
      } catch (erro) {
        if (!atual.signal.aborted && vigente) {
          // Falha de consulta não confirma fechamento. A validação financeira permanece no backend.
          const perdeuAcesso = [401, 403].includes(erro?.response?.status);
          publicar({
            caixa: perdeuAcesso ? null : estado.caixa,
            status: "erro",
            atualizando: false,
          });
        }
      } finally {
        if (controller === atual) emAndamento = null;
      }
    })();
    emAndamento = requisicao;
    return requisicao;
  };

  return {
    atualizar,
    sincronizar(serializado, contextoCaixa) {
      const opcoes = opcoesSincronizacaoCaixa(serializado, {
        contextoCaixa,
        caixaId: estado.caixa?.id,
      });
      return opcoes ? atualizar(opcoes) : Promise.resolve();
    },
    cancelar() {
      vigente = false;
      controller?.abort();
    },
  };
}
