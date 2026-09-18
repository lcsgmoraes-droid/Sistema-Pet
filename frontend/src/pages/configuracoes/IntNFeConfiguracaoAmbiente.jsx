import { useCallback, useState } from "react";
import { FiAlertTriangle, FiCheckCircle } from "react-icons/fi";
import IntNFeAmbienteEmissao from "./IntNFeAmbienteEmissao.jsx";
import IntNFeCsc from "./IntNFeCsc.jsx";
import IntNFeNumeracao from "./IntNFeNumeracao.jsx";

const initialChoices = {
  1: {},
  2: {},
};

export default function IntNFeConfiguracaoAmbiente({
  apiClient,
  disabled,
  onNumberingBusy,
  onCscBusy,
  onEnvironmentBusy,
  onNumberingData,
  onCscData,
  onEnvironmentData,
}) {
  const [environment, setEnvironment] = useState(2);
  const [choices, setChoices] = useState(initialChoices);
  const [numberingData, setNumberingData] = useState(null);
  const [environmentData, setEnvironmentData] = useState(null);

  const chooseSequence = useCallback(
    ({ modelo, serie, proximoNumero, pendente = false }) => {
      setChoices((current) => ({
        ...current,
        [environment]: {
          ...current[environment],
          [modelo]: { serie, proximoNumero, pendente, origem: "sequencia" },
        },
      }));
    },
    [environment],
  );

  const clearSequence = useCallback(
    ({ modelo }) => {
      setChoices((current) => {
        return {
          ...current,
          [environment]: {
            ...current[environment],
            [modelo]: {
              serie: "",
              proximoNumero: null,
              pendente: false,
              origem: "sequencia",
            },
          },
        };
      });
    },
    [environment],
  );

  const updateNumberingData = useCallback(
    (data) => {
      setNumberingData(data);
      onNumberingData?.(data);
    },
    [onNumberingData],
  );

  const updateEnvironmentData = useCallback(
    (data) => {
      setEnvironmentData(data);
      onEnvironmentData?.(data);
    },
    [onEnvironmentData],
  );

  return (
    <section className="space-y-5 rounded-3xl border border-slate-200 bg-slate-50 p-4 sm:p-6 dark:border-slate-700 dark:bg-slate-950/40">
      <header className="space-y-4">
        <div>
          <h2 className="text-xl font-bold text-slate-950 dark:text-white">
            Configuração por ambiente
          </h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            Escolha um ambiente uma vez. Todos os dados abaixo pertencerão ao ambiente selecionado.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2" role="tablist" aria-label="Ambiente fiscal">
          {[
            { code: 2, title: "Homologação", detail: "Testes sem valor fiscal" },
            { code: 1, title: "Produção", detail: "Emissão de documentos reais" },
          ].map((item) => {
            const selected = environment === item.code;
            return (
              <button
                key={item.code}
                type="button"
                role="tab"
                aria-selected={selected}
                disabled={disabled}
                onClick={() => setEnvironment(item.code)}
                className={`rounded-2xl border p-4 text-left transition ${
                  selected
                    ? item.code === 1
                      ? "border-amber-500 bg-amber-50 text-amber-950 ring-2 ring-amber-200"
                      : "border-blue-500 bg-blue-50 text-blue-950 ring-2 ring-blue-200"
                    : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                }`}
              >
                <span className="flex items-center gap-2 font-bold">
                  {selected ? <FiCheckCircle aria-hidden="true" /> : null}
                  {item.title}
                </span>
                <span className="mt-1 block text-sm opacity-80">{item.detail}</span>
              </button>
            );
          })}
        </div>

        <div
          className={`flex gap-3 rounded-xl border p-4 text-sm ${
            environment === 1
              ? "border-amber-300 bg-amber-50 text-amber-950"
              : "border-blue-200 bg-blue-50 text-blue-950"
          }`}
        >
          {environment === 1 ? <FiAlertTriangle className="mt-0.5 shrink-0" /> : null}
          <p>
            {environment === 1
              ? "Você está configurando a produção. As sequências e séries escolhidas aqui serão usadas em notas com valor fiscal."
              : "Você está configurando a homologação. Use esta área para validar o fluxo antes da emissão real."}
          </p>
        </div>
      </header>

      <IntNFeNumeracao
        apiClient={apiClient}
        disabled={disabled}
        environment={environment}
        onBusy={onNumberingBusy}
        onData={updateNumberingData}
        onUseSequence={chooseSequence}
        onClearSequence={clearSequence}
        savedConfigurations={environmentData?.configuracoes || []}
        onEnvironmentData={updateEnvironmentData}
      />

      <IntNFeCsc
        apiClient={apiClient}
        disabled={disabled}
        environment={environment}
        onBusy={onCscBusy}
        onData={onCscData}
      />

      <IntNFeAmbienteEmissao
        apiClient={apiClient}
        disabled={disabled}
        environment={environment}
        choices={choices[environment]}
        numberingData={numberingData}
        configurationData={environmentData}
        onBusy={onEnvironmentBusy}
        onData={updateEnvironmentData}
      />
    </section>
  );
}
