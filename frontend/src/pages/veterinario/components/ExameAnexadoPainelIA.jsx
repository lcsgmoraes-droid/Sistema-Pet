import { useEffect, useRef, useState } from "react";
import { AlertCircle, FlaskConical, Send } from "lucide-react";
import { vetApi } from "../vetApi";

function formatarData(iso) {
  if (!iso) return "-";
  const data = new Date(`${iso}T12:00:00`);
  return data.toLocaleDateString("pt-BR");
}

export default function ExameAnexadoPainelIA({ resumo, onAtualizado, onNovoExame, onAbrirConsulta }) {
  const [exame, setExame] = useState(null);
  const [carregandoDetalhe, setCarregandoDetalhe] = useState(true);
  const [processando, setProcessando] = useState(false);
  const [carregandoChat, setCarregandoChat] = useState(false);
  const [erroLocal, setErroLocal] = useState("");
  const [pergunta, setPergunta] = useState("");
  const [historico, setHistorico] = useState([]);
  const chatFimRef = useRef(null);

  const payloadIA = exame?.interpretacao_ia_payload || {};
  const alertasIA = Array.isArray(exame?.interpretacao_ia_alertas) ? exame.interpretacao_ia_alertas : [];
  const resultadoEstruturado =
    exame?.resultado_json && typeof exame.resultado_json === "object"
      ? Object.entries(exame.resultado_json)
      : [];
  const achadosImagem = Array.isArray(payloadIA.achados_imagem) ? payloadIA.achados_imagem : [];
  const condutasSugeridas = Array.isArray(payloadIA.conduta_sugerida) ? payloadIA.conduta_sugerida : [];
  const limitacoesIA = Array.isArray(payloadIA.limitacoes) ? payloadIA.limitacoes : [];
  const temArquivo = Boolean(exame?.arquivo_url || resumo?.arquivo_url);
  const temAnaliseIA = Boolean(
    exame?.interpretacao_ia ||
      exame?.interpretacao_ia_resumo ||
      alertasIA.length ||
      achadosImagem.length ||
      condutasSugeridas.length
  );
  const temResultadoBase = Boolean(
    (exame?.resultado_texto || "").trim() || resultadoEstruturado.length
  );

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
      const response = temArquivo
        ? await vetApi.processarArquivoExameIA(Number(exame.id))
        : await vetApi.interpretarExameIA(Number(exame.id));
      setExame(response.data);
      if (typeof onAtualizado === "function") onAtualizado(response.data);
      setHistorico((mensagens) => [
        ...mensagens,
        {
          role: "ia",
          text: temArquivo
            ? "Arquivo processado com IA. Ja deixei o resumo clinico, os alertas e os achados prontos para revisao."
            : "Resultado interpretado com IA. O resumo e os alertas ja foram atualizados.",
        },
      ]);
    } catch (error) {
      setErroLocal(
        error?.response?.data?.detail ||
          (temArquivo
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
      <div className="rounded-lg border border-indigo-100 bg-white px-3 py-3 text-xs text-indigo-700">
        <p className="font-medium text-indigo-800">O que esta IA ja pode ajudar agora</p>
        <p className="mt-1">
          Processa hemograma, bioquimica, laudos em PDF e imagem anexada ao exame. Para raio-x, ultrassom e outras
          imagens, a IA ajuda como apoio clinico e nao substitui o laudo do especialista.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onNovoExame}
          className="inline-flex items-center gap-2 rounded-lg border border-indigo-200 bg-white px-3 py-2 text-xs font-medium text-indigo-700 hover:bg-indigo-100"
        >
          <FlaskConical size={14} />
          Novo exame / anexar
        </button>
        <button
          type="button"
          onClick={processarExame}
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
        <button
          type="button"
          onClick={onAbrirConsulta}
          className="inline-flex items-center gap-2 rounded-lg border border-orange-200 bg-white px-3 py-2 text-xs font-medium text-orange-700 hover:bg-orange-50"
        >
          {resumo.consulta_id ? `Abrir consulta #${resumo.consulta_id}` : "Abrir consulta"}
        </button>
      </div>

      {erroLocal && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-3 text-xs text-red-600">
          <AlertCircle size={14} />
          <span>{erroLocal}</span>
        </div>
      )}

      <div className="space-y-3 rounded-xl border border-indigo-200 bg-white px-3 py-3 text-xs text-indigo-700">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="font-semibold text-indigo-900">
              Exame #{exame.id} - {exame.nome || exame.tipo || "Exame"}
            </div>
            <p className="mt-1 text-indigo-600">
              Tipo: {exame.tipo || "nao informado"}
              {exame.data_solicitacao ? ` - solicitado em ${formatarData(exame.data_solicitacao)}` : ""}
            </p>
            <p className="mt-1 text-indigo-600">
              Tutor: {resumo.tutor_nome || "-"} | Pet: {resumo.pet_nome || "-"}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <span
              className={`rounded-full px-2 py-1 font-medium ${
                temArquivo ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
              }`}
            >
              {temArquivo ? "Arquivo anexado" : "Sem arquivo"}
            </span>
            <span
              className={`rounded-full px-2 py-1 font-medium ${
                temAnaliseIA ? "bg-indigo-100 text-indigo-700" : "bg-gray-100 text-gray-600"
              }`}
            >
              {temAnaliseIA ? "IA pronta" : "IA pendente"}
            </span>
            <span
              className={`rounded-full px-2 py-1 font-medium ${
                temResultadoBase ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-600"
              }`}
            >
              {temResultadoBase ? "Resultado carregado" : "Sem resultado base"}
            </span>
          </div>
        </div>

        {exame.arquivo_nome && (
          <div className="rounded-lg border border-indigo-100 bg-indigo-50 px-3 py-2">
            <p className="font-medium text-indigo-800">Arquivo</p>
            <div className="mt-1 flex flex-wrap items-center gap-3">
              <span>{exame.arquivo_nome}</span>
              {exame.arquivo_url && (
                <a
                  href={exame.arquivo_url}
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

        {(exame.interpretacao_ia_resumo || exame.interpretacao_ia) && (
          <div className="rounded-lg border border-indigo-100 bg-indigo-50 px-3 py-3">
            <p className="font-medium text-indigo-900">Resumo da triagem</p>
            <p className="mt-1 text-sm text-indigo-800">
              {exame.interpretacao_ia_resumo || exame.interpretacao_ia}
            </p>
            {exame.interpretacao_ia &&
              exame.interpretacao_ia !== exame.interpretacao_ia_resumo && (
                <p className="mt-2 text-xs text-indigo-700">
                  <strong>Conclusao:</strong> {exame.interpretacao_ia}
                </p>
              )}
            {exame.interpretacao_ia_confianca != null && (
              <p className="mt-2 text-[11px] text-indigo-600">
                Confianca estimada: {Math.round(Number(exame.interpretacao_ia_confianca || 0) * 100)}%
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
                  <span
                    key={`${alerta.campo || "alerta"}_${index}`}
                    className={`rounded-full border px-2 py-1 text-[11px] ${classes}`}
                  >
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
                <span
                  key={chave}
                  className="rounded-full border border-indigo-200 bg-white px-2 py-1 text-[11px] text-indigo-700"
                >
                  {chave}: {String(valor)}
                </span>
              ))}
            </div>
          </div>
        )}

        {!temArquivo && !temResultadoBase && (
          <p className="text-xs text-amber-700">
            Este exame ainda nao tem arquivo nem resultado em texto. Cadastre o anexo para a IA conseguir analisar
            hemograma, bioquimica, laudos em PDF e imagens.
          </p>
        )}
      </div>

      {historico.length > 0 && (
        <div className="max-h-56 space-y-2 overflow-y-auto rounded-lg border border-indigo-100 bg-white p-3">
          {historico.map((mensagem, index) => (
            <div key={index} className={`flex ${mensagem.role === "user" ? "justify-end" : "justify-start"}`}>
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
          {carregandoChat && (
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
        <p className="text-xs italic text-indigo-500">
          Pergunte sobre este exame. Ex.: "Ha anemia no hemograma?", "Tem alerta importante?", "O raio-x sugere
          alteracao pulmonar?" ou "Qual conduta devo revisar?".
        </p>
      )}

      <div className="flex gap-2">
        <input
          type="text"
          value={pergunta}
          onChange={(event) => setPergunta(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Digite sua pergunta sobre o exame..."
          disabled={carregandoChat}
          className="flex-1 rounded-lg border border-indigo-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 disabled:opacity-60"
        />
        <button
          type="button"
          onClick={enviarPergunta}
          disabled={!pergunta.trim() || carregandoChat}
          className="flex items-center gap-1 rounded-lg bg-indigo-600 px-3 py-2 text-sm text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  );
}
