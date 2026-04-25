import { useState } from "react";

import { vetApi } from "../vetApi";

function baixarArquivo(blob, nomeArquivo) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = nomeArquivo;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export default function useConsultaPdfDownloads({
  consultaIdAtual,
  setErro,
}) {
  const [baixandoPdf, setBaixandoPdf] = useState(false);

  async function baixarProntuarioPdf() {
    if (!consultaIdAtual) return;
    setBaixandoPdf(true);
    setErro(null);
    try {
      const res = await vetApi.baixarProntuarioPdf(consultaIdAtual);
      baixarArquivo(res.data, `prontuario_consulta_${consultaIdAtual}.pdf`);
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Não foi possível baixar o prontuário em PDF.");
    } finally {
      setBaixandoPdf(false);
    }
  }

  async function baixarUltimaReceitaPdf() {
    if (!consultaIdAtual) return;
    setBaixandoPdf(true);
    setErro(null);
    try {
      const lista = await vetApi.listarPrescricoes(consultaIdAtual);
      const prescricoes = Array.isArray(lista.data) ? lista.data : (lista.data?.items ?? []);
      if (!prescricoes.length) {
        setErro("Essa consulta não tem prescrição emitida.");
        return;
      }

      const ultima = prescricoes[prescricoes.length - 1];
      const res = await vetApi.baixarPrescricaoPdf(ultima.id);
      baixarArquivo(res.data, `${ultima.numero || `prescricao_${ultima.id}`}.pdf`);
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Não foi possível baixar a receita em PDF.");
    } finally {
      setBaixandoPdf(false);
    }
  }

  return {
    baixandoPdf,
    baixarProntuarioPdf,
    baixarUltimaReceitaPdf,
  };
}
