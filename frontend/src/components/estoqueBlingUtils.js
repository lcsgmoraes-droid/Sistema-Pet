export function normalizeText(value) {
  return String(value || "")
    .trim()
    .toLowerCase();
}

export function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString("pt-BR");
}

export function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return Number(value).toLocaleString("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  });
}

export function formatCacheAge(seconds) {
  const totalSeconds = Number(seconds || 0);
  if (!totalSeconds) return "agora";
  if (totalSeconds < 60) return `${totalSeconds}s`;
  const minutes = Math.floor(totalSeconds / 60);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  return `${hours} h`;
}

export function formatDurationMs(value) {
  const totalMs = Number(value || 0);
  if (!totalMs) return "agora";
  if (totalMs < 1000) return `${totalMs} ms`;
  return `${(totalMs / 1000).toFixed(totalMs >= 10000 ? 0 : 1)} s`;
}

export function getErrorMessage(error, fallback = "Nao foi possivel carregar agora.") {
  return error?.response?.data?.detail || error?.message || fallback;
}

export function includesSearch(search, values) {
  const term = normalizeText(search);
  if (!term) return true;
  return values.some((value) => normalizeText(value).includes(term));
}

export function buildSyncErrorMeta(item, { blingConnected = null } = {}) {
  const ultimoErro = String(item.ultimo_erro || "").trim();
  const rateLimited = /429|too many requests|too_many_requests|limite de requisi/i.test(ultimoErro);
  const authInvalid =
    /invalid_token|invalid token|invalid_grant|unauthorized|401 client error|token expirado|reconecte o bling|autorizacao salva/i.test(
      ultimoErro,
    );
  const noActiveLink =
    /sem v[i\u00ed]nculo ativo com o bling|nao configurado para sincroniza/i.test(ultimoErro);
  const notFound = /not found|nao encontrado|n\u00e3o encontrado/i.test(ultimoErro);

  if (rateLimited) {
    const waitingQueue = item.queue_status === "pendente";
    return {
      category: "rate_limit",
      tone: "amber",
      title: waitingQueue
        ? "Aguardando janela segura do Bling"
        : "Limite temporario da API do Bling",
      description: waitingQueue
        ? "O item ja entrou de novo na fila segura e sera retomado em lote menor. Abrir ou atualizar a pagina nao dispara esse erro; a tela mostra apenas o ultimo registro salvo."
        : "A ultima tentativa esbarrou no limite temporario de requisicoes do Bling. Abrir ou atualizar a pagina nao dispara esse erro; a tela mostra apenas o ultimo registro salvo.",
      buttonLabel: waitingQueue ? "Tentar item" : "Reenfileirar item",
      action: "force",
      detailLabel: "Ultimo registro",
      detailValue: waitingQueue
        ? "Item aguardando nova janela segura para reenviar."
        : "Ultima tentativa bloqueada pelo limite temporario do Bling.",
      technicalValue: "429 TOO_MANY_REQUESTS",
    };
  }

  if (authInvalid) {
    const invalidGrant = /invalid_grant/i.test(ultimoErro);

    if (blingConnected === true) {
      return {
        category: "auth_resolved",
        tone: "sky",
        title: "Conexao com o Bling restabelecida",
        description:
          "A integracao ja voltou a responder. Agora voce pode reprocessar esta falha normalmente.",
        buttonLabel: "Corrigir agora",
        action: "force",
        detailLabel: "Ultimo registro",
        detailValue:
          "A fila guardou um erro antigo de autorizacao, mas a conexao atual ja esta valida.",
        technicalValue: invalidGrant
          ? "400 INVALID_GRANT (historico)"
          : "401 INVALID_TOKEN (historico)",
      };
    }

    return {
      category: "auth_invalid",
      tone: "amber",
      title: "Integracao do Bling precisa ser reconectada",
      description: invalidGrant
        ? "A autorizacao salva do Bling deixou de valer. Enquanto isso nao for reconectado, reprocessar e forcar sync vao falhar."
        : "O token do Bling expirou e a renovacao automatica nao conseguiu concluir. Enquanto isso nao for reconectado, reprocessar e forcar sync vao falhar.",
      buttonLabel: "Reconectar Bling",
      action: "reauthorize",
      detailLabel: "Ultimo registro",
      detailValue: "A credencial atual da integracao foi recusada pelo Bling.",
      technicalValue: invalidGrant ? "400 INVALID_GRANT" : "401 INVALID_TOKEN",
    };
  }

  if (noActiveLink) {
    return {
      category: "link",
      tone: "slate",
      title: "Vinculo do produto precisa de revisao",
      description:
        "A integracao deste produto nao esta pronta para enviar estoque agora. Revise o vinculo e depois tente novamente.",
      buttonLabel: "Corrigir agora",
      action: "force",
      detailLabel: "Ultimo registro",
      detailValue: "Produto sem vinculo ativo para sincronizacao.",
      technicalValue: "VINCULO_INATIVO",
    };
  }

  if (notFound) {
    return {
      category: "not_found",
      tone: "amber",
      title: "Produto nao localizado no Bling",
      description:
        "A ultima tentativa nao encontrou este produto do outro lado. Vale revisar o vinculo antes de tentar novo envio.",
      buttonLabel: "Corrigir agora",
      action: "force",
      detailLabel: "Ultimo registro",
      detailValue: "Ultima tentativa sem encontrar o item correspondente no Bling.",
      technicalValue: "ITEM_NAO_ENCONTRADO",
    };
  }

  if (ultimoErro) {
    return {
      category: "generic_error",
      tone: "red",
      title: "Falha de sincronizacao",
      description:
        "A ultima tentativa de envio nao foi concluida. Revise e tente novamente quando quiser.",
      buttonLabel: "Corrigir agora",
      action: "force",
      detailLabel: "Ultimo registro",
      detailValue: "O ultimo envio ao Bling terminou com erro.",
      technicalValue: ultimoErro.length > 140 ? `${ultimoErro.slice(0, 140)}...` : ultimoErro,
    };
  }

  return null;
}

