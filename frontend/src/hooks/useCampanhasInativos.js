import { useState } from "react";
import api from "../api";

const DEFAULT_ENVIO_INATIVOS_FORM = {
  assunto: "Sentimos sua falta! 🐾",
  mensagem: "",
};

export default function useCampanhasInativos() {
  const [modalEnvioInativos, setModalEnvioInativos] = useState(null);
  const [envioInativosForm, setEnvioInativosForm] = useState(
    DEFAULT_ENVIO_INATIVOS_FORM,
  );
  const [enviandoInativos, setEnviandoInativos] = useState(false);
  const [resultadoEnvioInativos, setResultadoEnvioInativos] = useState(null);

  const enviarParaInativos = async () => {
    if (
      !envioInativosForm.assunto.trim() ||
      !envioInativosForm.mensagem.trim()
    ) {
      alert("Preencha o assunto e a mensagem antes de enviar.");
      return;
    }

    setEnviandoInativos(true);
    setResultadoEnvioInativos(null);
    try {
      const res = await api.post("/campanhas/notificacoes/inativos", {
        dias_sem_compra: modalEnvioInativos,
        assunto: envioInativosForm.assunto,
        mensagem: envioInativosForm.mensagem,
      });
      setResultadoEnvioInativos(res.data);
    } catch (e) {
      alert("Erro ao enviar: " + (e?.response?.data?.detail || e.message));
    } finally {
      setEnviandoInativos(false);
    }
  };

  return {
    modalEnvioInativos,
    setModalEnvioInativos,
    envioInativosForm,
    setEnvioInativosForm,
    enviandoInativos,
    resultadoEnvioInativos,
    setResultadoEnvioInativos,
    enviarParaInativos,
  };
}
