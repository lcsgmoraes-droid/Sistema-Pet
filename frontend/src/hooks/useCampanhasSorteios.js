import { useState } from "react";
import api from "../api";

const DEFAULT_SORTEIO = {
  name: "",
  description: "",
  prize_description: "",
  rank_filter: "",
  draw_date: "",
  auto_execute: false,
};

export default function useCampanhasSorteios({
  setSorteios,
  carregarSorteios,
  setCodigosOffline,
  setLoadingCodigosOffline,
}) {
  const [modalSorteio, setModalSorteio] = useState(false);
  const [novoSorteio, setNovoSorteio] = useState(DEFAULT_SORTEIO);
  const [criandoSorteio, setCriandoSorteio] = useState(false);
  const [erroCriarSorteio, setErroCriarSorteio] = useState("");
  const [executandoSorteio, setExecutandoSorteio] = useState(null);
  const [inscrevendo, setInscrevendo] = useState(null);
  const [sorteioResultado, setSorteioResultado] = useState(null);
  const [modalCodigosOffline, setModalCodigosOffline] = useState(null);

  const criarSorteio = async () => {
    setErroCriarSorteio("");
    if (!novoSorteio.name.trim()) {
      setErroCriarSorteio("Nome obrigatório.");
      return;
    }
    setCriandoSorteio(true);
    try {
      await api.post("/campanhas/sorteios", novoSorteio);
      setModalSorteio(false);
      setNovoSorteio(DEFAULT_SORTEIO);
      await carregarSorteios();
    } catch (e) {
      setErroCriarSorteio(
        e?.response?.data?.detail || "Erro ao criar sorteio.",
      );
    } finally {
      setCriandoSorteio(false);
    }
  };

  const inscreverSorteio = async (drawingId) => {
    setInscrevendo(drawingId);
    try {
      const res = await api.post(`/campanhas/sorteios/${drawingId}/inscrever`);
      setSorteios((prev) =>
        prev.map((s) =>
          s.id === drawingId
            ? {
                ...s,
                status: res.data.status,
                total_participantes: res.data.total_inscritos,
              }
            : s,
        ),
      );
    } catch (e) {
      alert("Erro ao inscrever: " + (e?.response?.data?.detail || e.message));
    } finally {
      setInscrevendo(null);
    }
  };

  const executarSorteio = async (drawingId) => {
    if (!window.confirm("Executar o sorteio agora? Esta ação é irreversível.")) {
      return;
    }
    setExecutandoSorteio(drawingId);
    try {
      const res = await api.post(`/campanhas/sorteios/${drawingId}/executar`);
      setSorteioResultado(res.data);
      await carregarSorteios();
    } catch (e) {
      alert("Erro ao executar: " + (e?.response?.data?.detail || e.message));
    } finally {
      setExecutandoSorteio(null);
    }
  };

  const cancelarSorteio = async (drawingId, nome) => {
    if (!window.confirm(`Cancelar o sorteio "${nome}"?`)) return;
    try {
      await api.delete(`/campanhas/sorteios/${drawingId}`);
      setSorteios((prev) => prev.filter((s) => s.id !== drawingId));
    } catch (e) {
      alert("Erro ao cancelar: " + (e?.response?.data?.detail || e.message));
    }
  };

  const abrirCodigosOffline = async (sorteio) => {
    setModalCodigosOffline(sorteio);
    setCodigosOffline([]);
    setLoadingCodigosOffline(true);
    try {
      const res = await api.get(
        `/campanhas/sorteios/${sorteio.id}/codigos-offline`,
        { params: { limit: 500 } },
      );
      setCodigosOffline(res.data.codigos || res.data);
    } catch (e) {
      alert("Erro ao carregar códigos: " + (e?.response?.data?.detail || e.message));
      setModalCodigosOffline(null);
    } finally {
      setLoadingCodigosOffline(false);
    }
  };

  return {
    modalSorteio,
    setModalSorteio,
    novoSorteio,
    setNovoSorteio,
    criandoSorteio,
    erroCriarSorteio,
    setErroCriarSorteio,
    executandoSorteio,
    inscrevendo,
    sorteioResultado,
    setSorteioResultado,
    modalCodigosOffline,
    setModalCodigosOffline,
    criarSorteio,
    inscreverSorteio,
    executarSorteio,
    cancelarSorteio,
    abrirCodigosOffline,
  };
}
