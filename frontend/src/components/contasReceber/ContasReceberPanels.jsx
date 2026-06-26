import { X } from "lucide-react";
import { safeArray } from "../../utils/safeArray";
import ActionButton from "../ui/ActionButton";
import CustomerIdentity from "../ui/CustomerIdentity";
import DataTable from "../ui/DataTable";
import FilterBar from "../ui/FilterBar";
import MoneyCell from "../ui/MoneyCell";
import StatusBadge from "../ui/StatusBadge";

export function ContasReceberFilters({
  aplicarFiltros,
  buscaNumeroVenda,
  clientes,
  filtros,
  handleFiltrosSubmit,
  setBuscaNumeroVenda,
  setFiltros,
}) {
  return (
    <>
      {/* Filtros */}
      <FilterBar className="mb-6" onSubmit={handleFiltrosSubmit}>
        <h5 className="text-lg font-semibold mb-4">Filtros</h5>

        {/* Campo de busca por numero de venda */}
        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">Buscar por Numero da Venda</label>
          <input
            type="text"
            placeholder="Digite o numero da venda (ex: 202601100003) e pressione Enter"
            className="w-full border border-gray-300 rounded px-3 py-2"
            value={buscaNumeroVenda}
            onChange={(e) => {
              // Remove # automaticamente
              const valor = e.target.value.replace("#", "");
              setBuscaNumeroVenda(valor);
            }}
            onKeyPress={(e) => {
              if (e.key === "Enter") {
                aplicarFiltros();
              }
            }}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Status</label>
            <select
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.status}
              onChange={(e) => setFiltros({ ...filtros, status: e.target.value })}
            >
              <option value="todos">Todos</option>
              <option value="pendente">Pendente</option>
              <option value="parcial">Parcial</option>
              <option value="recebido">Recebido</option>
              <option value="vencido">Vencido</option>
            </select>
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-1">Cliente</label>
            <select
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.cliente_id || ""}
              onChange={(e) => setFiltros({ ...filtros, cliente_id: e.target.value || null })}
            >
              <option value="">Todos</option>
              {safeArray(clientes).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nome}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Data Inicio</label>
            <input
              type="date"
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.data_inicio}
              onChange={(e) => setFiltros({ ...filtros, data_inicio: e.target.value })}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Data Fim</label>
            <input
              type="date"
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.data_fim}
              onChange={(e) => setFiltros({ ...filtros, data_fim: e.target.value })}
            />
          </div>

          <div className="flex items-end gap-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                className="w-4 h-4"
                checked={filtros.apenas_vencidas}
                onChange={(e) =>
                  setFiltros({
                    ...filtros,
                    apenas_vencidas: e.target.checked,
                    apenas_vencer: false,
                  })
                }
              />
              <span className="text-sm">So Vencidas</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                className="w-4 h-4"
                checked={filtros.apenas_vencer}
                onChange={(e) =>
                  setFiltros({
                    ...filtros,
                    apenas_vencer: e.target.checked,
                    apenas_vencidas: false,
                  })
                }
              />
              <span className="text-sm">A Vencer</span>
            </label>
            <ActionButton intent="neutral" tone="solid" size="sm" onClick={aplicarFiltros}>
              Filtrar
            </ActionButton>
          </div>
        </div>
      </FilterBar>
    </>
  );
}

