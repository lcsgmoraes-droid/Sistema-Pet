import { Plus } from "lucide-react";

export default function PDVEntregaCard({
  cliente,
  entregadorSelecionado,
  entregadores,
  modoVisualizacao,
  onAbrirModalEndereco,
  onEnderecoEntregaChange,
  onObservacoesEntregaChange,
  onSelecionarEndereco,
  onSelecionarEntregador,
  onTaxaEntregaTotalChange,
  onTaxaEntregadorChange,
  onTaxaLojaChange,
  onToggleTemEntrega,
  vendaAtual,
}) {
  return (
    <div className="bg-white rounded-lg shadow-sm border p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Entrega</h2>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={vendaAtual.tem_entrega}
            onChange={(e) => onToggleTemEntrega(e.target.checked)}
            disabled={modoVisualizacao}
            className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed"
          />
          <span className="text-sm font-medium text-gray-700">
            Tem entrega?
          </span>
        </label>
      </div>

      {vendaAtual.tem_entrega && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Endereço Completo *
            </label>

            {cliente && (
              <div className="mb-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-medium text-blue-900">
                    Endereços cadastrados:
                  </p>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      onAbrirModalEndereco();
                    }}
                    disabled={modoVisualizacao}
                    className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Plus size={14} />
                    Adicionar Endereço
                  </button>
                </div>
                <div className="space-y-2">
                  {(cliente.endereco || cliente.cidade) && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        onSelecionarEndereco(
                          `${cliente.endereco}${cliente.numero ? ", " + cliente.numero : ""}${cliente.complemento ? " - " + cliente.complemento : ""}, ${cliente.bairro}, ${cliente.cidade}/${cliente.estado}`,
                        );
                      }}
                      disabled={modoVisualizacao}
                      className="w-full text-left px-3 py-2 bg-white hover:bg-blue-100 border border-blue-300 rounded text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <span className="font-medium text-blue-700">
                        🏠 Cadastro Principal:
                      </span>{" "}
                      <span className="text-gray-700">
                        {cliente.endereco}, {cliente.numero} - {cliente.bairro}
                      </span>
                    </button>
                  )}

                  {cliente.enderecos_adicionais &&
                    cliente.enderecos_adicionais.map((end, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          onSelecionarEndereco(
                            `${end.endereco}, ${end.numero}${end.complemento ? " - " + end.complemento : ""}, ${end.bairro}, ${end.cidade}/${end.estado}`,
                          );
                        }}
                        disabled={modoVisualizacao}
                        className="w-full text-left px-3 py-2 bg-white hover:bg-blue-100 border border-blue-300 rounded text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <span
                          className={`inline-block px-2 py-0.5 text-xs font-medium rounded mr-2 ${
                            end.tipo === "entrega"
                              ? "bg-blue-100 text-blue-800"
                              : end.tipo === "cobranca"
                                ? "bg-green-100 text-green-800"
                                : end.tipo === "comercial"
                                  ? "bg-purple-100 text-purple-800"
                                  : end.tipo === "residencial"
                                    ? "bg-orange-100 text-orange-800"
                                    : "bg-gray-100 text-gray-800"
                          }`}
                        >
                          {end.tipo === "entrega"
                            ? "📦"
                            : end.tipo === "cobranca"
                              ? "💰"
                              : end.tipo === "comercial"
                                ? "🏢"
                                : end.tipo === "residencial"
                                  ? "🏠"
                                  : "📍"}{" "}
                          {end.apelido || end.tipo}
                        </span>
                        <span className="text-gray-700">
                          {end.endereco}, {end.numero} - {end.bairro}
                        </span>
                      </button>
                    ))}

                  {!cliente.endereco &&
                    (!cliente.enderecos_adicionais ||
                      cliente.enderecos_adicionais.length === 0) && (
                      <p className="text-sm text-gray-600 italic">
                        Nenhum endereço cadastrado. Clique em "+ Adicionar
                        Endereço"
                      </p>
                    )}
                </div>
              </div>
            )}

            <textarea
              value={vendaAtual.entrega?.endereco_completo ?? ""}
              onChange={(e) => onEnderecoEntregaChange(e.target.value)}
              placeholder="Rua, número, complemento, bairro, cidade..."
              disabled={modoVisualizacao}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed"
              rows={3}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Entregador
            </label>
            <select
              value={entregadorSelecionado?.id || ""}
              onChange={(e) => onSelecionarEntregador(e.target.value)}
              disabled={modoVisualizacao}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed"
            >
              <option value="">Selecione um entregador</option>
              {entregadores.map((entregador) => (
                <option key={entregador.id} value={entregador.id}>
                  {entregador.nome_fantasia || entregador.nome}
                  {entregador.entregador_padrao && " (Padrão)"}
                </option>
              ))}
            </select>
            {entregadorSelecionado && (
              <p className="text-xs text-gray-500 mt-1">
                Modelo:{" "}
                {entregadorSelecionado.modelo_custo_entrega === "taxa_fixa"
                  ? "💵 Taxa Fixa"
                  : entregadorSelecionado.modelo_custo_entrega === "por_km"
                    ? "🚗 Por KM"
                    : entregadorSelecionado.modelo_custo_entrega === "rateio_rh"
                      ? "👔 Rateio RH"
                      : "⚙️ Configuração Global"}
              </p>
            )}
          </div>

          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Taxa de Entrega Total
              </label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500">
                  R$
                </span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={vendaAtual.entrega?.taxa_entrega_total ?? 0}
                  onChange={(e) => onTaxaEntregaTotalChange(e.target.value)}
                  disabled={modoVisualizacao}
                  className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Taxa Loja
                </label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500">
                    R$
                  </span>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max={vendaAtual.entrega?.taxa_entrega_total ?? 0}
                    value={parseFloat(
                      (vendaAtual.entrega?.taxa_loja ?? 0).toFixed(2),
                    )}
                    onChange={(e) => onTaxaLojaChange(e.target.value)}
                    disabled={modoVisualizacao}
                    className="w-full pl-12 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Taxa Entregador
                </label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500">
                    R$
                  </span>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max={vendaAtual.entrega?.taxa_entrega_total ?? 0}
                    value={parseFloat(
                      (vendaAtual.entrega?.taxa_entregador ?? 0).toFixed(2),
                    )}
                    onChange={(e) => onTaxaEntregadorChange(e.target.value)}
                    disabled={modoVisualizacao}
                    className="w-full pl-12 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed"
                  />
                </div>
              </div>
            </div>

            <p className="text-xs text-gray-500 italic">
              Preencha a taxa total e depois divida entre loja e entregador. Ao
              alterar uma, a outra é calculada automaticamente.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Observações da Entrega
            </label>
            <textarea
              value={vendaAtual.entrega?.observacoes_entrega ?? ""}
              onChange={(e) => onObservacoesEntregaChange(e.target.value)}
              placeholder="Horário preferencial, ponto de referência..."
              disabled={modoVisualizacao}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed"
              rows={2}
            />
          </div>
        </div>
      )}
    </div>
  );
}
