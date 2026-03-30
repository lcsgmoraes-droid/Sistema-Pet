import { Percent, Tag, X } from "lucide-react";
import { formatMoneyBRL } from "../../utils/formatters";

export default function PDVResumoFinanceiroCard({
  alertasCarrinho,
  codigoCupom,
  cupomAplicado,
  erroCupom,
  loadingCupom,
  modoVisualizacao,
  onAbrirModalDescontoTotal,
  onAplicarCupom,
  onCodigoCupomChange,
  onCodigoCupomKeyDown,
  onRemoverCupom,
  onRemoverDescontoTotal,
  totalImpostos,
  vendaAtual,
}) {
  const totalBruto = vendaAtual.subtotal + vendaAtual.desconto_valor;
  const saldoRestante = Math.max(0, vendaAtual.total - (vendaAtual.total_pago || 0));
  const descontoPercentualTexto =
    vendaAtual.desconto_valor > 0 && totalBruto > 0
      ? `${((vendaAtual.desconto_valor / totalBruto) * 100).toLocaleString(
          "pt-BR",
          {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          },
        )}% de desconto:`
      : "Desconto:";

  if (vendaAtual.itens.length === 0) {
    return null;
  }

  return (
    <>
      {alertasCarrinho.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 space-y-2">
          <p className="text-xs font-semibold text-amber-800 uppercase tracking-wide">
            Atenção - Carrinho
          </p>
          {alertasCarrinho.map((alerta, i) => (
            <div
              key={i}
              className={`flex items-start gap-2 text-sm rounded px-3 py-2 ${
                alerta.nivel === "critico"
                  ? "bg-red-100 text-red-800 border border-red-200"
                  : "bg-amber-100 text-amber-900 border border-amber-300"
              }`}
            >
              <span className="mt-0.5 shrink-0">
                {alerta.nivel === "critico" ? "🚨" : "⚠️"}
              </span>
              <span>{alerta.mensagem}</span>
            </div>
          ))}
        </div>
      )}

      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="space-y-3">
          <div className="flex justify-between text-gray-600">
            <span>Total bruto:</span>
            <span className="font-medium">{formatMoneyBRL(totalBruto)}</span>
          </div>

          {!modoVisualizacao && (
            <div className="border rounded-lg p-3 bg-purple-50 border-purple-200">
              <div className="flex items-center gap-1 mb-2">
                <Tag className="w-3.5 h-3.5 text-purple-600" />
                <span className="text-xs font-medium text-purple-700">
                  Cupom de desconto
                </span>
              </div>
              {cupomAplicado ? (
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-purple-800 bg-purple-100 px-2 py-0.5 rounded font-mono">
                      {cupomAplicado.code}
                    </span>
                    <span className="ml-2 text-xs text-green-700 font-medium">
                      - {formatMoneyBRL(cupomAplicado.discount_applied)}
                    </span>
                  </div>
                  <button
                    onClick={onRemoverCupom}
                    className="text-xs text-red-500 hover:text-red-700 flex items-center gap-0.5"
                    title="Remover cupom"
                  >
                    <X className="w-3 h-3" /> Remover
                  </button>
                </div>
              ) : (
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={codigoCupom}
                    onChange={(e) => onCodigoCupomChange(e.target.value)}
                    onKeyDown={onCodigoCupomKeyDown}
                    placeholder="Ex: FIDE-XK92P3"
                    className="flex-1 text-xs px-2 py-1.5 border border-purple-300 rounded focus:outline-none focus:border-purple-500 bg-white font-mono uppercase"
                    disabled={loadingCupom}
                  />
                  <button
                    onClick={onAplicarCupom}
                    disabled={loadingCupom || !codigoCupom.trim()}
                    className="px-3 py-1.5 text-xs bg-purple-600 hover:bg-purple-700 text-white rounded font-medium disabled:opacity-50 transition-colors"
                  >
                    {loadingCupom ? "..." : "Aplicar"}
                  </button>
                </div>
              )}
              {erroCupom && (
                <p className="text-xs text-red-600 mt-1">{erroCupom}</p>
              )}
            </div>
          )}

          <div className="flex justify-between items-center">
            <span
              className={
                vendaAtual.desconto_valor > 0
                  ? "text-orange-600 text-sm"
                  : "text-gray-500 text-sm"
              }
            >
              {descontoPercentualTexto}
            </span>
            <div className="flex items-center gap-2">
              {vendaAtual.desconto_valor > 0 && (
                <span className="font-medium text-orange-600 text-sm">
                  - {formatMoneyBRL(vendaAtual.desconto_valor)}
                </span>
              )}
              {!cupomAplicado && (
                <button
                  onClick={onAbrirModalDescontoTotal}
                  disabled={modoVisualizacao}
                  className="flex items-center gap-1 px-2 py-1 text-xs text-blue-600 hover:bg-blue-50 rounded border border-blue-200 disabled:opacity-50 transition-colors"
                  title="Aplicar desconto no total da venda"
                >
                  <Percent className="w-3 h-3" />
                  <span>{vendaAtual.desconto_valor > 0 ? "Editar" : "Adicionar"}</span>
                </button>
              )}
              {vendaAtual.desconto_valor > 0 && !cupomAplicado && (
                <button
                  onClick={onRemoverDescontoTotal}
                  disabled={modoVisualizacao}
                  className="p-1 text-red-400 hover:bg-red-50 rounded disabled:opacity-50 transition-colors"
                  title="Remover desconto"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>

          <div className="flex justify-between text-gray-600">
            <span>Total:</span>
            <span className="font-medium">{formatMoneyBRL(vendaAtual.subtotal)}</span>
          </div>

          {vendaAtual.tem_entrega && (
            <div className="flex justify-between text-blue-600">
              <span>Taxa de Entrega:</span>
              <span className="font-medium">
                + {formatMoneyBRL(vendaAtual.entrega?.taxa_entrega_total || 0)}
              </span>
            </div>
          )}

          <div className="border-t pt-3">
            <div className="flex justify-between text-lg font-bold text-gray-900">
              <span>Total da Venda:</span>
              <span>{formatMoneyBRL(vendaAtual.total)}</span>
            </div>
          </div>

          {totalImpostos > 0 && (
            <div className="flex justify-between text-sm text-blue-600 bg-blue-50 p-2 rounded">
              <span className="font-medium">Total de Impostos:</span>
              <span className="font-semibold">R$ {totalImpostos}</span>
            </div>
          )}

          {vendaAtual.total_pago > 0 && (
            <>
              <div className="flex justify-between text-green-600 border-t pt-3">
                <span className="font-medium">(-) Valor Pago:</span>
                <span className="font-semibold">
                  {formatMoneyBRL(vendaAtual.total_pago)}
                </span>
              </div>

              <div className="flex justify-between text-2xl font-bold border-t-2 pt-3">
                <span
                  className={
                    vendaAtual.total - vendaAtual.total_pago > 0
                      ? "text-orange-600"
                      : "text-green-600"
                  }
                >
                  {vendaAtual.total - vendaAtual.total_pago > 0
                    ? "Saldo Restante:"
                    : "Totalmente Pago:"}
                </span>
                <span
                  className={
                    vendaAtual.total - vendaAtual.total_pago > 0
                      ? "text-orange-600"
                      : "text-green-600"
                  }
                >
                  {formatMoneyBRL(saldoRestante)}
                </span>
              </div>
            </>
          )}

          {!vendaAtual.total_pago && (
            <div className="border-t pt-3">
              <div className="flex justify-between text-2xl font-bold text-gray-900">
                <span>Total:</span>
                <span className="text-green-600">
                  {formatMoneyBRL(vendaAtual.total)}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
