export default function useProdutosNovoRacao({
  opcoesApresentacoes,
  opcoesFases,
  setFormData,
}) {
  const handleClassificacaoRacaoChange = (valor) => {
    setFormData((prev) => ({
      ...prev,
      classificacao_racao: valor,
      linha_racao_id: valor === 'sim' ? prev.linha_racao_id : '',
      porte_animal_id: valor === 'sim' ? prev.porte_animal_id : '',
      fase_publico_id: valor === 'sim' ? prev.fase_publico_id : '',
      tipo_tratamento_id: valor === 'sim' ? prev.tipo_tratamento_id : '',
      sabor_proteina_id: valor === 'sim' ? prev.sabor_proteina_id : '',
      apresentacao_peso_id: valor === 'sim' ? prev.apresentacao_peso_id : '',
      peso_embalagem: valor === 'sim' ? prev.peso_embalagem : '',
      categoria_racao: valor === 'sim' ? prev.categoria_racao : '',
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
