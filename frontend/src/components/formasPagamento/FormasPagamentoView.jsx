import { ArrowLeftRight, Banknote, CreditCard, QrCode, Receipt } from "lucide-react";
import CurrencyInput from "../CurrencyInput";
import { formatMoneyBRL } from "../../utils/formatters";

const ehTipoCartao = (tipo) => ["cartao_credito", "cartao_debito"].includes(tipo);

const getIconeFormaPagamento = (icone, tipo) => {
  const key = (icone || tipo || "").toLowerCase();
  if (key.includes("pix")) return <QrCode className="w-5 h-5" />;
  if (key.includes("dinheiro") || key.includes("cash")) return <Banknote className="w-5 h-5" />;
  if (key.includes("transfer") || key.includes("banc"))
    return <ArrowLeftRight className="w-5 h-5" />;
  if (key.includes("boleto")) return <Receipt className="w-5 h-5" />;
  if (key.includes("debito") || key.includes("débito") || key.includes("cartao_debito"))
    return <CreditCard className="w-5 h-5" />;
  if (
    key.includes("credito") ||
    key.includes("crédito") ||
    key.includes("cartao_credito") ||
    key.includes("parcelado")
  )
    return <CreditCard className="w-5 h-5" />;
  return <CreditCard className="w-5 h-5" />;
};

