const MENSAGEM_SEFAZ_INDISPONIVEL =
  "SEFAZ está temporariamente indisponível ou retornou uma resposta incompleta. Tente novamente em alguns minutos.";

const PADROES_ERRO_SEFAZ_INDISPONIVEL = [
  "Cloudflare",
  "origin web server",
  "invalid or incomplete response",
];

export function normalizarMensagemErroSefaz(err) {
  const status = Number(err?.response?.status || 0);
  const detalhe = err?.response?.data?.detail;
  const mensagemDetalhe =
    typeof detalhe === "string"
      ? detalhe.trim()
      : Array.isArray(detalhe)
        ? detalhe
            .map((item) => item?.msg)
            .filter(Boolean)
            .join("; ")
        : "";
  const mensagem = mensagemDetalhe || err?.message || "";

  if (/\b656\b/.test(mensagem)) {
    return `A SEFAZ bloqueou temporariamente as consultas (cStat 656). Aguarde pelo menos 1 hora desde a última tentativa e evite repetir a consulta nesse período.${
      mensagemDetalhe ? ` Detalhe: ${mensagemDetalhe}` : ""
    }`;
  }

  if (status === 429) {
    return `Muitas consultas à SEFAZ em pouco tempo. Aguarde antes de tentar novamente.${
      mensagemDetalhe ? ` Detalhe: ${mensagemDetalhe}` : ""
    }`;
  }

  if (err?.code === "ECONNABORTED" || err?.code === "ETIMEDOUT" || /timeout/i.test(mensagem)) {
    return "A consulta demorou mais que o esperado. Aguarde um momento antes de tentar novamente.";
  }

  if (!err?.response && (err?.code === "ERR_NETWORK" || /network error/i.test(mensagem))) {
    return "Não foi possível conectar ao sistema para consultar a SEFAZ. Confira sua conexão e tente novamente.";
  }

  if (
    PADROES_ERRO_SEFAZ_INDISPONIVEL.some((padrao) =>
      mensagem.toLowerCase().includes(padrao.toLowerCase()),
    )
  ) {
    return MENSAGEM_SEFAZ_INDISPONIVEL;
  }

  if (mensagemDetalhe) return mensagemDetalhe;
  if (status) return `Erro HTTP ${status} ao consultar a SEFAZ. Tente novamente em alguns minutos.`;
  return "Erro ao consultar a SEFAZ.";
}
