import CampanhasGestorSection from "./CampanhasGestorSection";

export default function CampanhasGestorCashbackSection({
  gestorSaldo,
  gestorSecao,
  setGestorSecao,
  formatBRL,
  gestorCashbackTipo,
  setGestorCashbackTipo,
  gestorCashbackValor,
  setGestorCashbackValor,
  gestorCashbackDesc,
  setGestorCashbackDesc,
  gestorLancandoCashback,
  ajustarCashbackGestor,
}) {
  const isOpen = gestorSecao === "cashback";

  return (
    <CampanhasGestorSection
      icon="💰"
      title="Cashback"
      subtitle={`Saldo: R$ ${formatBRL(gestorSaldo.saldo_cashback)}`}
      isOpen={isOpen}
      onToggle={() => setGestorSecao(isOpen ? null : "cashback")}
    >
      <div className="p-6 space-y-4">
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Saldo atual</p>
          <p className="text-3xl font-bold text-green-700">
            R$ {formatBRL(gestorSaldo.saldo_cashback)}
          </p>
        </div>

        <div
          className={`border rounded-lg p-4 space-y-3 ${
            gestorCashbackTipo === "debito"
              ? "bg-red-50 border-red-200"
              : "bg-blue-50 border-blue-200"
          }`}
        >
          <p className="text-sm font-medium text-gray-700">Ajuste manual</p>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Tipo
              </label>
              <select
                value={gestorCashbackTipo}
                onChange={(e) => setGestorCashbackTipo(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              >
                <option value="credito">Crédito (adicionar)</option>
                <option value="debito">Débito (remover)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Valor (R$)
              </label>
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={gestorCashbackValor}
                onChange={(e) => setGestorCashbackValor(e.target.value)}
                placeholder="0,00"
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>

            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Motivo (opcional)
              </label>
              <input
                type="text"
                value={gestorCashbackDesc}
                onChange={(e) => setGestorCashbackDesc(e.target.value)}
                placeholder="Ex: Correção de campanha"
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
          </div>

          <button
            onClick={ajustarCashbackGestor}
            disabled={gestorLancandoCashback || !gestorCashbackValor}
            className={`w-full py-2 rounded-lg text-sm font-medium text-white disabled:opacity-50 ${
              gestorCashbackTipo === "debito"
                ? "bg-red-600 hover:bg-red-700"
                : "bg-blue-600 hover:bg-blue-700"
            }`}
          >
            {gestorLancandoCashback
              ? "Salvando..."
              : gestorCashbackTipo === "debito"
                ? "Confirmar débito"
                : "Confirmar crédito"}
          </button>
        </div>
      </div>
    </CampanhasGestorSection>
  );
}
