import { Repeat } from "lucide-react";

export default function ContaPagarRecorrenciaSection({ controller }) {
  const { dados, isEditando, pertenceRecorrencia, setDados } = controller;

  return (
    <section className="space-y-4 border-t pt-4">
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="eh_recorrente"
          checked={dados.eh_recorrente}
          onChange={(event) => setDados({ ...dados, eh_recorrente: event.target.checked })}
          className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
        />
        <label
          htmlFor="eh_recorrente"
          className="text-lg font-semibold text-gray-700 flex items-center gap-2 cursor-pointer"
        >
          <Repeat size={20} className="text-purple-600" />
          Despesa Recorrente
        </label>
      </div>

      {dados.eh_recorrente && (
        <div className="ml-6 space-y-4 p-4 bg-purple-50 rounded-lg">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tipo de Recorrência *
              </label>
              <select
                value={dados.tipo_recorrencia}
                onChange={(event) => setDados({ ...dados, tipo_recorrencia: event.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500"
              >
                <option value="semanal">📅 Semanal (7 em 7 dias)</option>
                <option value="quinzenal">📆 Quinzenal (15 em 15 dias)</option>
                <option value="mensal">🗓️ Mensal</option>
                <option value="personalizado">⚙️ Personalizado</option>
              </select>
            </div>

            {dados.tipo_recorrencia === "personalizado" && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Intervalo (em dias) *
                </label>
                <input
                  type="number"
                  min="1"
                  value={dados.intervalo_dias || ""}
                  onChange={(event) => setDados({ ...dados, intervalo_dias: event.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500"
                  placeholder="Ex: 10, 20, 45..."
                  required
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Número de Repetições
              </label>
              <input
                type="number"
                min="1"
                value={dados.numero_repeticoes || ""}
                onChange={(event) => setDados({ ...dados, numero_repeticoes: event.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500"
                placeholder="Ex: 12 (deixe vazio para infinito)"
              />
              <p className="text-xs text-gray-500 mt-1">Quantas vezes deve se repetir (opcional)</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Data de Término (alternativa)
              </label>
              <input
                type="date"
                value={dados.data_fim_recorrencia || ""}
                onChange={(event) =>
                  setDados({ ...dados, data_fim_recorrencia: event.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500"
              />
              <p className="text-xs text-gray-500 mt-1">Até quando deve repetir (opcional)</p>
            </div>
          </div>

          <div className="bg-blue-100 border border-blue-300 rounded-lg p-3">
            <p className="text-sm text-blue-800">
              <strong>💡 Como funciona:</strong> Esta conta será criada agora e o sistema irá gerar
              automaticamente novas contas nos próximos períodos conforme a recorrência configurada.
              {isEditando &&
                " Na edicao, a janela futura sera ajustada sem alterar pagamentos ja registrados."}
            </p>
          </div>

          {isEditando && <RecorrenciaFuturaCheckbox dados={dados} setDados={setDados} />}
        </div>
      )}

      {isEditando && pertenceRecorrencia && !dados.eh_recorrente && (
        <div className="ml-6">
          <RecorrenciaFuturaCheckbox dados={dados} setDados={setDados} />
        </div>
      )}
    </section>
  );
}

function RecorrenciaFuturaCheckbox({ dados, setDados }) {
  return (
    <label className="flex items-start gap-3 rounded-lg border border-purple-200 bg-purple-50 p-3">
      <input
        type="checkbox"
        checked={Boolean(dados.aplicar_recorrencia_futura)}
        onChange={(event) =>
          setDados({ ...dados, aplicar_recorrencia_futura: event.target.checked })
        }
        className="mt-1 h-4 w-4 rounded text-purple-600 focus:ring-purple-500"
      />
      <span>
        <span className="block text-sm font-semibold text-purple-900">
          Aplicar alterações aos próximos lançamentos desta recorrência
        </span>
        <span className="mt-1 block text-xs text-purple-700">
          Replica valor, fornecedor, categoria, DRE, tipo, canal, documento e observações para
          lançamentos futuros sem pagamento. As datas já geradas permanecem preservadas.
        </span>
      </span>
    </label>
  );
}
