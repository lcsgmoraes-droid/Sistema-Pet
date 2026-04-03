import { useState } from "react";
import api from "../api";

export default function useCampanhasFidelidade() {
  const [fidClienteId, setFidClienteId] = useState("");
  const [fidCarimbos, setFidCarimbos] = useState(null);
  const [fidLoadingCarimbos, setFidLoadingCarimbos] = useState(false);
  const [fidRemovendo, setFidRemovendo] = useState(null);
  const [fidIncluirEstornados, setFidIncluirEstornados] = useState(false);
  const [fidModalManual, setFidModalManual] = useState(false);
  const [fidLancandoManual, setFidLancandoManual] = useState(false);
  const [fidManualNota, setFidManualNota] = useState("");

  const carregarCarimbosCliente = async () => {
    if (!fidClienteId) return;
    setFidLoadingCarimbos(true);
    setFidCarimbos(null);
    try {
      const qs = fidIncluirEstornados ? "?incluir_estornados=true" : "";
      const res = await api.get(`/campanhas/clientes/${fidClienteId}/carimbos${qs}`);
      setFidCarimbos(res.data);
    } catch (e) {
      alert("Erro: " + (e?.response?.data?.detail || e.message));
    } finally {
      setFidLoadingCarimbos(false);
    }
  };

  const estornarCarimbo = async (stampId) => {
    const motivo = window.prompt("Motivo do estorno (opcional):");
    if (motivo === null) return;
    setFidRemovendo(stampId);
    try {
      const qs = motivo ? `?motivo=${encodeURIComponent(motivo)}` : "";
      await api.delete(`/campanhas/carimbos/${stampId}${qs}`);
      await carregarCarimbosCliente();
    } catch (e) {
      alert("Erro ao estornar: " + (e?.response?.data?.detail || e.message));
    } finally {
      setFidRemovendo(null);
    }
  };

  const lancarCarimboManual = async () => {
    if (!fidClienteId) {
      alert("Digite o ID do cliente primeiro.");
      return;
    }
    setFidLancandoManual(true);
    try {
      await api.post("/campanhas/carimbos/manual", {
        customer_id: Number(fidClienteId),
        nota: fidManualNota || "Carimbo lançado manualmente pelo operador",
      });
      setFidModalManual(false);
      setFidManualNota("");
      await carregarCarimbosCliente();
      alert("✅ Carimbo lançado com sucesso!");
    } catch (e) {
      alert("Erro: " + (e?.response?.data?.detail || e.message));
    } finally {
      setFidLancandoManual(false);
    }
  };

  return {
    fidClienteId,
    setFidClienteId,
    fidCarimbos,
    setFidCarimbos,
    fidLoadingCarimbos,
    fidRemovendo,
    fidIncluirEstornados,
    setFidIncluirEstornados,
    fidModalManual,
    setFidModalManual,
    fidLancandoManual,
    fidManualNota,
    setFidManualNota,
    carregarCarimbosCliente,
    estornarCarimbo,
    lancarCarimboManual,
  };
}
