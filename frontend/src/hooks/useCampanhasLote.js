import { useState } from "react";
import api from "../api";

const DEFAULT_LOTE_FORM = {
  nivel: "todos",
  assunto: "",
  mensagem: "",
};

export default function useCampanhasLote() {
  const [modalLote, setModalLote] = useState(false);
  const [loteForm, setLoteForm] = useState(DEFAULT_LOTE_FORM);
  const [enviandoLote, setEnviandoLote] = useState(false);
  const [resultadoLote, setResultadoLote] = useState(null);

  const enviarLote = async () => {
    if (!loteForm.assunto.trim() || !loteForm.mensagem.trim()) {
      alert("Preencha assunto e mensagem.");
      return;
    }

    setEnviandoLote(true);
    setResultadoLote(null);
    try {
      const res = await api.post("/campanhas/ranking/envio-em-lote", loteForm);
      setResultadoLote(res.data);
    } catch (e) {
      alert("Erro ao enviar: " + (e?.response?.data?.detail || e.message));
    } finally {
      setEnviandoLote(false);
    }
  };

  return {
    modalLote,
    setModalLote,
    loteForm,
    setLoteForm,
    enviandoLote,
    resultadoLote,
    setResultadoLote,
    enviarLote,
  };
}
