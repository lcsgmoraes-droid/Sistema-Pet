import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Calculator, Printer, Receipt, X } from "lucide-react";
import CustomerIdentity from "../ui/CustomerIdentity";
import SaleReference from "../ui/SaleReference";
import { formatBRL, formatMoneyBRL } from "../../utils/formatters";
import CurrencyInput from "../CurrencyInput";

export function CashCountPanel({
  aplicarContagem,
  atualizarQuantidadeNota,
  atualizarValorMoedas,
  calcularTotalNotas,
  limparContagem,
  mostrarContagem,
  notas,
  setMostrarContagem,
}) {
  return (
    <>
      {/* Painel de Contagem de Notas */}
      {mostrarContagem && (
        <div className="mt-4 bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-300 rounded-xl p-5 shadow-lg">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-base font-bold text-gray-900 flex items-center">
              <Calculator className="w-5 h-5 mr-2 text-blue-600" />
              Auxiliar de Contagem
            </h4>
            <button
              onClick={() => setMostrarContagem(false)}
              className="text-gray-400 hover:text-gray-600 p-1"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-3">
            {/* Notas de R$ 2 */}
            <div className="bg-white rounded-lg p-3 border-2 border-gray-200 hover:border-gray-400 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="bg-gradient-to-br from-gray-500 to-gray-600 text-white px-3 py-2 rounded-lg font-bold text-sm shadow-md">
                    R$ 2
                  </div>
                  <input
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    value={notas.n2}
                    onChange={(e) => atualizarQuantidadeNota("n2", e.target.value)}
                    className="w-20 px-3 py-2 border-2 border-gray-300 rounded-lg text-center font-bold text-lg focus:border-gray-500 focus:ring-2 focus:ring-gray-200"
                    placeholder=""
                  />
                  <span className="text-xs text-gray-500">×</span>
                </div>
                <span className="text-lg font-bold text-gray-600">
                  R$ {((parseInt(notas.n2) || 0) * 2).toFixed(2)}
                </span>
              </div>
            </div>

            {/* Notas de R$ 5 */}
            <div className="bg-white rounded-lg p-3 border-2 border-purple-200 hover:border-purple-400 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="bg-gradient-to-br from-purple-500 to-purple-600 text-white px-3 py-2 rounded-lg font-bold text-sm shadow-md">
                    R$ 5
                  </div>
                  <input
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    value={notas.n5}
                    onChange={(e) => atualizarQuantidadeNota("n5", e.target.value)}
                    className="w-20 px-3 py-2 border-2 border-gray-300 rounded-lg text-center font-bold text-lg focus:border-purple-500 focus:ring-2 focus:ring-purple-200"
                    placeholder=""
                  />
                  <span className="text-xs text-gray-500">×</span>
                </div>
                <span className="text-lg font-bold text-purple-600">
                  R$ {((parseInt(notas.n5) || 0) * 5).toFixed(2)}
                </span>
              </div>
            </div>

            {/* Notas de R$ 10 */}
            <div className="bg-white rounded-lg p-3 border-2 border-red-200 hover:border-red-400 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="bg-gradient-to-br from-red-500 to-red-600 text-white px-3 py-2 rounded-lg font-bold text-sm shadow-md">
                    R$ 10
                  </div>
                  <input
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    value={notas.n10}
                    onChange={(e) => atualizarQuantidadeNota("n10", e.target.value)}
                    className="w-20 px-3 py-2 border-2 border-gray-300 rounded-lg text-center font-bold text-lg focus:border-red-500 focus:ring-2 focus:ring-red-200"
                    placeholder=""
                  />
                  <span className="text-xs text-gray-500">×</span>
                </div>
                <span className="text-lg font-bold text-red-600">
                  R$ {((parseInt(notas.n10) || 0) * 10).toFixed(2)}
                </span>
              </div>
            </div>

            {/* Notas de R$ 20 */}
            <div className="bg-white rounded-lg p-3 border-2 border-yellow-200 hover:border-yellow-400 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="bg-gradient-to-br from-yellow-500 to-yellow-600 text-white px-3 py-2 rounded-lg font-bold text-sm shadow-md">
                    R$ 20
                  </div>
                  <input
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    value={notas.n20}
                    onChange={(e) => atualizarQuantidadeNota("n20", e.target.value)}
                    className="w-20 px-3 py-2 border-2 border-gray-300 rounded-lg text-center font-bold text-lg focus:border-yellow-500 focus:ring-2 focus:ring-yellow-200"
                    placeholder=""
                  />
                  <span className="text-xs text-gray-500">×</span>
                </div>
                <span className="text-lg font-bold text-yellow-600">
                  R$ {((parseInt(notas.n20) || 0) * 20).toFixed(2)}
                </span>
              </div>
            </div>

            {/* Notas de R$ 50 */}
            <div className="bg-white rounded-lg p-3 border-2 border-blue-200 hover:border-blue-400 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="bg-gradient-to-br from-blue-500 to-blue-600 text-white px-3 py-2 rounded-lg font-bold text-sm shadow-md">
                    R$ 50
                  </div>
                  <input
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    value={notas.n50}
                    onChange={(e) => atualizarQuantidadeNota("n50", e.target.value)}
                    className="w-20 px-3 py-2 border-2 border-gray-300 rounded-lg text-center font-bold text-lg focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                    placeholder=""
                  />
                  <span className="text-xs text-gray-500">×</span>
                </div>
                <span className="text-lg font-bold text-blue-600">
                  R$ {((parseInt(notas.n50) || 0) * 50).toFixed(2)}
                </span>
              </div>
            </div>

            {/* Notas de R$ 100 */}
            <div className="bg-white rounded-lg p-3 border-2 border-green-200 hover:border-green-400 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="bg-gradient-to-br from-green-500 to-green-600 text-white px-3 py-2 rounded-lg font-bold text-sm shadow-md">
                    R$ 100
                  </div>
                  <input
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    value={notas.n100}
                    onChange={(e) => atualizarQuantidadeNota("n100", e.target.value)}
                    className="w-20 px-3 py-2 border-2 border-gray-300 rounded-lg text-center font-bold text-lg focus:border-green-500 focus:ring-2 focus:ring-green-200"
                    placeholder=""
                  />
                  <span className="text-xs text-gray-500">×</span>
                </div>
                <span className="text-lg font-bold text-green-600">
                  R$ {((parseInt(notas.n100) || 0) * 100).toFixed(2)}
                </span>
              </div>
            </div>
          </div>

          {/* Moedas */}
          <div className="mt-4 pt-4 border-t-2 border-blue-300">
            <div className="bg-white rounded-lg p-4 border-2 border-amber-200 hover:border-amber-400 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="bg-gradient-to-br from-amber-500 to-amber-600 text-white px-3 py-2 rounded-lg font-bold text-sm shadow-md">
                    💰 Moedas
                  </div>
                  <CurrencyInput
                    value={notas.moedas}
                    onChange={atualizarValorMoedas}
                    className="w-32 px-3 py-2 border-2 border-gray-300 rounded-lg text-center font-bold text-lg focus:border-amber-500 focus:ring-2 focus:ring-amber-200"
                    aria-label="Valor das moedas"
                  />
                </div>
                <span className="text-lg font-bold text-amber-600">
                  R$ {formatBRL(notas.moedas)}
                </span>
              </div>
            </div>
          </div>

          {/* Total e Botões */}
          <div className="mt-5 pt-5 border-t-2 border-blue-300">
            <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl p-4 mb-4 shadow-lg">
              <div className="flex items-center justify-between">
                <span className="text-white font-semibold text-sm">TOTAL CONTADO</span>
                <span className="text-3xl font-bold text-white">
                  R$ {formatBRL(calcularTotalNotas())}
                </span>
              </div>
            </div>
            <div className="flex space-x-3">
              <button
                type="button"
                onClick={limparContagem}
                className="flex-1 px-4 py-3 border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-semibold transition-colors"
              >
                🗑️ Limpar
              </button>
              <button
                type="button"
                onClick={aplicarContagem}
                className="flex-1 px-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg hover:from-blue-700 hover:to-indigo-700 font-bold shadow-md transition-all"
              >
                ✓ Aplicar
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export function PaymentBreakdownPanel({
  carregarVendasForma,
  formaExpandida,
  loadingVendas,
  resumo,
  setFormaExpandida,
  vendasDetalhe,
}) {
  const [imprimindo, setImprimindo] = useState(false);
  const formas = Object.entries(resumo.vendas_por_forma_pagamento || {});
  const itensResumo = [
    ["Total vendido", resumo.total_vendido],
    ["Total recebido", resumo.total_recebido],
    ["Valor de abertura", resumo.caixa.valor_abertura],
    ["Suprimentos", resumo.totais.suprimentos],
    ["Sangria", resumo.totais.sangrias],
    ["Devoluções", resumo.totais.devolucoes],
    ["Despesas", resumo.totais.despesas],
  ];
  const recebimentosPorData = Object.entries(resumo.recebimentos_por_data_venda || {}).sort(
    ([dataA], [dataB]) => dataB.localeCompare(dataA),
  );
  const rotuloData = (data) =>
    data === "sem_venda" ? "Sem venda vinculada" : data.split("-").reverse().join("/");
  const totalPorData = (formasDoDia) =>
    Object.values(formasDoDia).reduce((total, dados) => total + dados.total, 0);

  useEffect(() => {
    if (!imprimindo) return undefined;

    document.body.classList.add("imprimindo-formas-caixa");
    const finalizar = () => setImprimindo(false);
    window.addEventListener("afterprint", finalizar);
    const frame = requestAnimationFrame(() => window.print());

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("afterprint", finalizar);
      document.body.classList.remove("imprimindo-formas-caixa");
    };
  }, [imprimindo]);

  return (
    <>
      <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-4 border border-blue-200">
        <div className="flex items-center justify-between gap-2 mb-3">
          <h4 className="text-sm font-bold text-gray-700 flex items-center">
            <Receipt className="w-4 h-4 mr-1.5 text-blue-600" />
            Resumo do Caixa
          </h4>
          <button
            type="button"
            onClick={() => setImprimindo(true)}
            className="inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold text-blue-700 bg-white border border-blue-300 rounded hover:bg-blue-50"
            title="Imprimir resumo do caixa e formas de pagamento"
          >
            <Printer className="w-4 h-4" />
            Imprimir
          </button>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {itensResumo.map(([titulo, valor]) => (
            <div key={titulo} className="bg-white rounded-lg p-3 border border-gray-200">
              <div className="text-xs font-semibold text-gray-700">{titulo}</div>
              <div className="mt-1 text-sm font-bold text-gray-900">{formatMoneyBRL(valor)}</div>
            </div>
          ))}
        </div>

        <h5 className="mt-4 mb-2 text-sm font-bold text-gray-700">Formas de Pagamento</h5>
        <div className="grid grid-cols-2 gap-2">
          {formas.map(([forma, dados]) => {
            const ehDinheiro = forma === "Dinheiro";
            return (
              <div
                key={forma}
                className={`bg-white rounded-lg p-3 border ${
                  formaExpandida === forma
                    ? "border-blue-400 bg-blue-50 shadow-md"
                    : ehDinheiro
                      ? "border-green-300 bg-green-50"
                      : "border-gray-200"
                } hover:shadow-sm transition-shadow cursor-pointer select-none`}
                title="Clique para ver detalhes dos recebimentos"
                onClick={() => carregarVendasForma(forma)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <div
                        className={`w-2 h-2 rounded-full ${
                          forma === "Dinheiro"
                            ? "bg-green-500"
                            : forma === "PIX"
                              ? "bg-purple-500"
                              : forma.includes("Débito")
                                ? "bg-blue-500"
                                : forma.includes("Crédito")
                                  ? "bg-orange-500"
                                  : "bg-gray-400"
                        }`}
                      ></div>
                      <span className="text-xs font-semibold text-gray-700">{forma}</span>
                      {ehDinheiro && (
                        <span className="text-xs bg-green-600 text-white px-1.5 py-0.5 rounded">
                          CAIXA
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {dados.quantidade} {dados.tipo_contagem || "pagamento"}
                      {dados.quantidade !== 1 ? "s" : ""}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-bold text-gray-900">
                      {formatMoneyBRL(dados.total)}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
          {formas.length === 0 && (
            <p className="col-span-2 text-xs text-gray-600">Nenhum pagamento registrado.</p>
          )}
        </div>

        {recebimentosPorData.length > 0 && (
          <details className="mt-3 rounded border border-blue-200 bg-white px-3 py-2 text-xs">
            <summary className="cursor-pointer font-semibold text-blue-800">
              Conferir por data da venda
            </summary>
            <p className="mt-2 text-gray-600">
              O total do caixa pode incluir pagamentos de vendas feitas em outras datas.
            </p>
            <div className="mt-2 space-y-2">
              {recebimentosPorData.map(([data, formasDoDia]) => (
                <div key={data} className="rounded border border-gray-200 p-2">
                  <div className="flex justify-between font-bold text-gray-800">
                    <span>{rotuloData(data)}</span>
                    <span>{formatMoneyBRL(totalPorData(formasDoDia))}</span>
                  </div>
                  {Object.entries(formasDoDia).map(([forma, dados]) => (
                    <div key={forma} className="flex justify-between text-gray-600">
                      <span>
                        {forma} · {dados.quantidade}
                      </span>
                      <span>{formatMoneyBRL(dados.total)}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </details>
        )}

        {/* Painel de detalhes dos recebimentos por forma */}
        {formaExpandida && (
          <div className="mt-3 border-t border-blue-200 pt-3">
            <div className="flex items-center justify-between mb-2">
              <h5 className="text-xs font-bold text-gray-700">Recebimentos — {formaExpandida}</h5>
              <button
                onClick={() => setFormaExpandida(null)}
                className="text-xs text-gray-400 hover:text-gray-600"
              >
                ✕ fechar
              </button>
            </div>
            {loadingVendas === formaExpandida ? (
              <div className="text-xs text-gray-500 py-2">Carregando...</div>
            ) : (
              <div className="space-y-1 max-h-44 overflow-y-auto">
                {(vendasDetalhe[formaExpandida] || []).length === 0 ? (
                  <div className="text-xs text-gray-400">Nenhuma venda encontrada.</div>
                ) : (
                  (vendasDetalhe[formaExpandida] || []).map((v) => (
                    <div
                      key={v.id}
                      className="flex justify-between items-center text-xs py-1.5 px-2 rounded bg-white border border-gray-100"
                    >
                      <div>
                        <SaleReference
                          sale={v}
                          showPrefix={false}
                          valueClassName="font-semibold text-gray-700"
                        />
                        <CustomerIdentity
                          className="ml-1.5"
                          fallback="Consumidor"
                          layout="inline"
                          nameClassName="text-gray-500"
                          venda={v}
                        />
                      </div>
                      <div className="text-right">
                        <span className="text-gray-400 mr-2">
                          {v.data_venda ? `${rotuloData(v.data_venda)} ` : ""}
                          {v.hora_venda}
                        </span>
                        <span className="font-bold text-gray-800">
                          {formatMoneyBRL(v.valor_nesta_forma ?? v.total)}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        )}

        <div className="mt-3 pt-3 border-t border-blue-200 text-xs text-gray-600">
          💡 <strong>Dica:</strong> Apenas <strong>Dinheiro</strong> afeta o saldo físico do caixa.
          As demais formas são informativas.
        </div>
      </div>
      {imprimindo &&
        createPortal(
          <div id="caixa-formas-impressao">
            <style>{`
            @media screen { #caixa-formas-impressao { display: none; } }
            @media print {
              @page { margin: 2mm; }
              body.imprimindo-formas-caixa > :not(#caixa-formas-impressao) { display: none !important; }
              #caixa-formas-impressao {
                display: block !important;
                box-sizing: border-box;
                width: 100%;
                max-width: 72mm;
                color: #111;
                font: 10pt/1.3 Arial, sans-serif;
              }
              #caixa-formas-impressao h1 { font-size: 12pt; margin: 0 0 2mm; }
              #caixa-formas-impressao h2 { font-size: 10pt; margin: 3mm 0 1mm; }
              #caixa-formas-impressao p { margin: 2mm 0; overflow-wrap: anywhere; }
              #caixa-formas-impressao .linha {
                display: flex;
                justify-content: space-between;
                gap: 2mm;
                border-bottom: 1px solid #bbb;
                padding: 1mm 0;
                break-inside: avoid;
              }
              #caixa-formas-impressao .linha span { flex: 1; min-width: 0; overflow-wrap: anywhere; }
              #caixa-formas-impressao .linha strong { flex-shrink: 0; white-space: nowrap; }
              #caixa-formas-impressao .grupo-data { break-inside: avoid; }
            }
          `}</style>
            <h1>Resumo do caixa</h1>
            <div>
              Caixa #{resumo.caixa.numero_caixa} — {resumo.caixa.usuario_nome}
            </div>
            <div>Abertura: {new Date(resumo.caixa.data_abertura).toLocaleString("pt-BR")}</div>
            {itensResumo.map(([titulo, valor]) => (
              <div className="linha" key={titulo}>
                <span>{titulo}</span>
                <strong>{formatMoneyBRL(valor)}</strong>
              </div>
            ))}
            <h2>Formas de pagamento</h2>
            {formas.map(([forma, dados]) => (
              <div className="linha" key={forma}>
                <span>
                  {forma} · {dados.quantidade} {dados.tipo_contagem || "pagamento"}
                  {dados.quantidade !== 1 ? "s" : ""}
                </span>
                <strong>{formatMoneyBRL(dados.total)}</strong>
              </div>
            ))}
            {recebimentosPorData.length > 0 && (
              <>
                <h2>Conferência por data da venda</h2>
                {recebimentosPorData.map(([data, formasDoDia]) => (
                  <div className="grupo-data" key={data}>
                    <div className="linha">
                      <strong>{rotuloData(data)}</strong>
                      <strong>{formatMoneyBRL(totalPorData(formasDoDia))}</strong>
                    </div>
                    {Object.entries(formasDoDia).map(([forma, dados]) => (
                      <div className="linha" key={forma}>
                        <span>
                          {forma} · {dados.quantidade}
                        </span>
                        <strong>{formatMoneyBRL(dados.total)}</strong>
                      </div>
                    ))}
                  </div>
                ))}
              </>
            )}
            <p>
              Dinheiro corresponde às entradas registradas no extrato deste caixa. As demais formas
              não afetam o saldo físico.
            </p>
          </div>,
          document.body,
        )}
    </>
  );
}

export function DifferenceTipsModal({
  diferenca,
  mostrarDicasDiferenca,
  resumo,
  setMostrarDicasDiferenca,
  valorContado,
}) {
  return (
    <>
      {/* Modal de Dicas de Diferença */}
      {mostrarDicasDiferenca && (
        <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-[60] p-4">
          <div className="bg-white rounded-xl w-full max-w-lg max-h-[85vh] overflow-y-auto shadow-2xl">
            <div
              className={`p-5 rounded-t-xl text-white ${diferenca > 0 ? "bg-blue-600" : "bg-yellow-600"}`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-bold">
                    {diferenca > 0 ? "💰 Sobrou dinheiro no caixa" : "⚠️ Faltou dinheiro no caixa"}
                  </h3>
                  <p className="text-sm opacity-90 mt-0.5">
                    Diferença de R$ {Math.abs(diferenca).toFixed(2)} — possíveis causas
                  </p>
                </div>
                <button
                  onClick={() => setMostrarDicasDiferenca(false)}
                  className="p-1 hover:bg-white hover:bg-opacity-20 rounded-lg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="p-5 space-y-4">
              {diferenca < 0 ? (
                // FALTOU dinheiro
                <>
                  <p className="text-sm text-gray-600">
                    O caixa deveria ter{" "}
                    <strong>R$ {(resumo?.totais?.saldo_atual ?? 0).toFixed(2)}</strong>, mas você
                    contou <strong>R$ {valorContado.toFixed(2)}</strong>. Alguém saiu com dinheiro
                    que não foi registrado, ou houve um erro de registro. Veja as causas mais
                    comuns:
                  </p>

                  <div className="space-y-3">
                    <div className="border border-yellow-200 bg-yellow-50 rounded-lg p-3">
                      <div className="font-semibold text-yellow-800 text-sm mb-1">
                        💸 Troco dado a mais
                      </div>
                      <div className="text-xs text-yellow-700">
                        O funcionário pode ter calculado errado o troco em alguma venda em dinheiro
                        e devolvido mais do que devia. Verifique as vendas em dinheiro do dia e
                        confira se os valores batem com o que foi recebido.
                      </div>
                    </div>

                    <div className="border border-yellow-200 bg-yellow-50 rounded-lg p-3">
                      <div className="font-semibold text-yellow-800 text-sm mb-1">
                        🏷️ Forma de pagamento lançada errada
                      </div>
                      <div className="text-xs text-yellow-700">
                        Uma venda pode ter sido registrada como "Dinheiro", mas o cliente pagou no
                        cartão ou PIX. Nesse caso, o caixa esperava receber aquele valor em espécie,
                        mas não recebeu. Verifique as vendas em dinheiro e confirme com o cliente ou
                        pelo extrato do maquininha.
                      </div>
                    </div>

                    <div className="border border-yellow-200 bg-yellow-50 rounded-lg p-3">
                      <div className="font-semibold text-yellow-800 text-sm mb-1">
                        📋 Despesa paga sem lançar no caixa
                      </div>
                      <div className="text-xs text-yellow-700">
                        Alguém pode ter pago uma despesa (fornecedor, frete, material) com o
                        dinheiro do caixa sem registrar como "Despesa". O dinheiro saiu fisicamente
                        mas o sistema não sabe. Pergunte à equipe se houve algum pagamento assim.
                      </div>
                    </div>

                    <div className="border border-yellow-200 bg-yellow-50 rounded-lg p-3">
                      <div className="font-semibold text-yellow-800 text-sm mb-1">
                        🔄 Sangria não registrada
                      </div>
                      <div className="text-xs text-yellow-700">
                        Dinheiro pode ter sido retirado do caixa sem passar pelo fluxo de Sangria no
                        sistema. Pergunte se alguém retirou dinheiro para troco ou outro fim sem
                        registrar.
                      </div>
                    </div>

                    <div className="border border-yellow-200 bg-yellow-50 rounded-lg p-3">
                      <div className="font-semibold text-yellow-800 text-sm mb-1">
                        🔢 Erro na contagem
                      </div>
                      <div className="text-xs text-yellow-700">
                        Recomendamos contar o dinheiro uma segunda vez, separando por cédula (R$
                        100, R$ 50, R$ 20, R$ 10, R$ 5, R$ 2) e somando as moedas por fim. Use o
                        auxiliar de contagem desta tela.
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                // SOBROU dinheiro
                <>
                  <p className="text-sm text-gray-600">
                    O caixa deveria ter{" "}
                    <strong>R$ {(resumo?.totais?.saldo_atual ?? 0).toFixed(2)}</strong>, mas você
                    contou <strong>R$ {valorContado.toFixed(2)}</strong>. Entrou mais dinheiro do
                    que foi registrado. Veja as causas mais comuns:
                  </p>

                  <div className="space-y-3">
                    <div className="border border-blue-200 bg-blue-50 rounded-lg p-3">
                      <div className="font-semibold text-blue-800 text-sm mb-1">
                        📥 Venda recebida mas não registrada
                      </div>
                      <div className="text-xs text-blue-700">
                        O cliente pagou em dinheiro, mas a venda não foi fechada no sistema. O
                        dinheiro entrou no caixa físico sem que o sistema soubesse. Verifique se há
                        vendas em aberto ou atendimentos que não foram finalizados.
                      </div>
                    </div>

                    <div className="border border-blue-200 bg-blue-50 rounded-lg p-3">
                      <div className="font-semibold text-blue-800 text-sm mb-1">
                        💳 Forma de pagamento lançada errada
                      </div>
                      <div className="text-xs text-blue-700">
                        Uma venda foi registrada como cartão ou PIX, mas o cliente pagou em
                        dinheiro. O sistema não contou esse valor como dinheiro no caixa. Confira as
                        vendas do dia e veja se todas as formas de pagamento foram registradas
                        corretamente.
                      </div>
                    </div>

                    <div className="border border-blue-200 bg-blue-50 rounded-lg p-3">
                      <div className="font-semibold text-blue-800 text-sm mb-1">
                        💰 Troco dado a menos
                      </div>
                      <div className="text-xs text-blue-700">
                        O funcionário pode ter devolvido menos troco do que devia em alguma venda. O
                        dinheiro ficou no caixa, mas o cliente levou menos do que era correto. Vale
                        revisar as vendas com pagamento em dinheiro.
                      </div>
                    </div>

                    <div className="border border-blue-200 bg-blue-50 rounded-lg p-3">
                      <div className="font-semibold text-blue-800 text-sm mb-1">
                        📋 Suprimento não registrado
                      </div>
                      <div className="text-xs text-blue-700">
                        Alguém pode ter colocado dinheiro no caixa (para troco ou reforço) sem
                        registrar como Suprimento no sistema. Pergunte se houve alguma entrada de
                        dinheiro que não foi registrada.
                      </div>
                    </div>

                    <div className="border border-blue-200 bg-blue-50 rounded-lg p-3">
                      <div className="font-semibold text-blue-800 text-sm mb-1">
                        🔢 Erro na contagem
                      </div>
                      <div className="text-xs text-blue-700">
                        Recomendamos contar o dinheiro uma segunda vez, separando por cédula (R$
                        100, R$ 50, R$ 20, R$ 10, R$ 5, R$ 2) e somando as moedas por fim. Use o
                        auxiliar de contagem desta tela.
                      </div>
                    </div>
                  </div>
                </>
              )}

              <div className="pt-3 border-t">
                <button
                  onClick={() => setMostrarDicasDiferenca(false)}
                  className="w-full px-4 py-3 bg-gray-800 hover:bg-gray-900 text-white rounded-lg font-semibold transition-colors"
                >
                  Entendi — voltar ao fechamento
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