export function ContasReceberRecebimentoModal({
  contaSelecionada,
  contasBancarias,
  dadosRecebimento,
  formasPagamento,
  formatarMoeda,
  mostrarModalRecebimento,
  registrarRecebimento,
  setDadosRecebimento,
  setMostrarModalRecebimento,
}) {
  return (
    <>
      {/* Modal de Recebimento */}
      {mostrarModalRecebimento && contaSelecionada && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4">
            <div className="flex justify-between items-center border-b p-4">
              <h5 className="text-xl font-bold">Registrar Recebimento</h5>
              <ActionButton
                intent="neutral"
                tone="ghost"
                size="sm"
                icon={X}
                aria-label="Fechar recebimento"
                onClick={() => setMostrarModalRecebimento(false)}
              />
            </div>

            <div className="p-6">
              <div className="bg-blue-50 border border-blue-200 rounded p-3 mb-4 text-sm">
                <strong>Conta:</strong> {contaSelecionada.descricao}
                <br />
                <strong>Valor Total:</strong> {formatarMoeda(contaSelecionada.valor_final)}
                <br />
                <strong>Ja Recebido:</strong> {formatarMoeda(contaSelecionada.valor_recebido)}
                <br />
                <strong>Saldo Restante:</strong>{" "}
                {formatarMoeda(contaSelecionada.valor_final - contaSelecionada.valor_recebido)}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Valor a Receber *</label>
                  <input
                    type="number"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    step="0.01"
                    value={dadosRecebimento.valor_recebido}
                    onChange={(e) =>
                      setDadosRecebimento({
                        ...dadosRecebimento,
                        valor_recebido: parseFloat(e.target.value),
                      })
                    }
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Data do Recebimento *</label>
                  <input
                    type="date"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    value={dadosRecebimento.data_recebimento}
                    onChange={(e) =>
                      setDadosRecebimento({ ...dadosRecebimento, data_recebimento: e.target.value })
                    }
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Forma de Pagamento</label>
                  <select
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    value={dadosRecebimento.forma_pagamento_id || ""}
                    onChange={(e) =>
                      setDadosRecebimento({
                        ...dadosRecebimento,
                        forma_pagamento_id: parseInt(e.target.value) || null,
                      })
                    }
                  >
                    <option value="">Selecione...</option>
                    {safeArray(formasPagamento).map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.nome}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Conta Bancaria *</label>
                  <select
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    value={dadosRecebimento.conta_bancaria_id || ""}
                    onChange={(e) =>
                      setDadosRecebimento({
                        ...dadosRecebimento,
                        conta_bancaria_id: parseInt(e.target.value) || null,
                      })
                    }
                  >
                    <option value="">Selecione a conta...</option>
                    {safeArray(contasBancarias).map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.nome} - {formatarMoeda(c.saldo_atual || 0)}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Juros</label>
                  <input
                    type="number"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    step="0.01"
                    value={dadosRecebimento.valor_juros}
                    onChange={(e) =>
                      setDadosRecebimento({
                        ...dadosRecebimento,
                        valor_juros: parseFloat(e.target.value) || 0,
                      })
                    }
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Multa</label>
                  <input
                    type="number"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    step="0.01"
                    value={dadosRecebimento.valor_multa}
                    onChange={(e) =>
                      setDadosRecebimento({
                        ...dadosRecebimento,
                        valor_multa: parseFloat(e.target.value) || 0,
                      })
                    }
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Desconto</label>
                  <input
                    type="number"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    step="0.01"
                    value={dadosRecebimento.valor_desconto}
                    onChange={(e) =>
                      setDadosRecebimento({
                        ...dadosRecebimento,
                        valor_desconto: parseFloat(e.target.value) || 0,
                      })
                    }
                  />
                </div>

                <div className="col-span-2">
                  <label className="block text-sm font-medium mb-1">Observacoes</label>
                  <textarea
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    rows="3"
                    value={dadosRecebimento.observacoes}
                    onChange={(e) =>
                      setDadosRecebimento({ ...dadosRecebimento, observacoes: e.target.value })
                    }
                  />
                </div>
              </div>

              <div className="bg-green-50 border border-green-200 rounded p-3 mt-4">
                <strong>Valor Final do Recebimento:</strong>{" "}
                {formatarMoeda(
                  (dadosRecebimento.valor_recebido || 0) +
                    (dadosRecebimento.valor_juros || 0) +
                    (dadosRecebimento.valor_multa || 0) -
                    (dadosRecebimento.valor_desconto || 0),
                )}
              </div>
            </div>

            <div className="flex justify-end gap-3 border-t p-4">
              <ActionButton
                intent="neutral"
                tone="soft"
                size="md"
                onClick={() => setMostrarModalRecebimento(false)}
              >
                Cancelar
              </ActionButton>
              <ActionButton intent="create" size="md" onClick={registrarRecebimento}>
                Confirmar Recebimento
              </ActionButton>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export function ContasReceberDetalhesModal({
  abrirFluxoDeCaixa,
  abrirVenda,
  contaSelecionada,
  detalhesCompletos,
  formatarData,
  formatarMoeda,
  mostrarDetalhes,
  setMostrarDetalhes,
}) {
  return (
    <>
      {/* Modal Detalhes */}
      {mostrarDetalhes && contaSelecionada && detalhesCompletos && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="bg-blue-600 text-white px-6 py-4 flex justify-between items-center sticky top-0">
              <h3 className="text-xl font-semibold">Detalhes da Conta</h3>
              <ActionButton
                onClick={() => setMostrarDetalhes(false)}
                intent="neutral"
                tone="ghost"
                size="sm"
                icon={X}
                className="text-white hover:bg-blue-700"
                aria-label="Fechar detalhes"
              />
            </div>

            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Numero da Conta</label>
                  <p className="mt-1 text-lg">{contaSelecionada.numero_documento || "N/A"}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Cliente</label>
                  <p className="mt-1 text-lg">
                    <CustomerIdentity
                      code={
                        detalhesCompletos.cliente?.codigo ||
                        detalhesCompletos.cliente_id ||
                        detalhesCompletos.cliente?.id
                      }
                      customer={detalhesCompletos.cliente}
                      fallback="N/A"
                    />
                  </p>
                </div>
              </div>

              {/* Numero do Pedido - Clicavel */}
              {detalhesCompletos.venda && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Pedido/Venda
                  </label>
                  <div className="flex gap-2">
                    <ActionButton
                      onClick={() => abrirVenda(detalhesCompletos.venda.id)}
                      intent="edit"
                      tone="soft"
                      size="md"
                      className="flex-1"
                    >
                      <span className="text-xl">Venda</span>
                      <span className="font-semibold">{detalhesCompletos.venda.numero_venda}</span>
                    </ActionButton>
                    <ActionButton
                      onClick={() => abrirFluxoDeCaixa(contaSelecionada)}
                      intent="create"
                      tone="soft"
                      size="md"
                      title="Ver no Fluxo de Caixa"
                    >
                      <span className="text-xl">Fluxo</span>
                      <span className="text-sm">Fluxo</span>
                    </ActionButton>
                  </div>
                </div>
              )}

              {!detalhesCompletos.venda && (
                <div>
                  <ActionButton
                    onClick={() => abrirFluxoDeCaixa(contaSelecionada)}
                    intent="create"
                    tone="soft"
                    size="md"
                    className="w-full"
                  >
                    <span className="text-xl">Fluxo</span>
                    <span className="font-medium">Ver no Fluxo de Caixa</span>
                  </ActionButton>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Data de Emissao</label>
                  <p className="mt-1">{formatarData(detalhesCompletos.datas.emissao)}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Data de Vencimento
                  </label>
                  <p className="mt-1">{formatarData(detalhesCompletos.datas.vencimento)}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Valor Original</label>
                  <p className="mt-1 text-lg font-semibold text-blue-600">
                    {formatarMoeda(detalhesCompletos.valores.final)}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Valor Recebido</label>
                  <p className="mt-1 text-lg font-semibold text-green-600">
                    {formatarMoeda(detalhesCompletos.valores.recebido)}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Saldo Restante</label>
                  <p className="mt-1 text-lg font-semibold text-red-600">
                    {formatarMoeda(detalhesCompletos.valores.saldo)}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Status</label>
                  <p className="mt-1">
                    <StatusBadge status={detalhesCompletos.status} />
                  </p>
                </div>
              </div>

              {/* Recebimentos com Conta Bancaria */}
              {detalhesCompletos.recebimentos && detalhesCompletos.recebimentos.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Historico de Recebimentos
                  </label>
                  <div className="border border-gray-200 rounded-lg overflow-hidden">
                    <DataTable
                      columns={[
                        {
                          key: "data",
                          header: "Data",
                          render: (recebimento) => formatarData(recebimento.data),
                        },
                        {
                          key: "valor",
                          header: "Valor",
                          align: "right",
                          className: "font-semibold text-green-600",
                          render: (recebimento) => (
                            <MoneyCell value={recebimento.valor} zeroAsDash />
                          ),
                        },
                        {
                          key: "conta",
                          header: "Conta Bancaria",
                          render: (recebimento) =>
                            recebimento.conta_bancaria_nome ? (
                              <span className="rounded bg-blue-50 px-2 py-1 text-xs text-blue-700">
                                {recebimento.conta_bancaria_nome}
                              </span>
                            ) : (
                              <span className="text-xs text-gray-400">Nao informada</span>
                            ),
                        },
                      ]}
                      data={safeArray(detalhesCompletos?.recebimentos)}
                      getRowKey={(recebimento, index) => recebimento.id || index}
                      tableClassName="w-full"
                      theadClassName="bg-gray-50"
                      tbodyClassName="divide-y divide-gray-200"
                    />
                  </div>
                </div>
              )}

              {detalhesCompletos.observacoes && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">Observacoes</label>
                  <p className="mt-1 text-gray-600">{detalhesCompletos.observacoes}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
