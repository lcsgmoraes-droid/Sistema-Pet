import { AlertCircle, Check, Layers, Package } from "lucide-react";
import CustomerIdentity from "../ui/CustomerIdentity";
import ProductIdentity from "../ui/ProductIdentity";
import SaleReference from "../ui/SaleReference";

function getVendaStatusDevolucaoInfo(status) {
  if (status === "finalizada") {
    return { label: "Finalizada", className: "bg-green-100 text-green-800" };
  }
  if (status === "baixa_parcial") {
    return { label: "Parcial", className: "bg-yellow-100 text-yellow-800" };
  }
  if (status === "pago_nf") {
    return { label: "Pago NF", className: "bg-blue-100 text-blue-800" };
  }
  if (status === "finalizada_devolucao" || status === "finalizada_devolucao_parcial") {
    return { label: "Dev. parcial", className: "bg-orange-100 text-orange-800" };
  }
  return { label: "Aberta", className: "bg-gray-100 text-gray-800" };
}

export default function ModalDevolucaoSections({
  calcularTotalDevolucao,
  componentesSelecionados,
  erro,
  filtros,
  formatarDataVenda,
  gerarCredito,
  handleConfirmar,
  handleEscolhaModoKit,
  handleQuantidadeChange,
  handleQuantidadeComponenteChange,
  isItemKit,
  itensSelecionados,
  loading,
  modoDevolucaoKit,
  motivo,
  onClose,
  passo,
  quantidades,
  quantidadesComponentes,
  selecionarVenda,
  setErro,
  setFiltros,
  setGerarCredito,
  setItensSelecionados,
  setMotivo,
  setPasso,
  setQuantidades,
  setVendaSelecionada,
  toggleComponente,
  toggleItem,
  vendaSelecionada,
  vendas,
}) {
  return (
    <>
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* Passo 1: Lista de Vendas */}
        {passo === 1 && (
          <div className="space-y-4">
            {/* Filtros */}
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Buscar</label>
                  <input
                    type="text"
                    value={filtros.busca}
                    onChange={(e) => setFiltros({ ...filtros, busca: e.target.value })}
                    placeholder="Número da venda, cliente..."
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Data Início
                  </label>
                  <input
                    type="date"
                    value={filtros.data_inicio}
                    onChange={(e) => setFiltros({ ...filtros, data_inicio: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Data Fim</label>
                  <input
                    type="date"
                    value={filtros.data_fim}
                    onChange={(e) => setFiltros({ ...filtros, data_fim: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* Lista de Vendas */}
            {loading ? (
              <div className="text-center py-12">
                <div className="animate-spin w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full mx-auto"></div>
                <p className="mt-4 text-gray-600">Carregando vendas...</p>
              </div>
            ) : vendas.length === 0 ? (
              <div className="text-center py-12 bg-gray-50 rounded-lg">
                <AlertCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600">Nenhuma venda encontrada</p>
              </div>
            ) : (
              <div className="space-y-2">
                {vendas.map((venda) => {
                  const statusInfo = getVendaStatusDevolucaoInfo(venda.status);

                  return (
                    <div
                      key={venda.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => selecionarVenda(venda)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          selecionarVenda(venda);
                        }
                      }}
                      className="w-full text-left p-4 border border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors"
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="font-semibold text-gray-900">
                            <SaleReference sale={venda} />
                          </div>
                          <div className="mt-1 text-sm text-gray-600">
                            <CustomerIdentity fallback="Consumidor Final" showLabel venda={venda} />
                          </div>
                          <div className="text-xs text-gray-500 mt-1">
                            {formatarDataVenda(venda)}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-lg font-bold text-green-600">
                            R$ {venda.total.toFixed(2)}
                          </div>
                          <div className={`text-xs mt-1 px-2 py-1 rounded ${statusInfo.className}`}>
                            {statusInfo.label}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {erro && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
                <AlertCircle className="w-5 h-5" />
                <span>{erro}</span>
              </div>
            )}
          </div>
        )}

        {/* Passo 2: Selecionar Itens */}
        {passo === 2 && vendaSelecionada && (
          <div className="space-y-6">
            {/* Informações da Venda */}
            <div className="bg-gray-50 rounded-lg p-4">
              <h3 className="mb-2 flex items-center gap-2 font-semibold text-gray-900">
                <SaleReference
                  label="Venda"
                  sale={vendaSelecionada}
                  showPrefix={false}
                  valueClassName="font-semibold text-gray-900"
                />
              </h3>
              <div className="grid grid-cols-1 gap-4 text-sm md:grid-cols-3">
                <div>
                  <span className="text-gray-600">Data:</span>
                  <span className="ml-2 font-medium">{formatarDataVenda(vendaSelecionada)}</span>
                </div>
                <div>
                  <CustomerIdentity
                    fallback="Consumidor Final"
                    nameClassName="font-medium text-gray-900"
                    showLabel
                    venda={vendaSelecionada}
                  />
                </div>
                <div>
                  <span className="text-gray-600">Total:</span>
                  <span className="ml-2 font-medium text-green-600">
                    R$ {vendaSelecionada.total.toFixed(2)}
                  </span>
                </div>
              </div>
            </div>

            {/* Lista de Itens */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-3">Itens da Venda</h3>
              <div className="space-y-2">
                {vendaSelecionada.itens.map((item) => {
                  const isKit = isItemKit(item);
                  const modoKit = modoDevolucaoKit[item.id];

                  return (
                    <div
                      key={item.id}
                      className={`border rounded-lg p-4 transition-colors ${
                        itensSelecionados[item.id]
                          ? "border-blue-500 bg-blue-50"
                          : "border-gray-200"
                      }`}
                    >
                      <div className="flex items-start gap-4">
                        <input
                          type="checkbox"
                          checked={itensSelecionados[item.id] || false}
                          onChange={() => toggleItem(item.id)}
                          className="mt-1 w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                        />

                        <div className="flex-1">
                          <ProductIdentity
                            className="gap-2"
                            name={item.produto_nome}
                            nameClassName="font-medium text-gray-900"
                            product={item}
                          >
                            {isKit && (
                              <span className="inline-flex items-center gap-1 px-2 py-1 bg-purple-100 text-purple-700 text-xs font-semibold rounded">
                                <Layers className="w-3 h-3" />
                                KIT
                              </span>
                            )}
                          </ProductIdentity>
                          <div className="text-sm text-gray-600">
                            Preço unitário: R$ {item.preco_unitario.toFixed(2)} | Qtd vendida:{" "}
                            {item.quantidade}
                          </div>

                          {/* 🆕 ESCOLHA: KIT INTEIRO OU COMPONENTES */}
                          {itensSelecionados[item.id] && isKit && (
                            <div className="mt-4 bg-white border-2 border-purple-300 rounded-lg p-4">
                              <div className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                                <Package className="w-5 h-5 text-purple-600" />
                                Como deseja devolver este KIT?
                              </div>

                              <div className="space-y-3">
                                <label className="flex items-start gap-3 cursor-pointer group">
                                  <input
                                    type="radio"
                                    name={`modo-kit-${item.id}`}
                                    checked={modoKit === "kit_inteiro"}
                                    onChange={() => handleEscolhaModoKit(item.id, "kit_inteiro")}
                                    className="mt-1 w-4 h-4 text-blue-600 focus:ring-2 focus:ring-blue-500"
                                  />
                                  <div className="flex-1">
                                    <div className="font-medium text-gray-800 group-hover:text-blue-700 transition-colors">
                                      📦 Devolver KIT Inteiro
                                    </div>
                                    <p className="text-xs text-gray-600 mt-1">
                                      Devolve o KIT completo como uma unidade
                                    </p>
                                  </div>
                                </label>

                                <label className="flex items-start gap-3 cursor-pointer group">
                                  <input
                                    type="radio"
                                    name={`modo-kit-${item.id}`}
                                    checked={modoKit === "componentes"}
                                    onChange={() => handleEscolhaModoKit(item.id, "componentes")}
                                    className="mt-1 w-4 h-4 text-purple-600 focus:ring-2 focus:ring-purple-500"
                                  />
                                  <div className="flex-1">
                                    <div className="font-medium text-gray-800 group-hover:text-purple-700 transition-colors">
                                      🧩 Selecionar Componentes
                                    </div>
                                    <p className="text-xs text-gray-600 mt-1">
                                      Escolha quais componentes do KIT devolver
                                    </p>
                                  </div>
                                </label>
                              </div>
                            </div>
                          )}

                          {/* QUANTIDADE - KIT INTEIRO */}
                          {itensSelecionados[item.id] && !isKit && (
                            <div className="mt-3 flex items-center gap-4">
                              <label className="text-sm font-medium text-gray-700">
                                Quantidade a devolver:
                              </label>
                              <input
                                type="number"
                                step="0.01"
                                min="0"
                                max={item.quantidade}
                                value={quantidades[item.id]}
                                onChange={(e) => handleQuantidadeChange(item.id, e.target.value)}
                                className="w-32 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                              />
                              <span className="text-sm text-gray-600">
                                Subtotal: R${" "}
                                {(item.preco_unitario * (quantidades[item.id] || 0)).toFixed(2)}
                              </span>
                            </div>
                          )}

                          {/* QUANTIDADE - KIT INTEIRO (quando escolheu devolver inteiro) */}
                          {itensSelecionados[item.id] && isKit && modoKit === "kit_inteiro" && (
                            <div className="mt-3 flex items-center gap-4">
                              <label className="text-sm font-medium text-gray-700">
                                Quantidade de KITs a devolver:
                              </label>
                              <input
                                type="number"
                                step="0.01"
                                min="0"
                                max={item.quantidade}
                                value={quantidades[item.id]}
                                onChange={(e) => handleQuantidadeChange(item.id, e.target.value)}
                                className="w-32 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                              />
                              <span className="text-sm text-gray-600">
                                Subtotal: R${" "}
                                {(item.preco_unitario * (quantidades[item.id] || 0)).toFixed(2)}
                              </span>
                            </div>
                          )}

                          {/* LISTA DE COMPONENTES (quando escolheu devolver por componentes) */}
                          {itensSelecionados[item.id] && isKit && modoKit === "componentes" && (
                            <div className="mt-4 bg-gradient-to-br from-purple-50 to-blue-50 border border-purple-200 rounded-lg p-4">
                              <div className="font-semibold text-gray-800 mb-3">
                                Selecione os componentes a devolver:
                              </div>
                              <div className="space-y-3">
                                {item.composicao_kit.map((componente, compIndex) => {
                                  const compSelecionado =
                                    componentesSelecionados[item.id]?.[compIndex];
                                  const qtdMaxima = componente.quantidade * item.quantidade;

                                  return (
                                    <div
                                      key={compIndex}
                                      className={`border rounded-lg p-3 transition-colors ${
                                        compSelecionado
                                          ? "border-purple-500 bg-white"
                                          : "border-gray-200 bg-gray-50"
                                      }`}
                                    >
                                      <div className="flex items-start gap-3">
                                        <input
                                          type="checkbox"
                                          checked={compSelecionado || false}
                                          onChange={() => toggleComponente(item.id, compIndex)}
                                          className="mt-1 w-4 h-4 text-purple-600 rounded focus:ring-2 focus:ring-purple-500"
                                        />
                                        <div className="flex-1">
                                          <div className="flex items-center gap-2">
                                            <Package className="w-4 h-4 text-gray-500" />
                                            <ProductIdentity
                                              name={componente.produto_nome}
                                              nameClassName="font-medium text-gray-800"
                                              product={componente}
                                            />
                                          </div>
                                          <div className="text-xs text-gray-600 mt-1">
                                            Qtd no KIT: {componente.quantidade} | Qtd total
                                            disponível: {qtdMaxima}
                                          </div>

                                          {compSelecionado && (
                                            <div className="mt-2 flex items-center gap-3">
                                              <label className="text-xs font-medium text-gray-700">
                                                Quantidade:
                                              </label>
                                              <input
                                                type="number"
                                                step="0.01"
                                                min="0"
                                                max={qtdMaxima}
                                                value={
                                                  quantidadesComponentes[item.id]?.[compIndex] || 0
                                                }
                                                onChange={(e) =>
                                                  handleQuantidadeComponenteChange(
                                                    item.id,
                                                    compIndex,
                                                    e.target.value,
                                                  )
                                                }
                                                className="w-24 px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-purple-500"
                                              />
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Motivo */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Motivo da Devolução *
              </label>
              <textarea
                value={motivo}
                onChange={(e) => setMotivo(e.target.value)}
                placeholder="Descreva o motivo da devolução..."
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                rows={3}
              />
            </div>

            {/* Opção de Crédito ou Dinheiro */}
            <div className="bg-gradient-to-br from-purple-50 to-blue-50 border-2 border-purple-200 rounded-lg p-5">
              <label className="block text-sm font-bold text-gray-800 mb-3">
                💳 Tipo de Devolução
              </label>
              <div className="space-y-3">
                <label className="flex items-start gap-3 cursor-pointer group">
                  <input
                    type="radio"
                    checked={!gerarCredito}
                    onChange={() => setGerarCredito(false)}
                    className="mt-1 w-5 h-5 text-green-600 focus:ring-2 focus:ring-green-500"
                  />
                  <div className="flex-1">
                    <div className="font-semibold text-gray-800 group-hover:text-green-700 transition-colors">
                      💵 Devolver em Dinheiro
                    </div>
                    <p className="text-xs text-gray-600 mt-1">
                      O valor será devolvido em dinheiro e registrado como saída de caixa
                    </p>
                  </div>
                </label>

                <label className="flex items-start gap-3 cursor-pointer group">
                  <input
                    type="radio"
                    checked={gerarCredito}
                    onChange={() => setGerarCredito(true)}
                    className="mt-1 w-5 h-5 text-purple-600 focus:ring-2 focus:ring-purple-500"
                  />
                  <div className="flex-1">
                    <div className="font-semibold text-gray-800 group-hover:text-purple-700 transition-colors">
                      🎁 Gerar Crédito para o Cliente
                    </div>
                    <p className="text-xs text-gray-600 mt-1">
                      O valor será convertido em crédito para uso em futuras compras (sem
                      movimentação de caixa)
                    </p>
                  </div>
                </label>
              </div>

              {gerarCredito && !vendaSelecionada?.cliente_id && (
                <div className="mt-3 p-3 bg-yellow-50 border border-yellow-300 rounded-lg">
                  <p className="text-xs text-yellow-800 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" />
                    <span>
                      <strong>Atenção:</strong> Esta venda não possui cliente vinculado. Para gerar
                      crédito, é necessário ter um cliente cadastrado.
                    </span>
                  </p>
                </div>
              )}
            </div>

            {/* Total */}
            <div
              className={`border-2 rounded-lg p-4 ${gerarCredito ? "bg-purple-50 border-purple-300" : "bg-orange-50 border-orange-200"}`}
            >
              <div className="flex justify-between items-center">
                <div>
                  <span className="text-lg font-semibold text-gray-900">
                    {gerarCredito ? "Crédito a Gerar:" : "Total da Devolução:"}
                  </span>
                  {gerarCredito && vendaSelecionada?.cliente && (
                    <p className="text-xs text-gray-600 mt-1">
                      <CustomerIdentity
                        fallback="Consumidor Final"
                        nameClassName="font-semibold text-gray-800"
                        showLabel
                        venda={vendaSelecionada}
                      />
                    </p>
                  )}
                </div>
                <span
                  className={`text-2xl font-bold ${gerarCredito ? "text-purple-600" : "text-orange-600"}`}
                >
                  R$ {calcularTotalDevolucao().toFixed(2)}
                </span>
              </div>
            </div>

            {erro && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
                <AlertCircle className="w-5 h-5" />
                <span>{erro}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="border-t p-6 bg-gray-50">
        <div className="flex justify-between">
          <button
            onClick={
              passo === 1
                ? onClose
                : () => {
                    setPasso(1);
                    setVendaSelecionada(null);
                    setItensSelecionados({});
                    setQuantidades({});
                    setMotivo("");
                    setErro("");
                  }
            }
            disabled={loading}
            className="px-6 py-3 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg font-medium transition-colors disabled:opacity-50"
          >
            {passo === 1 ? "Cancelar" : "Voltar"}
          </button>

          {passo === 2 && (
            <button
              onClick={handleConfirmar}
              disabled={loading || Object.values(itensSelecionados).filter(Boolean).length === 0}
              className="flex items-center gap-2 px-8 py-3 bg-orange-600 hover:bg-orange-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Processando...</span>
                </>
              ) : (
                <>
                  <Check className="w-5 h-5" />
                  <span>Confirmar Devolução</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </>
  );
}
