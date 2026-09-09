export function modoCreditos(catalogo) {
  if (!["off", "shadow", "enforced"].includes(catalogo?.mode)) {
    throw new Error("Não foi possível verificar a configuração dos créditos. Tente novamente.");
  }
  return catalogo.mode;
}

export function validarOrcamento(quote, expectedMode) {
  if (
    typeof quote?.operation_id !== "string" ||
    !quote.operation_id.trim() ||
    quote.mode !== expectedMode ||
    !Number.isSafeInteger(quote.credits) ||
    quote.credits < 0 ||
    !Number.isSafeInteger(quote.price_cents) ||
    quote.price_cents < 0 ||
    !Number.isFinite(Date.parse(quote.expires_at))
  ) {
    throw new Error("O orçamento retornou incompleto. Nenhuma geração foi iniciada.");
  }
  return quote;
}

export function orcamentoExpirou(quote, now = Date.now()) {
  return !quote || Date.parse(quote.expires_at) <= now;
}

export function podeConfirmarOrcamento(quote, wallet, now = Date.now()) {
  if (orcamentoExpirou(quote, now)) return false;
  if (quote.mode === "shadow") return true;
  return (
    quote.mode === "enforced" &&
    Number.isSafeInteger(wallet?.available_credits) &&
    wallet.available_credits >= quote.credits
  );
}

export function classificarResultadoOperacao(operation) {
  if (operation?.status === "completed" && operation.result != null) return "completed";
  if (operation?.status === "failed") return "failed";
  return "pending";
}

export function identidadeCreditos(tenant, user) {
  // /auth/me-multitenant restaura user.tenant, mas não necessariamente selectedTenant.
  const userTenantId = user?.tenant?.id || user?.tenant_id;
  const tenantId = userTenantId || tenant?.id;
  if (!tenantId || !user?.id) {
    throw new Error("Selecione a empresa e entre novamente antes de gerar com IA.");
  }
  if (userTenantId && tenant?.id && String(userTenantId) !== String(tenant.id)) {
    throw new Error("A seleção da empresa mudou. Atualize a página antes de gerar com IA.");
  }
  return `${tenantId}:${user.id}`;
}

export function identidadeSessaoCreditos(tenant, savedUser, contextUser) {
  const identity = identidadeCreditos(tenant, savedUser);
  if (identity !== identidadeCreditos(tenant, contextUser)) {
    throw new Error("A sessão mudou em outra aba. Atualize a página antes de gerar com IA.");
  }
  return identity;
}

export function rejeicaoAntesDaExecucao(error, operation) {
  const status = error?.response?.status;
  return (
    operation?.status === "quoted" &&
    status >= 400 &&
    status < 500 &&
    ![408, 429].includes(status) &&
    error?.response?.data?.detail?.code !== "credit_operation_pending"
  );
}

export function apresentacaoMovimentacao(entry) {
  if (entry?.mode === "shadow" || entry?.kind === "shadow_usage") {
    return { label: "Simulação", note: "Consumo hipotético; saldo não alterado." };
  }
  const labels = {
    reserve: { label: "Reserva", note: "Separado do saldo disponível, ainda não consumido." },
    capture: {
      label: "Consumo da reserva",
      note: "Confirma a reserva anterior; não é uma segunda cobrança.",
    },
    release: { label: "Devolução da reserva", note: "Créditos devolvidos ao saldo disponível." },
  };
  return (
    labels[entry?.kind] || { label: "Movimentação", note: "Consulte o saldo após esta operação." }
  );
}

// A recuperação consulta o resultado existente: jamais repete a chamada paga.
export async function enviarGeracaoUmaVez(request, operationId, recover) {
  try {
    return { recovered: false, result: await request(operationId) };
  } catch (error) {
    return { recovered: true, result: await recover(error) };
  }
}

export function fontesHttpsSeguras(fontes) {
  if (!Array.isArray(fontes)) return [];
  const urls = fontes.flatMap((value) => {
    if (typeof value !== "string") return [];
    try {
      const url = new URL(value.trim());
      return url.protocol === "https:" && !url.username && !url.password ? [url.href] : [];
    } catch {
      return [];
    }
  });
  return [...new Set(urls)].slice(0, 8);
}

export function payloadImagemCredito(item, config) {
  return {
    produto_id: Number(item.produto_id),
    estilo: config.tema === "natural" ? "natural" : "profissional",
    orientacao: config.formato === "quadrado" ? "quadrada" : "vertical",
    prompt_usuario: item.prompt_criacao?.trim() || "",
    imagem_url: item.imagem_url_arte || item.imagem_url || "",
    file_sha256: null,
  };
}
