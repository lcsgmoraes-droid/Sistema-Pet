import { useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle } from "lucide-react";

import { vetApi } from "../vetApi";
import ExameIABotoes from "./exameIA/ExameIABotoes";
import ExameIAChatBox from "./exameIA/ExameIAChatBox";
import ExameIAIntro from "./exameIA/ExameIAIntro";
import ExameIAResumoCard from "./exameIA/ExameIAResumoCard";
import { montarDadosExameIA } from "./exameIA/exameIAUtils";

export default function ExameAnexadoPainelIA({ resumo, onAtualizado, onNovoExame, onAbrirConsulta }) {
  const [exame, setExame] = useState(null);
  const [carregandoDetalhe, setCarregandoDetalhe] = useState(true);
  const [processando, setProcessando] = useState(false);
  const [carregandoChat, setCarregandoChat] = useState(false);
  const [erroLocal, setErroLocal] = useState("");
  const [pergunta, setPergunta] = useState("");
  const [historico, setHistorico] = useState([]);
  const chatFimRef = useRef(null);
  const dadosIA = useMemo(() => montarDadosExameIA(exame, resumo), [exame, resumo]);

  async function carregarDetalhe() {
    try {
      setCarregandoDetalhe(true);
      setErroLocal("");
      const response = await vetApi.listarExamesPet(resumo.pet_id);
      const lista = Array.isArray(response.data) ? response.data : response.data?.items ?? [];
      const encontrado = lista.find((item) => String(item.id) === String(resumo.exame_id));
      if (!encontrado) {
        setExame(null);
        setErroLocal("Nao foi possivel localizar os detalhes completos deste exame.");
        return;
      }
      setExame(encontrado);
      if (typeof onAtualizado === "function") onAtualizado(encontrado);
    } catch (error) {
      setExame(null);
      setErroLocal(error?.response?.data?.detail || "Erro ao carregar os detalhes deste exame.");
    } finally {
      setCarregandoDetalhe(false);
    }
  }

  useEffect(() => {
    carregarDetalhe();
  }, [resumo.exame_id, resumo.pet_id]);

  useEffect(() => {
    chatFimRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [historico]);

  async function processarExame() {
    if (!exame || processando) return;
    setProcessando(true);
    setErroLocal("");
    try {
      const response = dadosIA.temArquivo
        ? await vetApi.processarArquivoExameIA(Number(exame.id))
        : await vetApi.interpretarExameIA(Number(exame.id));
      setExame(response.data);
      if (typeof onAtualizado === "function") onAtualizado(response.data);
      setHistorico((mensagens) => [
        ...mensagens,
        {
          role: "ia",
          text: dadosIA.temArquivo
            ? "Arquivo processado com IA. Ja deixei o resumo clinico, os alertas e os achados prontos para revisao."
            : "Resultado interpretado com IA. O resumo e os alertas ja foram atualizados.",
        },
      ]);
    } catch (error) {
      setErroLocal(
        error?.response?.data?.detail ||
          (dadosIA.temArquivo
            ? "Nao foi possivel processar o arquivo com IA agora."
            : "Nao foi possivel interpretar o resultado deste exame.")
      );
    } finally {
      setProcessando(false);
    }
  }

  async function enviarPergunta() {
    if (!exame?.id || !pergunta.trim() || carregandoChat) return;
    const textoPergunta = pergunta.trim();
    setPergunta("");
    setHistorico((mensagens) => [...mensagens, { role: "user", text: textoPergunta }]);
    setCarregandoChat(true);
    setErroLocal("");
    try {
      const response = await vetApi.chatExameIA(Number(exame.id), textoPergunta);
      setHistorico((mensagens) => [...mensagens, { role: "ia", text: response.data?.resposta || "" }]);
      await carregarDetalhe();
    } catch (error) {
      setErroLocal(error?.response?.data?.detail || "Nao foi possivel consultar a IA deste exame.");
    } finally {
      setCarregandoChat(false);
    }
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      enviarPergunta();
    }
  }

  if (carregandoDetalhe) {
    return <p className="text-sm text-indigo-600">Carregando detalhes do exame...</p>;
  }

  if (!exame) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-3 text-sm text-red-600">
        {erroLocal || "Detalhes deste exame nao estao disponiveis no momento."}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <ExameIAIntro compacto />

      <ExameIABotoes
        consultaId={resumo.consulta_id}
        onAbrirConsulta={onAbrirConsulta}
        onNovoExame={onNovoExame}
        onProcessar={processarExame}
        processando={processando}
        temAnaliseIA={dadosIA.temAnaliseIA}
        temArquivo={dadosIA.temArquivo}
      />

      {erroLocal && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-3 text-xs text-red-600">
          <AlertCircle size={14} />
          <span>{erroLocal}</span>
        </div>
      )}

      <ExameIAResumoCard dadosIA={dadosIA} exame={exame} resumo={resumo} />

      <ExameIAChatBox
        carregando={carregandoChat}
        chatFimRef={chatFimRef}
        historico={historico}
        onEnviar={enviarPergunta}
        onKeyDown={handleKeyDown}
        pergunta={pergunta}
        setPergunta={setPergunta}
        textoVazio={
          'Pergunte sobre este exame. Ex.: "Ha anemia no hemograma?", "Tem alerta importante?", "O raio-x sugere alteracao pulmonar?" ou "Qual conduta devo revisar?".'
        }
      />
    </div>
  );
}
