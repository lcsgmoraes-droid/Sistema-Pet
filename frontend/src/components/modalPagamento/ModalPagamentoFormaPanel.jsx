import { Wallet, AlertCircle } from "lucide-react";

import CurrencyInput from "../CurrencyInput";
import PaymentMethodIcon from "../PaymentMethodIcon";
import {
  BANDEIRAS_CARTAO,
  obterCorVisualParcelamento,
  obterEstiloVisualParcelamento,
} from "../modalPagamentoUtils";

export default function ModalPagamentoFormaPanel({
  venda,
  formaPagamentoSelecionada,
  setFormaPagamentoSelecionada,
  setNumeroParcelas,
  setBandeira,
  setNsuCartao,
  setValorRecebido,
  valorRestante,
  saldoCashback,
  formasPagamento,
  valorRecebido,
  troco,
  opcaoExcedente,
  setOpcaoExcedente,
  operadoras,
  operadoraSelecionada,
  setOperadoraSelecionada,
  numeroParcelas,
  bandeira,
  nsuCartao,
  opcoesParcelamentoRef,
  estiloVisualParcelamento,
  simulacoesParcelamento,
  adicionarPagamento,
}) {
  return (
    <>
      {/* Coluna Esquerda - Seleção de Pagamentos */}
      <div className="space-y-6">
        <div>
          <h3 className="font-semibold text-gray-900 mb-4">Selecione a forma de pagamento</h3>

          <div className="grid grid-cols-2 gap-3">
            {/* Crédito Cliente (exibir primeiro se disponível) */}
            {venda.cliente && venda.cliente.credito > 0 && (
              <button
                onClick={() => {
                  setFormaPagamentoSelecionada({
                    id: "credito_cliente",
                    nome: "Crédito Cliente",
                    tipo: "credito_cliente",
                    icone: "🎁",
                    credito_disponivel: parseFloat(venda.cliente.credito),
                  });
                  setNumeroParcelas(1);
                  setBandeira("");
                  setNsuCartao(""); // Limpar NSU
                  // Pre-preencher com o menor valor entre crédito e valor restante
                  setValorRecebido(Math.min(parseFloat(venda.cliente.credito), valorRestante));
                }}
                className={`p-4 rounded-lg border-2 transition-all ${
                  formaPagamentoSelecionada?.id === "credito_cliente"
                    ? "border-purple-500 bg-purple-50"
                    : "border-purple-200 bg-purple-50/50 hover:border-purple-300"
                }`}
              >
                <div className="text-2xl mb-1">🎁</div>
                <div
                  className={`text-sm font-medium ${
                    formaPagamentoSelecionada?.id === "credito_cliente"
                      ? "text-purple-900"
                      : "text-purple-700"
                  }`}
                >
                  Crédito Cliente
                </div>
                <div className="text-xs text-purple-600 mt-1 font-semibold">
                  R$ {parseFloat(venda.cliente.credito).toFixed(2).replace(".", ",")}
                </div>
              </button>
            )}

            {/* Cashback de campanhas (exibir se disponível) */}
            {venda.cliente && saldoCashback > 0 && (
              <button
                onClick={() => {
                  setFormaPagamentoSelecionada({
                    id: "cashback",
                    nome: "Cashback",
                    tipo: "cashback",
                    icone: "💰",
                  });
                  setNumeroParcelas(1);
                  setBandeira("");
                  setNsuCartao("");
                  setValorRecebido(Math.min(saldoCashback, valorRestante));
                }}
                className={`p-4 rounded-lg border-2 transition-all ${
                  formaPagamentoSelecionada?.id === "cashback"
                    ? "border-green-500 bg-green-50"
                    : "border-green-200 bg-green-50/50 hover:border-green-300"
                }`}
              >
                <div className="text-2xl mb-1">💰</div>
                <div
                  className={`text-sm font-medium ${
                    formaPagamentoSelecionada?.id === "cashback"
                      ? "text-green-900"
                      : "text-green-700"
                  }`}
                >
                  Cashback
                </div>
                <div className="text-xs text-green-600 mt-1 font-semibold">
                  R$ {saldoCashback.toFixed(2).replace(".", ",")}
                </div>
              </button>
            )}

            {/* Formas de pagamento cadastradas */}
            {formasPagamento.map((forma) => {
              const selecionada = formaPagamentoSelecionada?.id === forma.id;

              return (
                <button
                  key={forma.id}
                  onClick={() => {
                    setFormaPagamentoSelecionada(forma);
                    setNumeroParcelas(1);
                    setBandeira("");
                    setNsuCartao(""); // Limpar NSU
                    setValorRecebido(valorRestante); // Pré-preencher valor restante
                  }}
                  className={`p-4 rounded-lg border-2 transition-all ${
                    selecionada
                      ? "border-blue-500 bg-blue-50"
                      : "border-gray-200 hover:border-gray-300"
                  }`}
                >
                  <div className="flex justify-center mb-1 text-gray-500">
                    <PaymentMethodIcon icone={forma.icone} nome={forma.nome} />
                  </div>
                  <div
                    className={`text-sm font-medium ${selecionada ? "text-blue-900" : "text-gray-700"}`}
                  >
                    {forma.nome}
                  </div>
                  {forma.taxa_percentual > 0 && (
                    <div className="text-xs text-gray-500 mt-1">Taxa: {forma.taxa_percentual}%</div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Formulário de pagamento */}
        {formaPagamentoSelecionada && (
          <div className="bg-gray-50 rounded-lg p-4 space-y-4">
            {/* Informações de Crédito Cliente */}
            {formaPagamentoSelecionada.id === "credito_cliente" && (
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 mb-3">
                <div className="flex items-center gap-2 text-purple-800 mb-2">
                  <Wallet className="w-4 h-4" />
                  <span className="text-sm font-semibold">Crédito Disponível</span>
                </div>
                <div className="text-lg font-bold text-purple-600">
                  R$ {formaPagamentoSelecionada.credito_disponivel.toFixed(2).replace(".", ",")}
                </div>
                <p className="text-xs text-purple-700 mt-1">💡 Não gera movimentação de caixa</p>
              </div>
            )}

            {/* Informações de Cashback */}
            {formaPagamentoSelecionada.id === "cashback" && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-3">
                <div className="flex items-center gap-2 text-green-800 mb-2">
                  <span className="text-base">💰</span>
                  <span className="text-sm font-semibold">Cashback Disponível</span>
                </div>
                <div className="text-lg font-bold text-green-600">
                  R$ {saldoCashback.toFixed(2).replace(".", ",")}
                </div>
                <p className="text-xs text-green-700 mt-1">
                  💡 Saldo acumulado em campanhas — não gera movimentação de caixa
                </p>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {formaPagamentoSelecionada.id === "credito_cliente"
                  ? "Valor a Utilizar"
                  : formaPagamentoSelecionada.id === "cashback"
                    ? "Valor a Resgatar"
                    : "Valor Recebido"}
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">R$</span>
                <CurrencyInput
                  value={valorRecebido}
                  onChange={(v) => {
                    if (formaPagamentoSelecionada.id === "credito_cliente") {
                      const maxCredito = Math.min(
                        formaPagamentoSelecionada.credito_disponivel,
                        valorRestante,
                      );
                      setValorRecebido(Math.min(v, maxCredito));
                    } else if (formaPagamentoSelecionada.id === "cashback") {
                      const maxCashback = Math.min(saldoCashback, valorRestante);
                      setValorRecebido(Math.min(v, maxCashback));
                    } else {
                      setValorRecebido(v);
                    }
                  }}
                  placeholder={valorRestante.toFixed(2).replace(".", ",")}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  autoFocus
                />
              </div>
              {formaPagamentoSelecionada.id === "credito_cliente" && (
                <p className="text-xs text-gray-600 mt-1">
                  Máximo: R${" "}
                  {Math.min(formaPagamentoSelecionada.credito_disponivel, valorRestante).toFixed(2)}
                </p>
              )}
              {formaPagamentoSelecionada.id === "cashback" && (
                <p className="text-xs text-gray-600 mt-1">
                  Máximo: R$ {Math.min(saldoCashback, valorRestante).toFixed(2).replace(".", ",")}
                </p>
              )}
            </div>

            {/* Aviso de excedente para métodos NÃO-dinheiro */}
            {formaPagamentoSelecionada?.tipo !== "dinheiro" &&
              formaPagamentoSelecionada?.tipo !== "credito_cliente" &&
              formaPagamentoSelecionada?.tipo !== "cashback" &&
              troco > 0.005 && (
                <div className="rounded-xl bg-amber-50 border border-amber-200 p-3 space-y-2">
                  <div className="flex items-center gap-2 text-amber-800 text-sm font-semibold">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    Valor R$ {valorRecebido.toFixed(2).replace(".", ",")} supera o total em{" "}
                    <span className="font-bold">R$ {troco.toFixed(2).replace(".", ",")}</span>
                  </div>
                  {venda.cliente ? (
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() =>
                          setOpcaoExcedente(opcaoExcedente === "troco" ? null : "troco")
                        }
                        className={`flex-1 py-2 text-xs font-semibold rounded-xl border-2 transition-colors ${
                          opcaoExcedente === "troco"
                            ? "bg-yellow-500 border-yellow-500 text-white"
                            : "bg-white border-yellow-300 text-yellow-800 hover:bg-yellow-50"
                        }`}
                      >
                        💵 Troco em dinheiro
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          setOpcaoExcedente(opcaoExcedente === "credito" ? null : "credito")
                        }
                        className={`flex-1 py-2 text-xs font-semibold rounded-xl border-2 transition-colors ${
                          opcaoExcedente === "credito"
                            ? "bg-green-500 border-green-500 text-white"
                            : "bg-white border-green-300 text-green-800 hover:bg-green-50"
                        }`}
                      >
                        💳 Gerar crédito
                      </button>
                    </div>
                  ) : (
                    <p className="text-xs text-amber-700">
                      Sem cliente associado — o excedente será desconsiderado.
                    </p>
                  )}
                </div>
              )}

            {/* Troco (somente para dinheiro) */}
            {formaPagamentoSelecionada.tipo === "dinheiro" && valorRecebido > 0 && (
              <div
                className={`rounded-lg p-3 ${troco > 0 ? "bg-yellow-50 border border-yellow-200" : "bg-gray-100"}`}
              >
                <div className="text-sm font-medium">
                  <span className={troco > 0 ? "text-yellow-800" : "text-gray-600"}>
                    Troco: R$ {troco.toFixed(2)}
                  </span>
                </div>
              </div>
            )}

            {/* Bandeira do cartão */}
            {formaPagamentoSelecionada?.tipo &&
              ["cartao_credito", "cartao_debito"].includes(formaPagamentoSelecionada.tipo) && (
                <>
                  {/* 🆕 OPERADORA DE CARTÃO */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Operadora *
                    </label>
                    <select
                      value={operadoraSelecionada?.id || ""}
                      onChange={(e) => {
                        const op = operadoras.find((o) => o.id === parseInt(e.target.value));
                        setOperadoraSelecionada(op);
                        // Ajustar parcelas se exceder o máximo da nova operadora
                        if (op && numeroParcelas > op.max_parcelas) {
                          setNumeroParcelas(op.max_parcelas);
                        }
                      }}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">Selecione a operadora...</option>
                      {operadoras.map((op) => (
                        <option key={op.id} value={op.id}>
                          {op.nome} ({op.max_parcelas}x máx)
                        </option>
                      ))}
                    </select>
                    {operadoraSelecionada && (
                      <p className="text-xs text-gray-500 mt-1">
                        Máximo de {operadoraSelecionada.max_parcelas} parcelas
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Bandeira</label>
                    <select
                      value={bandeira}
                      onChange={(e) => setBandeira(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">Selecione...</option>
                      {BANDEIRAS_CARTAO.map((b) => (
                        <option key={b} value={b}>
                          {b}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* NSU do Cartão (para conciliação bancária) */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      NSU (Número Sequencial Único)
                      <span className="text-gray-500 text-xs ml-1">
                        (Opcional - para conciliação)
                      </span>
                    </label>
                    <input
                      type="text"
                      value={nsuCartao}
                      onChange={(e) => setNsuCartao(e.target.value)}
                      placeholder="Ex: 123456789"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </>
              )}

            {/* Número de parcelas (apenas para cartão de crédito parcelado) */}
            {formaPagamentoSelecionada?.permite_parcelamento && (
              <div ref={opcoesParcelamentoRef}>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Número de Parcelas
                </label>
                <select
                  value={numeroParcelas}
                  onChange={(e) => setNumeroParcelas(parseInt(e.target.value))}
                  className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 ${estiloVisualParcelamento.selectClass}`}
                >
                  {/* 🆕 Usar max_parcelas da operadora se cartão, senão da forma de pagamento */}
                  {Array.from(
                    {
                      length:
                        operadoraSelecionada?.max_parcelas ||
                        formaPagamentoSelecionada.parcelas_maximas ||
                        12,
                    },
                    (_, i) => i + 1,
                  ).map((n) => {
                    const valorParaParcelar = valorRecebido || valorRestante;
                    const valorParcela = valorParaParcelar / n;
                    const cor = obterCorVisualParcelamento({
                      formaPagamento: formaPagamentoSelecionada,
                      simulacoesParcelamento,
                      numeroParcelas: n,
                      statusMargem: "verde",
                    });
                    const estilo = obterEstiloVisualParcelamento(cor);

                    return (
                      <option key={n} value={n} className={estilo.optionClass}>
                        {estilo.prefixo}
                        {n}x de R$ {valorParcela.toFixed(2)}{" "}
                        {valorRecebido > 0 ? `(Total: R$ ${valorParaParcelar.toFixed(2)})` : ""}
                      </option>
                    );
                  })}
                </select>
                {valorRecebido > 0 && numeroParcelas > 1 && (
                  <div
                    className={`mt-2 p-3 border rounded-lg ${estiloVisualParcelamento.painelClass}`}
                  >
                    <p className={`text-sm font-medium ${estiloVisualParcelamento.tituloClass}`}>
                      {estiloVisualParcelamento.prefixo}
                      💳 {numeroParcelas}x de R$ {(valorRecebido / numeroParcelas).toFixed(2)}
                    </p>
                    <p className={`text-xs mt-1 ${estiloVisualParcelamento.descricaoClass}`}>
                      Valor total parcelado: R$ {valorRecebido.toFixed(2)}
                      {estiloVisualParcelamento.aviso}
                    </p>
                  </div>
                )}
              </div>
            )}

            <button
              onClick={adicionarPagamento}
              className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
            >
              Adicionar Pagamento
            </button>
          </div>
        )}
      </div>
    </>
  );
}
