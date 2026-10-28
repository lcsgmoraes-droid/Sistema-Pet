import { Wallet, AlertCircle } from "lucide-react";

import InputMoeda from "../v2/InputMoeda/InputMoeda";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import SeletorFormaRecebimento from "../v2/SeletorFormaRecebimento/SeletorFormaRecebimento";
import CamposCartaoRecebimento from "../v2/CamposCartaoRecebimento/CamposCartaoRecebimento";
import InputTexto from "../v2/InputTexto/InputTexto";
import InputQuantidade from "../v2/InputQuantidade/InputQuantidade";
import InputCombobox from "../v2/InputCombobox/InputCombobox";
import { formatMoneyBRL, formatPercent } from "../../utils/formatters";
import {
  gerarPlanoCrediario,
  mascararDataCrediario,
  vencimentoPadraoCrediario,
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
  saldoCashbackTotal,
  cashbackLimitPercent,
  saldoCreditoDisponivel,
  formasPagamento,
  valorRecebido,
  troco,
  operadoras,
  operadoraSelecionada,
  setOperadoraSelecionada,
  numeroParcelas,
  bandeira,
  nsuCartao,
  opcoesParcelamentoRef,
  estiloVisualParcelamento,
  adicionarPagamento,
  bandeirasDisponiveis,
  parcelasDisponiveis,
  taxaCartaoSelecionada,
}) {
  const planoCrediario =
    formaPagamentoSelecionada?.tipo === "crediario"
      ? gerarPlanoCrediario({
          valorTotal: Math.min(Number(valorRecebido || 0), Number(valorRestante || 0)),
          numeroParcelas,
          primeiraData: formaPagamentoSelecionada.data_vencimento_crediario,
          intervalo: formaPagamentoSelecionada.intervalo_crediario || "mensal",
        })
      : [];

  return (
    <>
      {/* Coluna Esquerda - Seleção de Pagamentos */}
      <div className="space-y-6">
        <div>
          <h3 className="font-semibold text-gray-900 mb-4">Selecione a forma de pagamento</h3>

          <div className="grid grid-cols-2 gap-3">
            {/* Crédito Cliente (exibir primeiro se disponível) */}
            {venda.cliente && saldoCreditoDisponivel > 0 && (
              <BotaoInteracao
                onClick={() => {
                  setFormaPagamentoSelecionada({
                    id: "credito_cliente",
                    nome: "Crédito Cliente",
                    tipo: "credito_cliente",
                    icone: "🎁",
                    credito_disponivel: saldoCreditoDisponivel,
                  });
                  setNumeroParcelas(1);
                  setBandeira("");
                  setNsuCartao(""); // Limpar NSU
                  // Pre-preencher com o menor valor entre crédito e valor restante
                  setValorRecebido(Math.min(saldoCreditoDisponivel, valorRestante));
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
                  {formatMoneyBRL(saldoCreditoDisponivel)}
                </div>
              </BotaoInteracao>
            )}

            {/* Cashback de campanhas (exibir se disponível) */}
            {venda.cliente && saldoCashbackTotal > 0 && (
              <BotaoInteracao
                disabled={saldoCashback <= 0}
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
                className={`p-4 rounded-lg border-2 transition-all disabled:opacity-60 disabled:cursor-not-allowed ${
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
                <div className="text-xs text-green-700 mt-1">
                  Saldo: {formatMoneyBRL(saldoCashbackTotal)}
                </div>
                <div className="text-xs text-green-600 mt-1 font-semibold">
                  Até {formatMoneyBRL(Math.min(saldoCashback, valorRestante))}
                </div>
                {cashbackLimitPercent !== null && (
                  <div className="text-xs text-green-700 mt-1">
                    Limite: {formatPercent(cashbackLimitPercent)} da compra
                  </div>
                )}
              </BotaoInteracao>
            )}

            <div className="col-span-2 min-w-0">
              <SeletorFormaRecebimento
                formas={formasPagamento}
                value={formaPagamentoSelecionada?.id}
                onChange={(forma) => {
                  setFormaPagamentoSelecionada(
                    forma.tipo === "crediario"
                      ? {
                          ...forma,
                          data_vencimento_crediario: vencimentoPadraoCrediario(
                            forma.prazo_dias || forma.prazo_recebimento || 30,
                          ),
                          intervalo_crediario: "mensal",
                        }
                      : forma,
                  );
                  setNumeroParcelas(1);
                  setBandeira("");
                  setNsuCartao("");
                  setValorRecebido(valorRestante);
                }}
              />
            </div>
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
                  {formatMoneyBRL(saldoCreditoDisponivel)}
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
                  {formatMoneyBRL(saldoCashback)}
                </div>
                {cashbackLimitPercent !== null && (
                  <p className="text-xs text-green-700 mt-1">
                    Limite de {formatPercent(cashbackLimitPercent)} da compra. Saldo acumulado:{" "}
                    {formatMoneyBRL(saldoCashbackTotal)}.
                  </p>
                )}
                <p className="text-xs text-green-700 mt-1">
                  💡 Saldo acumulado em campanhas — não gera movimentação de caixa
                </p>
              </div>
            )}

            <div>
              <InputMoeda
                id="modal-pagamento-valor"
                label={
                  formaPagamentoSelecionada.id === "credito_cliente"
                    ? "Valor a Utilizar"
                    : formaPagamentoSelecionada.id === "cashback"
                      ? "Valor a Resgatar"
                      : formaPagamentoSelecionada.tipo === "dinheiro"
                        ? "Valor entregue em dinheiro"
                        : "Valor do pagamento"
                }
                value={valorRecebido}
                onChange={setValorRecebido}
                help={
                  formaPagamentoSelecionada.tipo === "dinheiro"
                    ? "O saldo é aplicado à venda e o excedente é devolvido como troco."
                    : "Informe o valor integral. Excedente exige justificativa; benefícios e crediário respeitam o saldo."
                }
              />
              {formaPagamentoSelecionada.id === "credito_cliente" && (
                <p className="text-xs text-gray-600 mt-1">
                  Máximo: {formatMoneyBRL(Math.min(saldoCreditoDisponivel, valorRestante))}
                </p>
              )}
              {formaPagamentoSelecionada.id === "cashback" && (
                <p className="text-xs text-gray-600 mt-1">
                  Máximo: {formatMoneyBRL(Math.min(saldoCashback, valorRestante))}
                </p>
              )}
            </div>

            {formaPagamentoSelecionada.tipo === "crediario" && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Primeira data de vencimento
                </label>
                <InputTexto
                  label="Primeira data de vencimento"
                  inputMode="numeric"
                  value={formaPagamentoSelecionada.data_vencimento_crediario || ""}
                  onChange={(texto) =>
                    setFormaPagamentoSelecionada((atual) => ({
                      ...atual,
                      data_vencimento_crediario: mascararDataCrediario(texto),
                    }))
                  }
                  placeholder="DD-MM-AAAA"
                  maxLength={10}
                />
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Quantidade de parcelas
                    </label>
                    <InputQuantidade
                      label="Quantidade de parcelas"
                      min={1}
                      value={numeroParcelas}
                      onChange={(valor) =>
                        setNumeroParcelas(Math.max(1, Math.min(60, Math.floor(valor))))
                      }
                    />
                  </div>
                  {numeroParcelas > 1 && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Intervalo
                      </label>
                      <InputCombobox
                        label="Intervalo"
                        value={formaPagamentoSelecionada.intervalo_crediario || "mensal"}
                        permitirLimpar={false}
                        opcoes={[
                          { value: "7_dias", label: "A cada 7 dias" },
                          { value: "15_dias", label: "A cada 15 dias" },
                          { value: "mensal", label: "Mensal" },
                        ]}
                        onChange={(intervalo_crediario) =>
                          setFormaPagamentoSelecionada((atual) => ({
                            ...atual,
                            intervalo_crediario,
                          }))
                        }
                      />
                    </div>
                  )}
                </div>
                {planoCrediario.length > 0 && (
                  <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3">
                    <p className="text-sm font-semibold text-amber-900 mb-2">Prévia das parcelas</p>
                    <div className="max-h-44 overflow-y-auto space-y-1">
                      {planoCrediario.map((parcela) => (
                        <div
                          key={parcela.numero}
                          className="flex items-center justify-between text-xs text-amber-900"
                        >
                          <span>
                            {parcela.numero}/{parcela.total_parcelas} · {parcela.data_vencimento}
                          </span>
                          <strong>{formatMoneyBRL(parcela.valor)}</strong>
                        </div>
                      ))}
                    </div>
                    <p className="text-[11px] text-amber-700 mt-2">
                      A última parcela absorve eventual diferença de centavos.
                    </p>
                  </div>
                )}
                {!venda.cliente && (
                  <p className="text-xs text-amber-700 mt-1">
                    Selecione o cliente da venda para usar o crediário.
                  </p>
                )}
              </div>
            )}

            {/* Aviso de excedente para métodos NÃO-dinheiro */}
            {formaPagamentoSelecionada?.tipo !== "dinheiro" &&
              formaPagamentoSelecionada?.tipo !== "credito_cliente" &&
              formaPagamentoSelecionada?.tipo !== "cashback" &&
              valorRestante > 0 &&
              troco > 0 && (
                <div className="rounded-xl bg-amber-50 border border-amber-200 p-3 space-y-2">
                  <div className="flex items-center gap-2 text-amber-800 text-sm font-semibold">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    Valor {formatMoneyBRL(valorRecebido)} supera o restante em{" "}
                    <span className="font-bold">{formatMoneyBRL(troco)}</span>
                  </div>
                  <p className="text-xs text-amber-700">
                    {["crediario", "boleto"].includes(formaPagamentoSelecionada.tipo)
                      ? "Crediário e boleto devem respeitar o saldo da venda; revise o valor previsto."
                      : "Confira o valor. Para registrar o excedente, confirme a exceção com justificativa no resumo."}
                  </p>
                </div>
              )}

            {/* Troco (somente para dinheiro) */}
            {formaPagamentoSelecionada.tipo === "dinheiro" && valorRecebido > 0 && (
              <div
                className={`rounded-lg p-3 ${troco > 0 ? "bg-yellow-50 border border-yellow-200" : "bg-gray-100"}`}
              >
                <div className="text-sm font-medium">
                  <p className="mb-1 text-slate-700 dark:text-slate-300">
                    Aplicado à venda:{" "}
                    {formatMoneyBRL(Math.min(Number(valorRecebido || 0), valorRestante))}
                  </p>
                  <span className={troco > 0 ? "text-yellow-800" : "text-gray-600"}>
                    Troco: {formatMoneyBRL(troco)}
                  </span>
                </div>
              </div>
            )}

            {["cartao_credito", "cartao_debito", "link_pagamento"].includes(
              formaPagamentoSelecionada.tipo,
            ) && (
              <div ref={opcoesParcelamentoRef}>
                <CamposCartaoRecebimento
                  operadoras={operadoras}
                  operadoraId={operadoraSelecionada?.id}
                  onOperadoraChange={(id) => {
                    setOperadoraSelecionada(operadoras.find((o) => o.id === id) || null);
                    setNumeroParcelas(1);
                  }}
                  bandeiras={bandeirasDisponiveis}
                  bandeira={bandeira}
                  onBandeiraChange={setBandeira}
                  nsu={nsuCartao}
                  onNsuChange={setNsuCartao}
                  parcelas={parcelasDisponiveis}
                  numeroParcelas={numeroParcelas}
                  onParcelasChange={setNumeroParcelas}
                  valor={valorRecebido || valorRestante}
                  permiteParcelamento={Boolean(formaPagamentoSelecionada.permite_parcelamento)}
                />
                {bandeira &&
                  operadoraSelecionada?.taxas_configuradas > 0 &&
                  !taxaCartaoSelecionada && (
                    <p role="alert" className="mt-2 text-sm text-red-700 dark:text-red-400">
                      Esta combinação não está disponível. Confira bandeira e parcelas.
                    </p>
                  )}
                {valorRecebido > 0 && numeroParcelas > 1 && (
                  <div
                    className={`mt-2 rounded-lg border p-3 ${estiloVisualParcelamento.painelClass}`}
                  >
                    <p className={`text-sm font-medium ${estiloVisualParcelamento.tituloClass}`}>
                      {estiloVisualParcelamento.prefixo}
                      {numeroParcelas}x de {formatMoneyBRL(valorRecebido / numeroParcelas)}
                    </p>
                    <p className={`text-xs ${estiloVisualParcelamento.descricaoClass}`}>
                      Total: {formatMoneyBRL(valorRecebido)} {estiloVisualParcelamento.aviso}
                    </p>
                  </div>
                )}
              </div>
            )}

            {valorRestante <= 0 && (
              <p className="text-xs text-slate-600 dark:text-slate-300">
                O saldo já foi coberto. Remova ou revise um pagamento antes de adicionar outro.
              </p>
            )}
            <BotaoInteracao
              onClick={adicionarPagamento}
              disabled={valorRestante <= 0}
              className="w-full"
            >
              Adicionar Pagamento
            </BotaoInteracao>
          </div>
        )}
      </div>
    </>
  );
}
