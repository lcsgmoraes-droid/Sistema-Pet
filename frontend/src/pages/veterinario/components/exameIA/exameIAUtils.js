export function formatarDataExame(iso) {
  if (!iso) return "-";
  const data = new Date(`${iso}T12:00:00`);
  return data.toLocaleDateString("pt-BR");
}

export function montarDadosExameIA(exame, resumo = {}) {
  const payloadIA = exame?.interpretacao_ia_payload || {};
  const alertasIA = Array.isArray(exame?.interpretacao_ia_alertas) ? exame.interpretacao_ia_alertas : [];
  const resultadoEstruturado =
    exame?.resultado_json && typeof exame.resultado_json === "object"
      ? Object.entries(exame.resultado_json)
      : [];
  const achadosImagem = Array.isArray(payloadIA.achados_imagem) ? payloadIA.achados_imagem : [];
  const condutasSugeridas = Array.isArray(payloadIA.conduta_sugerida) ? payloadIA.conduta_sugerida : [];
  const limitacoesIA = Array.isArray(payloadIA.limitacoes) ? payloadIA.limitacoes : [];
  const temArquivo = Boolean(exame?.arquivo_url || resumo?.arquivo_url);
  const temAnaliseIA = Boolean(
    exame?.interpretacao_ia ||
      exame?.interpretacao_ia_resumo ||
      alertasIA.length ||
      achadosImagem.length ||
      condutasSugeridas.length
  );
  const temResultadoBase = Boolean((exame?.resultado_texto || "").trim() || resultadoEstruturado.length);

  return {
    achadosImagem,
    alertasIA,
    condutasSugeridas,
    limitacoesIA,
    resultadoEstruturado,
    temAnaliseIA,
    temArquivo,
    temResultadoBase,
  };
}
