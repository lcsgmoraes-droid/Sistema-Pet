export function buildBillingNotice(assinatura) {
  if (!assinatura) return null;

  if (assinatura.acesso_operacional_ativo === false) {
    return {
      label: "Acesso suspenso pela administração",
      tone: "rose",
      icon: "lock",
      text: "O acesso foi suspenso por decisão administrativa. Entre em contato com a equipe CorePet.",
    };
  }

  const status = assinatura.status_efetivo || assinatura.status;
  const etapa = assinatura.avisos_cobranca?.etapa;
  const acessoCompletoManual = assinatura.acesso_completo_manual === true;

  if (!acessoCompletoManual && (status === "expired" || assinatura.trial_expirado)) {
    return {
      label: "Período de teste encerrado",
      tone: "amber",
      icon: "attention",
      text: "O período de teste terminou. O acesso continua liberado; nossa equipe entrará em contato para acompanhar a continuidade.",
    };
  }

  if (status === "past_due") {
    const mensagens = {
      lembrete:
        "Lembrete: há um pagamento em atraso. O acesso continua liberado; confira os dados em Meu plano.",
      atencao:
        "O pagamento continua em atraso. O acesso permanece liberado e nossa equipe ajudará na regularização.",
      revisao_manual:
        "O pagamento em atraso precisa de acompanhamento da nossa equipe. O acesso continua liberado durante a revisão.",
    };
    return {
      label: "Pagamento em atraso",
      tone: "amber",
      icon: "attention",
      text: mensagens[etapa] || mensagens.lembrete,
    };
  }

  if (status === "pending") {
    return {
      label: "Pagamento pendente",
      tone: "amber",
      icon: "clock",
      text: "Aguardamos a confirmação do pagamento. O acesso continua liberado; nossa equipe acompanhará a pendência.",
    };
  }

  if (["blocked", "refunded", "canceled"].includes(status)) {
    return {
      label: "Pagamento precisa de atenção",
      tone: "amber",
      icon: "attention",
      text: "Há uma pendência na cobrança para revisão da nossa equipe. O acesso continua liberado durante o acompanhamento.",
    };
  }

  const dias = assinatura.dias_restantes_trial;
  if (!acessoCompletoManual && status === "trial" && Number.isInteger(dias) && dias <= 7) {
    return {
      label: "Seu período de teste está terminando",
      tone: "blue",
      icon: "clock",
      text: `${dias === 1 ? "Falta" : "Faltam"} ${dias} ${dias === 1 ? "dia" : "dias"} para o fim do teste. O acesso continuará liberado e nossa equipe ajudará a definir o próximo passo.`,
    };
  }

  return null;
}
