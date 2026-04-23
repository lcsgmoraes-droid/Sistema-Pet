export default function useProdutosNovoRacao({
  opcoesApresentacoes,
  opcoesFases,
  setFormData,
}) {
  const handleClassificacaoRacaoChange = (valor) => {
    const ehRacao = valor === 'sim';

    setFormData((prev) => ({
      ...prev,
      eh_racao: ehRacao,
      linha_racao_id: ehRacao ? prev.linha_racao_id : '',
      porte_animal_id: ehRacao ? prev.porte_animal_id : '',
      fase_publico_id: ehRacao ? prev.fase_publico_id : '',
      tipo_tratamento_id: ehRacao ? prev.tipo_tratamento_id : '',
      sabor_proteina_id: ehRacao ? prev.sabor_proteina_id : '',
      apresentacao_peso_id: ehRacao ? prev.apresentacao_peso_id : '',
      classificacao_racao: ehRacao ? prev.classificacao_racao : '',
      peso_embalagem: ehRacao ? prev.peso_embalagem : '',
      categoria_racao: ehRacao ? prev.categoria_racao : '',
      especies_indicadas: ehRacao ? prev.especies_indicadas : 'both',
      tabela_nutricional: ehRacao ? prev.tabela_nutricional : '',
      tabela_consumo: ehRacao ? prev.tabela_consumo : '',
    }));
  };

  const handleFasePublicoChange = (faseId) => {
    const faseSelecionada = opcoesFases.find((fase) => String(fase.id) === String(faseId));

    setFormData((prev) => ({
      ...prev,
      fase_publico_id: faseId,
      categoria_racao: faseSelecionada ? faseSelecionada.nome : '',
    }));
  };

  const handleApresentacaoPesoChange = (apresentacaoId) => {
    const apresentacao = opcoesApresentacoes.find(
      (item) => String(item.id) === String(apresentacaoId),
    );

    setFormData((prev) => ({
      ...prev,
      apresentacao_peso_id: apresentacaoId,
      peso_embalagem: apresentacao ? String(apresentacao.peso_kg) : prev.peso_embalagem,
    }));
  };

  return {
    handleClassificacaoRacaoChange,
    handleFasePublicoChange,
    handleApresentacaoPesoChange,
  };
}
