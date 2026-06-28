import { useEffect, useMemo, useState } from "react";
import {
  FiAlertCircle,
  FiCheckCircle,
  FiCircle,
  FiExternalLink,
  FiRefreshCcw,
  FiRotateCcw,
} from "react-icons/fi";
import api from "../api";
import {
  BADGE_LABELS,
  SECOES_ONBOARDING,
  buildGuiaHref,
  flattenOnboardingItems,
} from "./introducaoGuiada/introducaoGuiadaConfig";
import { executarIntroducaoChecks } from "./introducaoGuiada/introducaoGuiadaChecks";

const STORAGE_KEY = "introducao_guiada_v1";

const SECOES = SECOES_ONBOARDING;

function makeStorageKey() {
  try {
    const raw = localStorage.getItem("user");
    if (!raw) return STORAGE_KEY;
    const user = JSON.parse(raw);
    return `${STORAGE_KEY}_${user?.id || "anon"}_${user?.tenant_id || "tenant"}`;
  } catch {
    return STORAGE_KEY;
  }
}

export default function IntroducaoGuiada() {
  const [marcados, setMarcados] = useState({});
  const [autoChecks, setAutoChecks] = useState({});
  const [carregandoChecks, setCarregandoChecks] = useState(false);

  const storageKey = useMemo(() => makeStorageKey(), []);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") {
        setMarcados(parsed);
      }
    } catch {
      // Ignora leitura invalida do localStorage
    }
  }, [storageKey]);

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(marcados));
  }, [marcados, storageKey]);

  const executarChecksAutomaticos = async () => {
    setCarregandoChecks(true);
    const results = await executarIntroducaoChecks(api);
    setAutoChecks(results);
    setCarregandoChecks(false);
  };

  useEffect(() => {
    executarChecksAutomaticos();
  }, []);

  const todosItens = useMemo(() => flattenOnboardingItems(SECOES), []);

  const total = todosItens.length;
  const concluidos = todosItens.filter((item) => {
    const auto = item.autoCheckKey ? autoChecks[item.autoCheckKey] : false;
    return Boolean(auto || marcados[item.id]);
  }).length;

  const percentual = total > 0 ? Math.round((concluidos / total) * 100) : 0;

  const alternarItem = (itemId) => {
    setMarcados((prev) => ({ ...prev, [itemId]: !prev[itemId] }));
  };

  const resetarChecklist = () => {
    setMarcados({});
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm mb-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-5">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Preparando seu sistema</h2>
            <p className="text-sm text-gray-600 mt-1">
              Sequencia guiada para configurar o sistema do jeito certo e evitar falhas no dia a
              dia.
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={executarChecksAutomaticos}
              className="inline-flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <FiRefreshCcw className="w-4 h-4" />
              Atualizar checagem
            </button>
            <button
              onClick={resetarChecklist}
              className="inline-flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <FiRotateCcw className="w-4 h-4" />
              Resetar
            </button>
          </div>
        </div>

        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="text-gray-600">Progresso geral</span>
          <span className="font-semibold text-gray-900">
            {concluidos}/{total} ({percentual}%)
          </span>
        </div>
        <div className="h-3 w-full bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-500 transition-all"
            style={{ width: `${percentual}%` }}
          />
        </div>

        {carregandoChecks && (
          <div className="mt-3 text-xs text-gray-500">Verificando situacao real no sistema...</div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4">
        {SECOES.map((secao) => (
          <section
            key={secao.id}
            className="bg-white border border-gray-200 rounded-2xl p-5 shadow-sm"
          >
            <h3 className="text-lg font-bold text-gray-900 mb-2">{secao.titulo}</h3>
            {secao.resumo && <p className="text-sm text-gray-600 mb-4">{secao.resumo}</p>}

            <div className="space-y-3">
              {secao.itens.map((item) => {
                const autoConcluido = item.autoCheckKey
                  ? Boolean(autoChecks[item.autoCheckKey])
                  : false;
                const concluido = autoConcluido || Boolean(marcados[item.id]);
                const badgeLabel = BADGE_LABELS[item.tipo] || "Recomendado";
                const badgeClass =
                  item.tipo === "obrigatorio"
                    ? "bg-red-100 text-red-700"
                    : item.tipo === "condicional"
                      ? "bg-amber-100 text-amber-700"
                      : "bg-gray-100 text-gray-600";

                return (
                  <div
                    key={item.id}
                    className={`border rounded-xl p-4 ${concluido ? "border-emerald-200 bg-emerald-50/40" : "border-gray-200"}`}
                  >
                    <div className="flex items-start gap-3">
                      <button
                        type="button"
                        onClick={() => alternarItem(item.id)}
                        disabled={autoConcluido}
                        className={`mt-0.5 ${autoConcluido ? "cursor-not-allowed" : "cursor-pointer"}`}
                        aria-label={`Marcar item ${item.titulo}`}
                      >
                        {concluido ? (
                          <FiCheckCircle className="w-5 h-5 text-emerald-600" />
                        ) : (
                          <FiCircle className="w-5 h-5 text-gray-400" />
                        )}
                      </button>

                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-1">
                          <p className="text-sm font-semibold text-gray-900">{item.titulo}</p>
                          <span className={`text-xs px-2 py-0.5 rounded-full ${badgeClass}`}>
                            {badgeLabel}
                          </span>
                          {autoConcluido && (
                            <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700">
                              Confirmado automaticamente
                            </span>
                          )}
                        </div>

                        {item.condicao && (
                          <p className="text-xs text-amber-700 inline-flex items-center gap-1 mb-1">
                            <FiAlertCircle className="w-3 h-3" />
                            {item.condicao}
                          </p>
                        )}

                        <div className="text-xs text-gray-600 space-y-1">
                          <p>
                            <span className="font-medium">Onde fazer:</span>{" "}
                            <a
                              href={buildGuiaHref(item.onde, item.id)}
                              target="_blank"
                              rel="noreferrer"
                              className="text-indigo-700 hover:underline inline-flex items-center gap-1"
                            >
                              {item.onde} <FiExternalLink className="w-3 h-3" />
                            </a>
                          </p>
                          <p>
                            <span className="font-medium">Resultado:</span> {item.resultado}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        ))}
      </div>

      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-2xl p-5">
        <p className="text-sm font-semibold text-blue-900 mb-1">Proxima evolucao (ja planejada)</p>
        <p className="text-sm text-blue-800">
          Pre-configuracao automatica com 1 clique para criar cadastros padrao (formas de pagamento,
          categorias e ajustes iniciais), reduzindo o trabalho manual na implantacao.
        </p>
      </div>
    </div>
  );
}
