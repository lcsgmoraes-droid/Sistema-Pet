import { useState } from "react";
import api from "../api";

export default function useCampanhasUnificacao({
  setSugestoes,
  carregarSugestoes,
}) {
  const [confirmandoMerge, setConfirmandoMerge] = useState(null);
  const [resultadoMerge, setResultadoMerge] = useState(null);

  const confirmarMerge = async (keepId, removeId, motivo) => {
    if (
      !globalThis.confirm(
        `Unificar clientes? O cliente #${removeId} sera mesclado no #${keepId}. Os dados de campanhas serao transferidos.`,
      )
    ) {
      return;
    }

    setConfirmandoMerge(`${keepId}-${removeId}`);
    try {
      const res = await api.post("/campanhas/unificacao/confirmar", {
        customer_keep_id: keepId,
        customer_remove_id: removeId,
        motivo,
      });
      setResultadoMerge(res.data);
      setSugestoes((prev) =>
        prev.filter(
          (s) =>
            !(s.cliente_a.id === keepId && s.cliente_b.id === removeId) &&
            !(s.cliente_a.id === removeId && s.cliente_b.id === keepId),
        ),
      );
    } catch (e) {
      alert("Erro ao unificar: " + (e?.response?.data?.detail || e.message));
    } finally {
      setConfirmandoMerge(null);
    }
  };

  const desfazerMerge = async (mergeId) => {
    if (
      !globalThis.confirm(
        "Desfazer esta unificacao? Os dados de campanhas serao restaurados.",
      )
    ) {
      return;
    }
    try {
      await api.delete(`/campanhas/unificacao/${mergeId}`);
      setResultadoMerge(null);
      await carregarSugestoes();
    } catch (e) {
      alert("Erro ao desfazer: " + (e?.response?.data?.detail || e.message));
    }
  };

  return {
    confirmandoMerge,
    resultadoMerge,
    confirmarMerge,
    desfazerMerge,
  };
}
