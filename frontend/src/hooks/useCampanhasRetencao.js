import { useState } from "react";
import api from "../api";

export const NOVA_REGRA_RETENCAO_PADRAO = {
  name: "",
  inactivity_days: 30,
  coupon_type: "percent",
  coupon_value: 10,
  coupon_valid_days: 7,
  coupon_channel: "all",
  notification_message:
    "Ola, {nome}! Sentimos sua falta. Use o cupom {code} e ganhe {value}% de desconto.",
  priority: 50,
};

export default function useCampanhasRetencao({ carregarRetencao }) {
  const [retencaoEditando, setRetencaoEditando] = useState(null);
  const [salvandoRetencao, setSalvandoRetencao] = useState(false);
  const [deletandoRetencao, setDeletandoRetencao] = useState(null);

  const salvarRetencao = async (form) => {
    setSalvandoRetencao(true);
    try {
      if (form.id) {
        await api.put(`/campanhas/retencao/${form.id}`, form);
      } else {
        await api.post("/campanhas/retencao", form);
      }
      setRetencaoEditando(null);
      await carregarRetencao();
    } catch (e) {
      alert("Erro ao salvar: " + (e?.response?.data?.detail || e.message));
    } finally {
      setSalvandoRetencao(false);
    }
  };

  const deletarRetencao = async (id) => {
    if (!window.confirm("Remover esta regra de retencao?")) return;
    setDeletandoRetencao(id);
    try {
      await api.delete(`/campanhas/retencao/${id}`);
      await carregarRetencao();
    } catch (e) {
      alert("Erro ao remover: " + (e?.response?.data?.detail || e.message));
    } finally {
      setDeletandoRetencao(null);
    }
  };

  return {
    retencaoEditando,
    setRetencaoEditando,
    salvandoRetencao,
    deletandoRetencao,
    salvarRetencao,
    deletarRetencao,
  };
}
