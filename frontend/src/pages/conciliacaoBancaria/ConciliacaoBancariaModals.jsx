import { useState } from "react";
import { Settings } from "lucide-react";
import { api } from "../../services/api";
import FornecedorIdentity from "../../components/ui/FornecedorIdentity";

// Componente Modal de Classificação
export function ModalClassificacao({ movimentacao, onClose, onClassificar }) {
  const [tipoVinculo, setTipoVinculo] = useState(movimentacao.tipo_vinculo || "fornecedor");
  const [criarRegra, setCriarRegra] = useState(true);
  const [recorrente, setRecorrente] = useState(false);
  const [periodicidade, setPeriodicidade] = useState("mensal");

  const handleSubmit = (e) => {
    e.preventDefault();
    onClassificar(movimentacao, {
      tipo_vinculo: tipoVinculo,
      criar_regra: criarRegra,
      recorrente,
      periodicidade: recorrente ? periodicidade : null,
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">Classificar Movimentação</h2>
        </div>

        <div className="p-6 space-y-4">
          {/* Dados da movimentação */}
          <div className="p-4 bg-gray-50 rounded-lg space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Data:</span>
              <span className="text-sm font-medium">
                {new Date(movimentacao.data_movimento).toLocaleDateString("pt-BR")}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Valor:</span>
              <span className="text-sm font-medium">
                {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(
                  movimentacao.valor,
                )}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Descrição:</span>
              <span className="text-sm font-medium truncate ml-4">{movimentacao.memo}</span>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Tipo de Vínculo
              </label>
              <select
                value={tipoVinculo}
                onChange={(e) => setTipoVinculo(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value="fornecedor">Pagamento a Fornecedor</option>
                <option value="taxa">Taxa Bancária</option>
                <option value="transferencia">Transferência Entre Contas</option>
                <option value="recebimento">Recebimento de Cliente</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="criar_regra"
                checked={criarRegra}
                onChange={(e) => setCriarRegra(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded"
              />
              <label htmlFor="criar_regra" className="text-sm text-gray-700">
                Criar regra automática para movimentações similares
              </label>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="recorrente"
                checked={recorrente}
                onChange={(e) => setRecorrente(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded"
              />
              <label htmlFor="recorrente" className="text-sm text-gray-700">
                Movimentação recorrente (criar provisões futuras)
              </label>
            </div>

            {recorrente && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Periodicidade
                </label>
                <select
                  value={periodicidade}
                  onChange={(e) => setPeriodicidade(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="mensal">Mensal</option>
                  <option value="anual">Anual</option>
                  <option value="trimestral">Trimestral</option>
                  <option value="semestral">Semestral</option>
                </select>
              </div>
            )}

            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Classificar
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

// Componente Modal de Regras
export function ModalRegras({ regras, onClose, onAtualizar }) {
  const [regrasLocais, setRegrasLocais] = useState(regras);

  const excluirRegra = async (regraId) => {
    if (!confirm("Deseja realmente desativar esta regra?")) return;

    try {
      await api.delete(`/conciliacao/regras/${regraId}`);

      onAtualizar();
      const novasRegras = regrasLocais.filter((r) => r.id !== regraId);
      setRegrasLocais(novasRegras);
    } catch (error) {
      console.error("Erro ao excluir regra:", error);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200 flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Regras de Aprendizado</h2>
            <p className="text-sm text-gray-600 mt-1">Sistema aprende com suas classificações</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>

        <div className="p-6">
          {regrasLocais.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Settings size={48} className="mx-auto mb-4 text-gray-300" />
              <p>Nenhuma regra criada ainda.</p>
              <p className="text-sm mt-2">
                Classifique movimentações para criar regras automáticas.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {regrasLocais.map((regra) => (
                <div
                  key={regra.id}
                  className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="px-3 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded">
                          {regra.padrao_memo}
                        </span>
                        {regra.tipo_operacao && (
                          <span className="text-xs text-gray-600">{regra.tipo_operacao}</span>
                        )}
                      </div>

                      <div className="grid grid-cols-3 gap-4 text-sm">
                        <div>
                          <span className="text-gray-600">Confiança:</span>
                          <div className="flex items-center gap-2 mt-1">
                            <div className="flex-1 bg-gray-200 rounded-full h-2">
                              <div
                                className={`h-2 rounded-full ${
                                  regra.confianca >= 80
                                    ? "bg-green-500"
                                    : regra.confianca >= 50
                                      ? "bg-yellow-500"
                                      : "bg-red-500"
                                }`}
                                style={{ width: `${regra.confianca}%` }}
                              />
                            </div>
                            <span className="font-medium">{regra.confianca}%</span>
                          </div>
                        </div>

                        <div>
                          <span className="text-gray-600">Aplicada:</span>
                          <p className="font-medium mt-1">{regra.vezes_aplicada}x</p>
                        </div>

                        <div>
                          <span className="text-gray-600">Confirmada:</span>
                          <p className="font-medium mt-1">{regra.vezes_confirmada}x</p>
                        </div>
                      </div>

                      {regra.fornecedor_nome && (
                        <p className="text-sm text-gray-600 mt-2">
                          <span className="mr-1">→</span>
                          <FornecedorIdentity
                            fallback=""
                            layout="inline"
                            nameClassName="font-medium text-gray-700"
                            record={regra}
                            showDocument={false}
                          />
                        </p>
                      )}
                    </div>

                    <button
                      onClick={() => excluirRegra(regra.id)}
                      className="ml-4 px-3 py-1 text-xs text-red-600 hover:bg-red-50 rounded"
                    >
                      Desativar
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
