export default function CampanhasCupomManualModal({
  modalCupomAberto,
  setModalCupomAberto,
  setErroCupom,
  novoCupom,
  setNovoCupom,
  erroCupom,
  criarCupomManual,
  criandoCupom,
}) {
  if (!modalCupomAberto) return null;

  const fechar = () => {
    setModalCupomAberto(false);
    setErroCupom("");
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <h3 className="font-semibold text-gray-900">Criar cupom manual</h3>
          <button
            onClick={fechar}
            className="text-gray-400 hover:text-gray-600 text-xl"
          >
            x
          </button>
        </div>
        <div className="px-6 py-4 space-y-3">
          <div>
            <label
              htmlFor="cupom-tipo"
              className="block text-xs font-medium text-gray-600 mb-1"
            >
              Tipo de desconto
            </label>
            <select
              id="cupom-tipo"
              value={novoCupom.coupon_type}
              onChange={(e) =>
                setNovoCupom((p) => ({ ...p, coupon_type: e.target.value }))
              }
              className="w-full border rounded-lg px-3 py-2 text-sm"
            >
              <option value="fixed">Valor fixo (R$)</option>
              <option value="percent">Percentual (%)</option>
              <option value="gift">Brinde (sem valor)</option>
            </select>
          </div>
          {novoCupom.coupon_type === "fixed" && (
            <div>
              <label
                htmlFor="cupom-valor"
                className="block text-xs font-medium text-gray-600 mb-1"
              >
                Valor do desconto (R$)
              </label>
              <input
                id="cupom-valor"
                type="text"
                placeholder="Ex: 20,00"
                value={novoCupom.discount_value}
                onChange={(e) =>
                  setNovoCupom((p) => ({
                    ...p,
                    discount_value: e.target.value,
                  }))
                }
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
          )}
          {novoCupom.coupon_type === "percent" && (
            <div>
              <label
                htmlFor="cupom-pct"
                className="block text-xs font-medium text-gray-600 mb-1"
              >
                Percentual (%)
              </label>
              <input
                id="cupom-pct"
                type="number"
                min="1"
                max="100"
                placeholder="Ex: 10"
                value={novoCupom.discount_percent}
                onChange={(e) =>
                  setNovoCupom((p) => ({
                    ...p,
                    discount_percent: e.target.value,
                  }))
                }
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
          )}
          <div>
            <label
              htmlFor="cupom-canal"
              className="block text-xs font-medium text-gray-600 mb-1"
            >
              Canal
            </label>
            <select
              id="cupom-canal"
              value={novoCupom.channel}
              onChange={(e) =>
                setNovoCupom((p) => ({ ...p, channel: e.target.value }))
              }
              className="w-full border rounded-lg px-3 py-2 text-sm"
            >
              <option value="pdv">PDV (caixa)</option>
              <option value="ecommerce">E-commerce</option>
              <option value="app">App</option>
            </select>
          </div>
          <div>
            <label
              htmlFor="cupom-validade"
              className="block text-xs font-medium text-gray-600 mb-1"
            >
              Valido ate (opcional)
            </label>
            <input
              id="cupom-validade"
              type="date"
              value={novoCupom.valid_until}
              onChange={(e) =>
                setNovoCupom((p) => ({ ...p, valid_until: e.target.value }))
              }
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label
              htmlFor="cupom-mincompra"
              className="block text-xs font-medium text-gray-600 mb-1"
            >
              Compra minima (R$, opcional)
            </label>
            <input
              id="cupom-mincompra"
              type="text"
              placeholder="Ex: 50,00"
              value={novoCupom.min_purchase_value}
              onChange={(e) =>
                setNovoCupom((p) => ({
                  ...p,
                  min_purchase_value: e.target.value,
                }))
              }
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label
              htmlFor="cupom-cliente"
              className="block text-xs font-medium text-gray-600 mb-1"
            >
              ID do cliente (opcional)
            </label>
            <input
              id="cupom-cliente"
              type="number"
              placeholder="Deixe vazio para cupom generico"
              value={novoCupom.customer_id}
              onChange={(e) =>
                setNovoCupom((p) => ({ ...p, customer_id: e.target.value }))
              }
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label
              htmlFor="cupom-descricao"
              className="block text-xs font-medium text-gray-600 mb-1"
            >
              Descricao (opcional)
            </label>
            <input
              id="cupom-descricao"
              type="text"
              placeholder="Ex: Cupom de cortesia"
              value={novoCupom.descricao}
              onChange={(e) =>
                setNovoCupom((p) => ({ ...p, descricao: e.target.value }))
              }
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
          </div>
          {erroCupom && <p className="text-red-600 text-sm">{erroCupom}</p>}
        </div>
        <div className="px-6 py-4 border-t flex gap-3 justify-end">
          <button
            onClick={fechar}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200"
          >
            Cancelar
          </button>
          <button
            onClick={criarCupomManual}
            disabled={criandoCupom}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {criandoCupom ? "Criando..." : "Criar cupom"}
          </button>
        </div>
      </div>
    </div>
  );
}