export function buildSyncIssue(item, options = {}) {
  const divergencia = Math.abs(Number(item.divergencia || 0));
  const syncError = buildSyncErrorMeta(item, options);

  if (syncError?.category === "rate_limit" && item.queue_status === "pendente") {
    return syncError;
  }

  if (
    item.queue_status === "falha_final" ||
    item.queue_status === "erro" ||
    item.status === "erro"
  ) {
    return (
      syncError || {
        tone: "red",
        title: "Falha de sincronizacao",
        description: "A ultima tentativa de envio para o Bling falhou e precisa de nova tentativa.",
        buttonLabel: "Corrigir agora",
        action: "force",
        detailLabel: "Ultimo registro",
        detailValue: "Falha registrada na ultima tentativa.",
        technicalValue: "-",
      }
    );
  }

  if (divergencia >= 0.01) {
    return {
      tone: "amber",
      title: "Estoque divergente",
      description: `Sistema ${formatNumber(item.estoque_sistema)} | Bling ${formatNumber(item.estoque_bling)} | Divergencia ${formatNumber(item.divergencia)}`,
      buttonLabel: "Reconciliar agora",
      action: "reconcile",
    };
  }

  if (item.queue_status === "pendente") {
    return {
      tone: "sky",
      title: "Fila pendente",
      description:
        "Existe uma tentativa aguardando processamento. Abrir ou atualizar a pagina nao dispara o envio; a tela mostra apenas o estado atual da fila.",
      buttonLabel: "Forcar agora",
      action: "force",
      detailLabel: "Ultimo registro",
      detailValue: "Item aguardando a vez na fila automatica.",
      technicalValue: "FILA_PENDENTE",
    };
  }

  if (item.status !== "ativo") {
    return {
      tone: "slate",
      title: "Vinculo fora do estado ideal",
      description: "O produto esta vinculado, mas o status do sync nao esta como ativo.",
      buttonLabel: "Forcar agora",
      action: "force",
      detailLabel: "Ultimo registro",
      detailValue: "Estado do sync diferente do esperado para envio automatico.",
      technicalValue: item.status || "STATUS_FORA_DO_IDEAL",
    };
  }

  return null;
}
