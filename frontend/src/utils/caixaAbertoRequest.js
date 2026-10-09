export function criarConsultaCaixaAberto(consultar) {
  const emAndamento = new Map();
  return (opcoes = {}) => {
    const compact = opcoes.compact === true;
    // Uma consulta cancelável pertence ao seu solicitante; não cancela outras telas.
    if (opcoes.signal) return consultar({ compact, signal: opcoes.signal });
    const chave = compact ? "compact" : "full";
    if (!emAndamento.has(chave)) {
      const requisicao = Promise.resolve()
        .then(() => consultar({ compact }))
        .finally(() => {
          if (emAndamento.get(chave) === requisicao) emAndamento.delete(chave);
        });
      emAndamento.set(chave, requisicao);
    }
    return emAndamento.get(chave);
  };
}
