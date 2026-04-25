import { useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, Bot, FlaskConical, Send } from "lucide-react";
import { vetApi } from "../vetApi";

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
  const payloadIA = exameSelecionado?.interpretacao_ia_payload || {};
  const alertasIA = Array.isArray(exameSelecionado?.interpretacao_ia_alertas)
    ? exameSelecionado.interpretacao_ia_alertas
    : [];
  const resultadoEstruturado =
    exameSelecionado?.resultado_json && typeof exameSelecionado.resultado_json === "object"
      ? Object.entries(exameSelecionado.resultado_json)
      : [];
  const achadosImagem = Array.isArray(payloadIA.achados_imagem) ? payloadIA.achados_imagem : [];
  const condutasSugeridas = Array.isArray(payloadIA.conduta_sugerida) ? payloadIA.conduta_sugerida : [];
  const limitacoesIA = Array.isArray(payloadIA.limitacoes) ? payloadIA.limitacoes : [];
  const temArquivo = Boolean(exameSelecionado?.arquivo_url);
  const temAnaliseIA = Boolean(
    exameSelecionado?.interpretacao_ia ||
      exameSelecionado?.interpretacao_ia_resumo ||
      alertasIA.length ||
      achadosImagem.length ||
      condutasSugeridas.length
  );
  const temResultadoBase = Boolean(
    (exameSelecionado?.resultado_texto || "").trim() || resultadoEstruturado.length
  );

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
      const response = temArquivo
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
          text: temArquivo
            ? "Arquivo processado com IA. Ja deixei o resumo clinico pronto para voce revisar e perguntar em seguida."
            : "Resultado interpretado com IA. Ja deixei a triagem automatica atualizada.",
        },
      ]);
    } catch (erro) {
      setErroLocal(
        erro?.response?.data?.detail ||
          (temArquivo
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
          <div className="rounded-lg border border-indigo-100 bg-white px-3 py-3 text-xs text-indigo-700">
            <p className="font-medium text-indigo-800">O que esta IA ja pode ajudar agora</p>
            <p className="mt-1">
              Processa hemograma, bioquimica, laudos em PDF e imagem anexada ao exame. Para imagem, ajuda a revisar
              raio-x, ultrassom e outros arquivos visuais como apoio clinico, sem substituir o laudo do especialista.
            </p>
          </div>

          <div className="flex flex-wrap gap-2 pt-1">
            {typeof onNovoExame === "function" && (
              <button
                type="button"
                onClick={onNovoExame}
                className="inline-flex items-center gap-2 rounded-lg border border-indigo-200 bg-white px-3 py-2 text-xs font-medium text-indigo-700 hover:bg-indigo-100"
              >
                <FlaskConical size={14} />
                Novo exame / anexar
              </button>
            )}
            {exameSelecionado && (
              <button
                type="button"
                onClick={processarExameSelecionado}
                disabled={processando}
                className="inline-flex items-center gap-2 rounded-lg border border-indigo-200 bg-indigo-600 px-3 py-2 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
              >
                {processando
                  ? "Processando..."
                  : temArquivo
                    ? temAnaliseIA
                      ? "Reprocessar arquivo + IA"
                      : "Processar arquivo + IA"
                    : "Interpretar resultado"}
              </button>
            )}
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
              <div>
                <label className="mb-1 block text-xs font-medium text-indigo-700">Exame para consultar</label>
                <select
                  value={exameId}
                  onChange={(event) => {
                    setExameId(event.target.value);
                    setHistorico([]);
                  }}
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

              {exameSelecionado && (
                <>
                  <div className="space-y-3 rounded-xl border border-indigo-200 bg-white px-3 py-3 text-xs text-indigo-700">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="font-semibold text-indigo-900">
                          Exame #{exameSelecionado.id} - {exameSelecionado.nome || exameSelecionado.tipo || "Exame"}
                        </div>
                        <p className="mt-1 text-indigo-600">
                          Tipo: {exameSelecionado.tipo || "nao informado"}
                          {exameSelecionado.data_solicitacao ? ` - solicitado em ${exameSelecionado.data_solicitacao}` : ""}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <span className={`rounded-full px-2 py-1 font-medium ${temArquivo ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>
                          {temArquivo ? "Arquivo anexado" : "Sem arquivo"}
                        </span>
                        <span className={`rounded-full px-2 py-1 font-medium ${temAnaliseIA ? "bg-indigo-100 text-indigo-700" : "bg-gray-100 text-gray-600"}`}>
                          {temAnaliseIA ? "IA pronta" : "IA pendente"}
                        </span>
                        <span className={`rounded-full px-2 py-1 font-medium ${temResultadoBase ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-600"}`}>
                          {temResultadoBase ? "Resultado carregado" : "Sem resultado base"}
                        </span>
                      </div>
                    </div>

                    {exameSelecionado.arquivo_nome && (
                      <div className="rounded-lg border border-indigo-100 bg-indigo-50 px-3 py-2">
                        <p className="font-medium text-indigo-800">Arquivo</p>
                        <div className="mt-1 flex flex-wrap items-center gap-3">
                          <span>{exameSelecionado.arquivo_nome}</span>
                          {exameSelecionado.arquivo_url && (
                            <a
                              href={exameSelecionado.arquivo_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-indigo-700 underline"
                            >
                              abrir arquivo
                            </a>
                          )}
                        </div>
                      </div>
                    )}

                    {(exameSelecionado.interpretacao_ia_resumo || exameSelecionado.interpretacao_ia) && (
                      <div className="rounded-lg border border-indigo-100 bg-indigo-50 px-3 py-3">
                        <p className="font-medium text-indigo-900">Resumo da triagem</p>
                        <p className="mt-1 text-sm text-indigo-800">
                          {exameSelecionado.interpretacao_ia_resumo || exameSelecionado.interpretacao_ia}
                        </p>
                        {exameSelecionado.interpretacao_ia && exameSelecionado.interpretacao_ia !== exameSelecionado.interpretacao_ia_resumo && (
                          <p className="mt-2 text-xs text-indigo-700">
                            <strong>Conclusao:</strong> {exameSelecionado.interpretacao_ia}
                          </p>
                        )}
                        {exameSelecionado.interpretacao_ia_confianca != null && (
                          <p className="mt-2 text-[11px] text-indigo-600">
                            Confianca estimada: {Math.round(Number(exameSelecionado.interpretacao_ia_confianca || 0) * 100)}%
                          </p>
                        )}
                      </div>
                    )}

                    {alertasIA.length > 0 && (
                      <div className="space-y-2">
                        <p className="font-medium text-indigo-900">Alertas automaticos</p>
                        <div className="flex flex-wrap gap-2">
                          {alertasIA.map((alerta, index) => {
                            const status = String(alerta.status || "atencao").toLowerCase();
                            const classes =
                              status === "alto" || status === "baixo"
                                ? "border-red-200 bg-red-50 text-red-700"
                                : "border-amber-200 bg-amber-50 text-amber-700";
                            return (
                              <span key={`${alerta.campo || "alerta"}_${index}`} className={`rounded-full border px-2 py-1 text-[11px] ${classes}`}>
                                {alerta.mensagem || alerta.campo}
                              </span>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {(achadosImagem.length > 0 || condutasSugeridas.length > 0 || limitacoesIA.length > 0) && (
                      <div className="grid gap-3 md:grid-cols-3">
                        <div className="rounded-lg border border-indigo-100 bg-gray-50 px-3 py-3">
                          <p className="font-medium text-gray-800">Achados da imagem</p>
                          {achadosImagem.length > 0 ? (
                            <ul className="mt-2 space-y-1 text-gray-600">
                              {achadosImagem.map((item, index) => (
                                <li key={`achado_${index}`}>- {item}</li>
                              ))}
                            </ul>
                          ) : (
                            <p className="mt-2 text-gray-500">Sem achados visuais destacados.</p>
                          )}
                        </div>
                        <div className="rounded-lg border border-indigo-100 bg-gray-50 px-3 py-3">
                          <p className="font-medium text-gray-800">Condutas sugeridas</p>
                          {condutasSugeridas.length > 0 ? (
                            <ul className="mt-2 space-y-1 text-gray-600">
                              {condutasSugeridas.map((item, index) => (
                                <li key={`conduta_${index}`}>- {item}</li>
                              ))}
                            </ul>
                          ) : (
                            <p className="mt-2 text-gray-500">Sem conduta sugerida automaticamente.</p>
                          )}
                        </div>
                        <div className="rounded-lg border border-indigo-100 bg-gray-50 px-3 py-3">
                          <p className="font-medium text-gray-800">Limitacoes</p>
                          {limitacoesIA.length > 0 ? (
                            <ul className="mt-2 space-y-1 text-gray-600">
                              {limitacoesIA.map((item, index) => (
                                <li key={`limite_${index}`}>- {item}</li>
                              ))}
                            </ul>
                          ) : (
                            <p className="mt-2 text-gray-500">Sem limitacoes especiais registradas.</p>
                          )}
                        </div>
                      </div>
                    )}

                    {resultadoEstruturado.length > 0 && (
                      <div className="space-y-2">
                        <p className="font-medium text-indigo-900">Valores estruturados</p>
                        <div className="flex flex-wrap gap-2">
                          {resultadoEstruturado.slice(0, 12).map(([chave, valor]) => (
                            <span key={chave} className="rounded-full border border-indigo-200 bg-white px-2 py-1 text-[11px] text-indigo-700">
                              {chave}: {String(valor)}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {!temArquivo && !temResultadoBase && (
                      <p className="text-xs text-amber-700">
                        Este exame ainda nao tem arquivo nem resultado em texto. Cadastre o anexo para a IA conseguir
                        analisar hemograma, bioquimica, laudos em PDF e imagens.
                      </p>
                    )}
                  </div>

                  {historico.length > 0 && (
                    <div className="max-h-56 space-y-2 overflow-y-auto rounded-lg border border-indigo-100 bg-white p-3">
                      {historico.map((mensagem, index) => (
                        <div
                          key={index}
                          className={`flex ${mensagem.role === "user" ? "justify-end" : "justify-start"}`}
                        >
                          <div
                            className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${
                              mensagem.role === "user"
                                ? "rounded-br-none bg-indigo-600 text-white"
                                : "rounded-bl-none bg-gray-100 text-gray-800"
                            }`}
                          >
                            {mensagem.role === "ia" && (
                              <span className="mb-0.5 block text-xs font-semibold text-indigo-500">IA</span>
                            )}
                            {mensagem.text}
                          </div>
                        </div>
                      ))}
                      {carregando && (
                        <div className="flex justify-start">
                          <div className="animate-pulse rounded-xl rounded-bl-none bg-gray-100 px-3 py-2 text-sm text-gray-500">
                            Analisando...
                          </div>
                        </div>
                      )}
                      <div ref={chatFimRef} />
                    </div>
                  )}

                  {historico.length === 0 && (
                    <p className="text-xs italic text-indigo-400">
                      Pergunte sobre o exame selecionado. Ex.: "Ha anemia no hemograma?", "Tem alerta importante?",
                      "O raio-x sugere alteracao pulmonar?" ou "Qual conduta devo revisar?".
                    </p>
                  )}

                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={pergunta}
                      onChange={(event) => setPergunta(event.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Digite sua pergunta sobre o exame..."
                      disabled={carregando}
                      className="flex-1 rounded-lg border border-indigo-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 disabled:opacity-60"
                    />
                    <button
                      type="button"
                      onClick={enviar}
                      disabled={!pergunta.trim() || carregando}
                      className="flex items-center gap-1 rounded-lg bg-indigo-600 px-3 py-2 text-sm text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
                    >
                      <Send size={14} />
                    </button>
                  </div>
                </>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
