import { useState } from "react";

export function useExamesAnexadosResumo({ navigate, setDados }) {
  const [exameExpandidoId, setExameExpandidoId] = useState("");

  function atualizarResumoExame(exameAtualizado) {
    if (!exameAtualizado?.id) return;
    setDados((atual) => ({
      ...atual,
      items: (Array.isArray(atual.items) ? atual.items : []).map((item) =>
        String(item.exame_id) === String(exameAtualizado.id)
          ? {
              ...item,
              status: exameAtualizado.status || item.status,
              arquivo_nome: exameAtualizado.arquivo_nome || item.arquivo_nome,
              arquivo_url: exameAtualizado.arquivo_url || item.arquivo_url,
              tem_interpretacao_ia: Boolean(
                exameAtualizado.interpretacao_ia ||
                  exameAtualizado.interpretacao_ia_resumo ||
                  exameAtualizado.interpretacao_ia_payload
              ),
            }
          : item
      ),
    }));
  }

  function toggleExameExpandido(exameId) {
    setExameExpandidoId((atual) => (
      String(atual) === String(exameId) ? "" : String(exameId)
    ));
  }

  function abrirConsultaExame(item) {
    if (item.consulta_id) {
      navigate(`/veterinario/consultas/${item.consulta_id}`);
      return;
    }

    navigate(`/veterinario/consultas/nova?pet_id=${item.pet_id}`);
  }

  return {
    abrirConsultaExame,
    atualizarResumoExame,
    exameExpandidoId,
    toggleExameExpandido,
  };
}