export default function FormasPagamentoView({
  abrirModal,
  contasBancarias,
  destacarFormasPagamento,
  editando,
  excluir,
  financeiroErpAtivo,
  formData,
  formas,
  guiaClasses,
  loading,
  mostrarModal,
  operadoras,
  salvar,
  setFormData,
  setMostrarModal,
  tiposDisponiveis,
}) {
  if (loading) {
    return <div className="flex justify-center items-center h-64">Carregando...</div>;
  }

  const editandoCartao = ehTipoCartao(formData.tipo);

  return (
    <div className="p-6">
      {destacarFormasPagamento && (
        <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-amber-900">
          Etapa da introducao guiada: clique em <strong>+ Nova Forma</strong> e cadastre os meios de
          pagamento usados no PDV.
        </div>
      )}

      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Formas de Pagamento/Recebimento</h2>
        <button
          className={`${
            destacarFormasPagamento
              ? `bg-amber-600 hover:bg-amber-700 ${guiaClasses.action}`
              : "bg-blue-600 hover:bg-blue-700"
          } text-white px-4 py-2 rounded`}
          onClick={() => abrirModal()}
        >
          + Nova Forma
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Nome
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Tipo
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Taxa %
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Taxa Fixa
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Prazo
              </th>
              {financeiroErpAtivo && (
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Conta Destino
                </th>
              )}
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Acoes
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {formas.length === 0 ? (
              <tr>
                <td
                  colSpan={financeiroErpAtivo ? 8 : 7}
                  className="px-6 py-4 text-center text-gray-500"
                >
                  Nenhuma forma de pagamento cadastrada
                </td>
              </tr>
            ) : (
              formas.map((forma) => (
                <tr key={forma.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <span className="text-gray-500">
                        {getIconeFormaPagamento(forma.icone, forma.tipo)}
                      </span>
                      <div>
                        <div className="font-medium">{forma.nome}</div>
                        {forma.operadora_id && (
                          <div className="text-xs text-gray-500">
                            {operadoras.find((op) => op.id === forma.operadora_id)?.nome ||
                              forma.operadora ||
                              "Operadora nao encontrada"}
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {tiposDisponiveis.find((t) => t.value === forma.tipo)?.label || forma.tipo}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {ehTipoCartao(forma.tipo) ? "Por operadora" : `${forma.taxa_percentual}%`}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {ehTipoCartao(forma.tipo)
                      ? "Por operadora"
                      : formatMoneyBRL(forma.taxa_fixa || 0)}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {ehTipoCartao(forma.tipo) ? "Por regra" : `${forma.prazo_dias} dias`}
                  </td>
                  {financeiroErpAtivo && (
                    <td className="px-6 py-4 text-sm">
                      {forma.conta_bancaria_destino_id ? (
                        contasBancarias.find((c) => c.id === forma.conta_bancaria_destino_id)
                          ?.nome || "N/A"
                      ) : (
                        <span className="text-gray-400">Nenhuma</span>
                      )}
                    </td>
                  )}
                  <td className="px-6 py-4">
                    <span
                      className={`px-2 py-1 rounded text-xs ${
                        forma.ativo ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-800"
                      }`}
                    >
                      {forma.ativo ? "Ativo" : "Inativo"}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex gap-2">
                      <button
                        className="text-blue-600 hover:text-blue-800"
                        onClick={() => abrirModal(forma)}
                      >
                        Editar
                      </button>
                      <button
                        className="text-red-600 hover:text-red-800"
                        onClick={() => excluir(forma.id)}
                      >
                        Excluir
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Modal */}
      {mostrarModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <div className="bg-blue-600 text-white px-6 py-4 flex justify-between items-center sticky top-0">
              <h3 className="text-xl font-semibold">
                {editando ? "Editar" : "Nova"} Forma de Pagamento
              </h3>
              <button
                onClick={() => setMostrarModal(false)}
                className="text-white hover:bg-blue-700 px-3 py-1 rounded"
              >
                Fechar
              </button>
            </div>

            <div className="p-6">
              <div className="grid grid-cols-2 gap-4">
                {/* Nome */}
                <div className="col-span-2">
                  <label className="block text-sm font-medium mb-1">Nome *</label>
                  <input
                    type="text"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    value={formData.nome}
                    onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                    placeholder="Ex: Dinheiro, PIX, Stone Credito..."
                  />
                </div>

                {/* Tipo */}
                <div>
                  <label className="block text-sm font-medium mb-1">Tipo *</label>
                  <select
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    value={formData.tipo}
                    onChange={(e) => setFormData({ ...formData, tipo: e.target.value })}
                  >
                    {tiposDisponiveis.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.icone} {t.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Icone */}
                <div>
                  <label className="block text-sm font-medium mb-1">Icone</label>
                  <input
                    type="text"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    value={formData.icone}
                    onChange={(e) => setFormData({ ...formData, icone: e.target.value })}
                    placeholder="\uD83D\uDCB5"
                    maxLength={2}
                  />
                </div>

                {!editandoCartao && (
                  <>
                    <div>
                      <label className="block text-sm font-medium mb-1">Taxa % (Ex: 2.5%)</label>
                      <input
                        type="number"
                        className="w-full border border-gray-300 rounded px-3 py-2"
                        step="0.01"
                        value={formData.taxa_percentual}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            taxa_percentual: parseFloat(e.target.value) || 0,
                          })
                        }
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-1">Taxa Fixa (R$)</label>
                      <CurrencyInput
                        className="w-full border border-gray-300 rounded px-3 py-2"
                        value={formData.taxa_fixa}
                        onChange={(value) => setFormData({ ...formData, taxa_fixa: value })}
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-1">Prazo (dias)</label>
                      <input
                        type="number"
                        className="w-full border border-gray-300 rounded px-3 py-2"
                        value={formData.prazo_dias}
                        onChange={(e) =>
                          setFormData({ ...formData, prazo_dias: parseInt(e.target.value) || 0 })
                        }
                      />
                    </div>
                  </>
                )}

                {financeiroErpAtivo && (
                  <div className="col-span-2">
                    <label className="block text-sm font-medium mb-1">Conta Bancaria Destino</label>
                    <select
                      className="w-full border border-gray-300 rounded px-3 py-2"
                      value={formData.conta_bancaria_destino_id || ""}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          conta_bancaria_destino_id: parseInt(e.target.value) || null,
                        })
                      }
                    >
                      <option value="">Selecione...</option>
                      {contasBancarias.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.nome}
                        </option>
                      ))}
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      Esta conta sera usada automaticamente quando esta forma for selecionada em
                      pagamentos/recebimentos
                    </p>
                  </div>
                )}

                {/* Operadora (para cartoes) */}
                {editandoCartao && (
                  <div className="col-span-2 rounded border border-blue-200 bg-blue-50 p-4 text-sm text-blue-800">
                    Operadora, bandeira, taxa e prazo de recebimento sao configurados em{" "}
                    <a href="/cadastros/financeiro/operadoras" className="font-semibold underline">
                      Operadoras de Cartao
                    </a>
                    . Esta forma define apenas se o pagamento e credito ou debito.
                  </div>
                )}

                {/* Checkboxes */}
                <div className="col-span-2 space-y-2">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.ativo}
                      onChange={(e) => setFormData({ ...formData, ativo: e.target.checked })}
                    />
                    <span className="text-sm">Ativo</span>
                  </label>

                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.gera_contas_receber}
                      onChange={(e) =>
                        setFormData({ ...formData, gera_contas_receber: e.target.checked })
                      }
                    />
                    <span className="text-sm">Gera Contas a Receber (para cartoes com prazo)</span>
                  </label>

                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.requer_nsu}
                      onChange={(e) => setFormData({ ...formData, requer_nsu: e.target.checked })}
                    />
                    <span className="text-sm">Requer NSU (numero de transacao)</span>
                  </label>

                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.permite_parcelamento}
                      onChange={(e) =>
                        setFormData({ ...formData, permite_parcelamento: e.target.checked })
                      }
                    />
                    <span className="text-sm">Permite Parcelamento</span>
                  </label>

                  {formData.permite_parcelamento && (
                    <div className="ml-6 space-y-3">
                      <div>
                        <label className="block text-sm font-medium mb-1">Maximo de Parcelas</label>
                        <input
                          type="number"
                          className="w-full border border-gray-300 rounded px-3 py-2"
                          min="1"
                          max={24}
                          value={formData.parcelas_maximas}
                          onChange={(e) => {
                            const valor = parseInt(e.target.value) || 1;
                            setFormData({ ...formData, parcelas_maximas: valor });
                          }}
                        />
                      </div>

                      {/* Configuracao de taxas por parcela */}
                      {!editandoCartao && (
                        <div className="bg-blue-50 border border-blue-200 rounded p-3">
                          <h4 className="text-sm font-semibold text-blue-900 mb-2">
                            Taxas Especificas por Numero de Parcelas
                          </h4>
                          <p className="text-xs text-blue-700 mb-3">
                            Configure taxas diferentes para cada quantidade de parcelas. Se nao
                            informado, usa a taxa base ({formData.taxa_percentual}%).
                          </p>

                          <div className="grid grid-cols-3 gap-2 max-h-48 overflow-y-auto">
                            {Array.from({ length: formData.parcelas_maximas }, (_, i) => i + 1).map(
                              (numParcelas) => (
                                <div key={numParcelas} className="flex items-center gap-2">
                                  <label className="text-xs font-medium text-gray-700 w-10">
                                    {numParcelas}x:
                                  </label>
                                  <input
                                    type="number"
                                    step="0.01"
                                    className="flex-1 border border-gray-300 rounded px-2 py-1 text-sm"
                                    placeholder={formData.taxa_percentual}
                                    value={formData.taxas_por_parcela[numParcelas] || ""}
                                    onChange={(e) => {
                                      const novasTaxas = { ...formData.taxas_por_parcela };
                                      if (e.target.value) {
                                        novasTaxas[numParcelas] = parseFloat(e.target.value);
                                      } else {
                                        delete novasTaxas[numParcelas];
                                      }
                                      setFormData({ ...formData, taxas_por_parcela: novasTaxas });
                                    }}
                                  />
                                  <span className="text-xs text-gray-500">%</span>
                                </div>
                              ),
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {!editandoCartao && (
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={formData.permite_antecipacao}
                        onChange={(e) =>
                          setFormData({ ...formData, permite_antecipacao: e.target.checked })
                        }
                      />
                      <span className="text-sm">Permite Antecipacao de Recebiveis</span>
                    </label>
                  )}

                  {!editandoCartao && formData.permite_antecipacao && (
                    <div className="ml-6 space-y-3">
                      <div>
                        <label className="block text-sm font-medium mb-1">
                          Dias para Recebimento Antecipado
                        </label>
                        <input
                          type="number"
                          className="w-full border border-gray-300 rounded px-3 py-2"
                          min="0"
                          max="30"
                          value={
                            formData.dias_recebimento_antecipado != null
                              ? formData.dias_recebimento_antecipado
                              : ""
                          }
                          onChange={(e) => {
                            const val = e.target.value;
                            setFormData({
                              ...formData,
                              dias_recebimento_antecipado: val === "" ? null : parseInt(val),
                            });
                          }}
                          placeholder="Ex: 0 (D+0) ou 1 (D+1)"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          Quantos dias apos a venda o dinheiro cai na conta com antecipacao. Use 0
                          para D+0 (cai na hora), 1 para D+1, etc.
                        </p>
                      </div>

                      <div>
                        <label className="block text-sm font-medium mb-1">
                          Taxa de Antecipacao (%) - OPCIONAL
                        </label>
                        <input
                          type="number"
                          step="0.01"
                          className="w-full border border-gray-300 rounded px-3 py-2"
                          value={formData.taxa_antecipacao_percentual || ""}
                          onChange={(e) =>
                            setFormData({
                              ...formData,
                              taxa_antecipacao_percentual: parseFloat(e.target.value) || null,
                            })
                          }
                          placeholder="Ex: 0.50"
                        />
                        <div className="mt-2 p-3 bg-amber-50 border border-amber-200 rounded">
                          <p className="text-xs text-amber-800 font-semibold mb-1">
                            Duas formas de configurar:
                          </p>
                          <p className="text-xs text-amber-700 mb-1">
                            <strong>1. Com taxa de antecipacao:</strong> Preencha este campo e a
                            taxa sera somada automaticamente as taxas por parcela configuradas acima
                          </p>
                          <p className="text-xs text-amber-700">
                            <strong>2. Sem taxa de antecipacao:</strong> Deixe vazio e configure nos
                            campos 1x a 12x acima ja com o valor final (taxa normal + antecipacao
                            somadas)
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3 border-t p-4">
              <button
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
                onClick={() => setMostrarModal(false)}
              >
                Cancelar
              </button>
              <button
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                onClick={salvar}
              >
                Salvar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
