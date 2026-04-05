import { formatBRL } from "../../utils/formatters";

function getCategoriaLabel(categoria) {
  return categoria === "maior_gasto" ? "Maior Gasto" : "Mais Compras";
}

export default function CampanhasDestaqueVencedorCard({
  categoria,
  info,
  premio,
  selecionado,
  onToggleSelecionado,
  onPremioChange,
}) {
  const usandoMensagem = premio.tipo_premio === "mensagem";

  return (
    <div
      className={`bg-gradient-to-br from-amber-50 to-yellow-50 border rounded-xl p-4 space-y-3 transition-opacity ${
        selecionado
          ? "border-amber-200 opacity-100"
          : "border-gray-200 opacity-50"
      }`}
    >
      <div className="flex items-center justify-between">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={selecionado}
            onChange={(e) => onToggleSelecionado(e.target.checked)}
            className="w-4 h-4 accent-amber-500"
          />
          <p className="text-xs font-semibold text-amber-600 uppercase">
            {getCategoriaLabel(categoria)}
          </p>
        </label>

        <div className="flex gap-1">
          <button
            onClick={() => onPremioChange({ tipo_premio: "cupom" })}
            className={`px-2 py-0.5 rounded text-xs font-medium border transition-colors ${
              !usandoMensagem
                ? "bg-amber-500 text-white border-amber-500"
                : "bg-white text-gray-600 border-gray-200 hover:border-amber-300"
            }`}
          >
            Cupom
          </button>
          <button
            onClick={() => onPremioChange({ tipo_premio: "mensagem" })}
            className={`px-2 py-0.5 rounded text-xs font-medium border transition-colors ${
              usandoMensagem
                ? "bg-amber-500 text-white border-amber-500"
                : "bg-white text-gray-600 border-gray-200 hover:border-amber-300"
            }`}
          >
            Brinde
          </button>
        </div>
      </div>

      <div>
        <p className="font-bold text-gray-900">{info.nome}</p>
        <p className="text-sm text-gray-600">
          {categoria === "maior_gasto"
            ? `R$ ${formatBRL(info.total_spent)} gastos`
            : `${info.total_purchases} compra(s)`}
        </p>
      </div>

      {!usandoMensagem ? (
        <div className="space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs text-gray-500 block mb-1">
                Valor do cupom (R$)
              </label>
              <input
                type="number"
                min="1"
                step="0.01"
                value={premio.coupon_value ?? 50}
                onChange={(e) =>
                  onPremioChange({
                    coupon_value: Number.parseFloat(e.target.value) || 0,
                  })
                }
                className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-300"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">
                Validade (dias)
              </label>
              <input
                type="number"
                min="1"
                value={premio.coupon_valid_days ?? 10}
                onChange={(e) =>
                  onPremioChange({
                    coupon_valid_days:
                      Number.parseInt(e.target.value, 10) || 1,
                  })
                }
                className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-300"
              />
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">
              Mensagem ao cliente
            </label>
            <input
              type="text"
              value={premio.mensagem ?? ""}
              onChange={(e) => onPremioChange({ mensagem: e.target.value })}
              placeholder="Ex: Parabens! Use este cupom em sua proxima visita"
              className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-300"
            />
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          <div>
            <label className="text-xs text-gray-500 block mb-1">
              Mensagem ao cliente
            </label>
            <textarea
              rows={3}
              value={premio.mensagem_brinde ?? ""}
              onChange={(e) =>
                onPremioChange({ mensagem_brinde: e.target.value })
              }
              className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-300 resize-none"
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs text-gray-500 block mb-1">
                Retirada a partir de
              </label>
              <input
                type="date"
                value={premio.retirar_de ?? ""}
                onChange={(e) => onPremioChange({ retirar_de: e.target.value })}
                className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-300"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">
                Retirada ate
              </label>
              <input
                type="date"
                value={premio.retirar_ate ?? ""}
                onChange={(e) =>
                  onPremioChange({ retirar_ate: e.target.value })
                }
                className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-300"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
