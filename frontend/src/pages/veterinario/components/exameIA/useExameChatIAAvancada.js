import { useEffect, useMemo, useRef, useState } from "react";

import { vetApi } from "../../vetApi";
import { montarDadosExameIA } from "./exameIAUtils";

export function useExameChatIAAvancada({ petId, refreshToken }) {
  const [expandido, setExpandido] = useState(true);
  const [exames, setExames] = useState([]);
  const [exameId, setExameId] = useState("");
  const [pergunta, setPergunta] = useState("");
  const [historico, setHistorico] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [processando, setProcessando] = useState(false);
  const [erroLocal, setErroLocal] = useState("");
  const chatFimRef = useRef(null);

  const exameSelecionado = useMemo(
    () => exames.find((item) => String(item.id) === String(exameId)),
    [exames, exameId]
  );
  const dadosIA = useMemo(() => montarDadosExameIA(exameSelecionado), [exameSelecionado]);

  async function carregarExames(preferidoId = null) {
    if (!petId) return;
    try {
      const response = await vetApi.listarExamesPet(petId);
      const lista = Array.isArray(response.data) ? response.data : response.data?.items ?? [];
      setExames(lista);
      setExameId((anterior) => {
        const alvo = preferidoId != null ? String(preferidoId) : anterior;
        if (alvo && lista.some((item) => String(item.id) === alvo)) return alvo;
        return lista.length === 1 ? String(lista[0].id) : "";
      });
    } catch {
      setExames([]);
    }
  }

  useEffect(() => {
    carregarExames();
  }, [petId, refreshToken]);

  useEffect(() => {
    chatFimRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [historico]);

  useEffect(() => {
    setErroLocal("");
  }, [exameId]);

  async function processarExameSelecionado() {
    if (!exameSelecionado || processando) return;
    setProcessando(true);
    setErroLocal("");
    try {
      const response = dadosIA.temArquivo
        ? await vetApi.processarArquivoExameIA(Number(exameSelecionado.id))
        : await vetApi.interpretarExameIA(Number(exameSelecionado.id));
      const exameAtualizado = response.data;
      setExames((lista) =>
        lista.map((item) => (String(item.id) === String(exameAtualizado.id) ? exameAtualizado : item))
      );
      setHistorico((mensagens) => [
        ...mensagens,
        {
          role: "ia",
          text: dadosIA.temArquivo
            ? "Arquivo processado com IA. Ja deixei o resumo clinico pronto para voce revisar e perguntar em seguida."
            : "Resultado interpretado com IA. Ja deixei a triagem automatica atualizada.",
        },
      ]);
    } catch (erro) {
      setErroLocal(
        erro?.response?.data?.detail ||
          (dadosIA.temArquivo
            ? "Nao foi possivel processar o arquivo com IA agora."
            : "Nao foi possivel interpretar o resultado agora.")
      );
    } finally {
      setProcessando(false);
    }
  }

  async function enviar() {
    if (!exameId || !pergunta.trim() || carregando) return;
    const perguntaAtual = pergunta.trim();
    setHistorico((mensagens) => [...mensagens, { role: "user", text: perguntaAtual }]);
    setPergunta("");
    setCarregando(true);
    setErroLocal("");
    try {
      const response = await vetApi.chatExameIA(Number(exameId), perguntaAtual);
      setHistorico((mensagens) => [...mensagens, { role: "ia", text: response.data.resposta }]);
      await carregarExames(exameId);
    } catch {
      setHistorico((mensagens) => [
        ...mensagens,
        { role: "ia", text: "Erro ao consultar a IA. Tente novamente." },
      ]);
    } finally {
      setCarregando(false);
    }
  }

  function alterarExame(valor) {
    setExameId(valor);
    setHistorico([]);
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      enviar();
    }
  }

  return {
    alterarExame,
    carregando,
    chatFimRef,
    dadosIA,
    enviar,
    erroLocal,
    exameId,
    exames,
    exameSelecionado,
    expandido,
    handleKeyDown,
    historico,
    pergunta,
    processando,
    processarExameSelecionado,
    setExpandido,
    setPergunta,
  };
}
