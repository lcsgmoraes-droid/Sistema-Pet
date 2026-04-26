export default function NovaInternacaoBaiasSection({
  formNova,
  mapaInternacao,
  setFormNova,
  setTotalBaias,
  totalBaias,
}) {
  return (
    <div>
      <div className="flex items-end justify-between mb-2">
        <label className="block text-xs font-medium text-gray-600">Mapa de baias (selecione uma livre) *</label>
        <div className="w-28">
          <input
            type="number"
            min="1"
            max="200"
            value={totalBaias}
            onChange={(event) => {
              const valor = Number.parseInt(event.target.value || "0", 10);
              if (!Number.isFinite(valor)) return;
              setTotalBaias(Math.max(1, Math.min(200, valor)));
            }}
            className="w-full border border-gray-200 rounded-lg px-2 py-1 text-xs"
            title="Total de baias"
          />
        </div>
      </div>
      <div className="border border-gray-200 rounded-lg p-2 max-h-44 overflow-auto">
        <div className="grid grid-cols-3 gap-2">
          {mapaInternacao
            .filter((baia) => Number.isFinite(Number.parseInt(String(baia.numero), 10)))
            .sort((a, b) => Number(a.numero) - Number(b.numero))
            .map((baia) => (
              <BaiaButton
                key={`nova_baia_${baia.numero}`}
                baia={baia}
                formNova={formNova}
                setFormNova={setFormNova}
              />
            ))}
        </div>
      </div>
      <p className="text-xs mt-1 text-gray-500">
        Selecionada: <span className="font-semibold text-gray-800">{formNova.box || "nenhuma"}</span>
      </p>
    </div>
  );
}

function BaiaButton({ baia, formNova, setFormNova }) {
  const numero = String(baia.numero);
  const ocupadaPorOutro = baia.ocupada;
  const selecionada = formNova.box === numero;

  return (
    <button
      type="button"
      disabled={ocupadaPorOutro}
      onClick={() => setFormNova((prev) => ({ ...prev, box: numero }))}
      className={`rounded-md border px-2 py-2 text-left transition-colors ${
        ocupadaPorOutro
          ? "bg-red-50 border-red-200 text-red-700 cursor-not-allowed"
          : selecionada
          ? "bg-purple-600 border-purple-600 text-white"
          : "bg-emerald-50 border-emerald-200 text-emerald-700 hover:bg-emerald-100"
      }`}
    >
      <p className="text-xs font-bold">Baia {numero}</p>
      <p className="text-[11px] truncate">
        {ocupadaPorOutro ? (baia.internacao?.pet_nome ?? "Ocupada") : "Disponivel"}
      </p>
    </button>
  );
}
