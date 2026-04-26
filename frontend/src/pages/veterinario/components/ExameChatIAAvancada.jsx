import { useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, Bot } from "lucide-react";

import { vetApi } from "../vetApi";
import ExameIABotoes from "./exameIA/ExameIABotoes";
import ExameIAChatBox from "./exameIA/ExameIAChatBox";
import ExameIAIntro from "./exameIA/ExameIAIntro";
import ExameIAResumoCard from "./exameIA/ExameIAResumoCard";
import { montarDadosExameIA } from "./exameIA/exameIAUtils";

export default function ExameChatIAAvancada({ petId, refreshToken, onNovoExame }) {
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
    const perg = pergunta.trim();
    setHistorico((mensagens) => [...mensagens, { role: "user", text: perg }]);
    setPergunta("");
    setCarregando(true);
    setErroLocal("");
    try {
      const response = await vetApi.chatExameIA(Number(exameId), perg);
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

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      enviar();
    }
  }

  return (
    <div className="overflow-hidden rounded-xl border border-indigo-200 bg-indigo-50">
      <button
        type="button"
        onClick={() => setExpandido((valorAtual) => !valorAtual)}
        className="flex w-full items-center justify-between px-4 py-3 text-left transition-colors hover:bg-indigo-100"
      >
        <div className="flex items-center gap-2">
          <Bot size={18} className="text-indigo-500" />
          <span className="text-sm font-semibold text-indigo-800">Exames do paciente + IA</span>
          {exames.length > 0 && (
            <span className="rounded-full bg-indigo-200 px-2 py-0.5 text-xs text-indigo-700">
              {exames.length} exame{exames.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
        <span className="text-xs text-indigo-500">{expandido ? "fechar" : "abrir"}</span>
      </button>

      {expandido && (
        <div className="space-y-3 px-4 pb-4">
          <ExameIAIntro />

          <div className="pt-1">
            <ExameIABotoes
              onNovoExame={onNovoExame}
              onProcessar={exameSelecionado ? processarExameSelecionado : undefined}
              processando={processando}
              temAnaliseIA={dadosIA.temAnaliseIA}
              temArquivo={dadosIA.temArquivo}
            />
          </div>

          {erroLocal && (
            <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-3 text-xs text-red-600">
              <AlertCircle size={14} />
              <span>{erroLocal}</span>
            </div>
          )}

          {!petId ? (
            <p className="text-xs italic text-indigo-500">Selecione o pet para carregar os exames.</p>
          ) : exames.length === 0 ? (
            <p className="text-xs italic text-indigo-500">
              Nenhum exame encontrado para este pet ainda. Voce ja pode cadastrar e anexar um arquivo acima.
            </p>
          ) : (
            <>
              <SeletorExame
                exameId={exameId}
                exames={exames}
                onChange={(valor) => {
                  setExameId(valor);
                  setHistorico([]);
                }}
              />

              {exameSelecionado && (
                <>
                  <ExameIAResumoCard dadosIA={dadosIA} exame={exameSelecionado} />

                  <ExameIAChatBox
                    carregando={carregando}
                    chatFimRef={chatFimRef}
                    historico={historico}
                    onEnviar={enviar}
                    onKeyDown={handleKeyDown}
                    pergunta={pergunta}
                    setPergunta={setPergunta}
                    textoVazio={
                      'Pergunte sobre o exame selecionado. Ex.: "Ha anemia no hemograma?", "Tem alerta importante?", "O raio-x sugere alteracao pulmonar?" ou "Qual conduta devo revisar?".'
                    }
                  />
                </>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

function SeletorExame({ exameId, exames, onChange }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-indigo-700">Exame para consultar</label>
      <select
        value={exameId}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border border-indigo-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
      >
        <option value="">Selecione um exame...</option>
        {exames.map((exame) => (
          <option key={exame.id} value={exame.id}>
            #{exame.id} - {exame.nome || exame.tipo || "Exame"}
            {exame.data_solicitacao ? ` - ${exame.data_solicitacao}` : ""}
          </option>
        ))}
      </select>
    </div>
  );
}
