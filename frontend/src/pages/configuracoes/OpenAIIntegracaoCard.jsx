import { useEffect, useMemo, useState } from "react";
import {
  FiAlertTriangle,
  FiCheckCircle,
  FiCpu,
  FiEye,
  FiEyeOff,
  FiKey,
  FiSave,
} from "react-icons/fi";
import { api } from "../../services/api";

const MODELOS_RECOMENDADOS = [
  { value: "gpt-4o-mini", label: "gpt-4o-mini (recomendado para começar)" },
  { value: "gpt-4.1-mini", label: "gpt-4.1-mini" },
  { value: "gpt-4.1", label: "gpt-4.1" },
];

export default function OpenAIIntegracaoCard() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [mostrarChave, setMostrarChave] = useState(false);
  const [configExiste, setConfigExiste] = useState(false);
  const [temChaveSalva, setTemChaveSalva] = useState(false);
  const [msg, setMsg] = useState(null);
  const [form, setForm] = useState({
    openai_api_key: "",
    model_preference: "gpt-4o-mini",
  });

  const ajudaAtual = useMemo(
    () =>
      temChaveSalva
        ? "Chave OpenAI já cadastrada para este tenant. Se quiser trocar, cole uma nova abaixo."
        : "Cole aqui a chave da OpenAI para habilitar análise de PDF, hemograma e imagens nos exames veterinários.",
    [temChaveSalva]
  );

  useEffect(() => {
    carregarConfig();
  }, []);

  function mostrarMensagem(tipo, texto) {
    setMsg({ tipo, texto });
    window.clearTimeout(window.__openaiIntegracaoToastTimer);
    window.__openaiIntegracaoToastTimer = window.setTimeout(() => setMsg(null), 6000);
  }

  async function carregarConfig() {
    try {
      setLoading(true);
      const response = await api.get("/whatsapp/config");
      const data = response.data;
      if (data) {
        setConfigExiste(true);
        setTemChaveSalva(Boolean(data.openai_api_key));
        setForm((prev) => ({
          ...prev,
          openai_api_key: "",
          model_preference: data.model_preference || "gpt-4o-mini",
        }));
      } else {
        setConfigExiste(false);
        setTemChaveSalva(false);
      }
    } catch (error) {
      if (error?.response?.status === 404) {
        setConfigExiste(false);
        setTemChaveSalva(false);
      } else {
        mostrarMensagem("erro", "Não foi possível carregar a configuração da OpenAI.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function salvarConfig(event) {
    event.preventDefault();

    const payload = {
      model_preference: form.model_preference || "gpt-4o-mini",
    };

    if (form.openai_api_key.trim()) {
      payload.openai_api_key = form.openai_api_key.trim();
    }

    if (!configExiste && !payload.openai_api_key) {
      mostrarMensagem("erro", "Cole uma chave da OpenAI para criar a configuração inicial.");
      return;
    }

    try {
      setSaving(true);
      if (configExiste) {
        await api.put("/whatsapp/config", payload);
      } else {
        await api.post("/whatsapp/config", {
          provider: "360dialog",
          ...payload,
        });
      }

      setConfigExiste(true);
      setTemChaveSalva(temChaveSalva || Boolean(payload.openai_api_key));
      setForm((prev) => ({
        ...prev,
        openai_api_key: "",
      }));
      mostrarMensagem("sucesso", "Configuração da OpenAI salva com sucesso.");
    } catch (error) {
      mostrarMensagem(
        "erro",
        error?.response?.data?.detail || "Não foi possível salvar a configuração da OpenAI."
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="rounded-2xl border border-indigo-100 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="rounded-xl bg-indigo-100 p-2 text-indigo-600">
              <FiCpu size={18} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900">OpenAI para Exames Veterinários</h2>
              <p className="mt-1 text-sm text-slate-500">
                Habilita leitura e apoio de IA para hemograma, bioquímica, PDF, raio-x, ultrassom e imagens anexadas.
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <span
            className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium ${
              temChaveSalva ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
            }`}
          >
            {temChaveSalva ? <FiCheckCircle size={13} /> : <FiAlertTriangle size={13} />}
            {temChaveSalva ? "Chave cadastrada" : "Configuração pendente"}
          </span>
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-3 text-sm text-indigo-800">
        <p className="font-medium">O que esta integração libera</p>
        <ul className="mt-2 space-y-1 text-indigo-700">
          <li>- Processar arquivo do exame com IA na consulta e na tela de exames anexados.</li>
          <li>- Interpretar hemograma e exames laboratoriais a partir de PDF ou imagem.</li>
          <li>- Extrair alertas, achados, condutas sugeridas e responder perguntas sobre o exame.</li>
        </ul>
      </div>

      {msg && (
        <div
          className={`mt-4 rounded-xl px-4 py-3 text-sm ${
            msg.tipo === "sucesso"
              ? "border border-emerald-200 bg-emerald-50 text-emerald-700"
              : "border border-red-200 bg-red-50 text-red-700"
          }`}
        >
          {msg.texto}
        </div>
      )}

      <form className="mt-5 space-y-4" onSubmit={salvarConfig}>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Modelo da IA</label>
          <select
            value={form.model_preference}
            onChange={(event) =>
              setForm((prev) => ({
                ...prev,
                model_preference: event.target.value,
              }))
            }
            disabled={loading || saving}
            className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none transition focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100"
          >
            {MODELOS_RECOMENDADOS.map((modelo) => (
              <option key={modelo.value} value={modelo.value}>
                {modelo.label}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-slate-500">Sugestão: comece com `gpt-4o-mini`.</p>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Chave da OpenAI</label>
          <div className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2.5 focus-within:border-indigo-300 focus-within:ring-2 focus-within:ring-indigo-100">
            <FiKey className="shrink-0 text-slate-400" size={16} />
            <input
              type={mostrarChave ? "text" : "password"}
              value={form.openai_api_key}
              onChange={(event) =>
                setForm((prev) => ({
                  ...prev,
                  openai_api_key: event.target.value,
                }))
              }
              disabled={loading || saving}
              placeholder={temChaveSalva ? "Cole uma nova chave apenas se quiser trocar a atual" : "sk-..."}
              className="min-w-0 flex-1 border-0 bg-transparent text-sm outline-none placeholder:text-slate-400"
            />
            <button
              type="button"
              onClick={() => setMostrarChave((atual) => !atual)}
              className="rounded-lg p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-700"
              aria-label={mostrarChave ? "Ocultar chave" : "Mostrar chave"}
            >
              {mostrarChave ? <FiEyeOff size={16} /> : <FiEye size={16} />}
            </button>
          </div>
          <p className="mt-1 text-xs text-slate-500">{ajudaAtual}</p>
        </div>

        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <p className="font-medium">Segurança</p>
          <p className="mt-1">
            Se uma chave foi enviada em conversa, print ou outro local exposto, o ideal é revogar essa chave na OpenAI
            e cadastrar uma nova aqui.
          </p>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={loading || saving}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <FiSave size={16} />
            {saving ? "Salvando..." : "Salvar OpenAI"}
          </button>
        </div>
      </form>
    </section>
  );
}
