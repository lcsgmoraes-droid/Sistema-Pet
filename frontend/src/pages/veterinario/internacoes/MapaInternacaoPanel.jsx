export default function MapaInternacaoPanel({
  mapaInternacao,
  totalBaias,
  setTotalBaias,
  onSelecionarInternacao,
}) {
  return (
    <div className="space-y-3">
      <div className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col md:flex-row md:items-end gap-3">
        <div>
          <p className="text-sm font-semibold text-gray-800">Mapa visual de baias</p>
          <p className="text-xs text-gray-500">Estilo assento: vermelho ocupado, verde disponível.</p>
        </div>
        <div className="md:ml-auto w-full md:w-56">
          <label className="block text-xs font-medium text-gray-600 mb-1">Total de baias no local</label>
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
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
          />
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6 gap-3">
          {mapaInternacao.map((baia) => {
            const ocupada = baia.ocupada;
            const internacao = baia.internacao;

            return (
              <div
                key={String(baia.numero)}
                onClick={() => {
                  if (!internacao?.id) return;
                  onSelecionarInternacao(internacao.id);
                }}
                className={`rounded-xl border p-3 min-h-[92px] transition-colors ${
                  ocupada
                    ? "border-red-300 bg-red-50"
                    : "border-emerald-300 bg-emerald-50"
                } ${ocupada ? "cursor-pointer hover:shadow-sm" : ""}`}
              >
                <p className={`text-sm font-bold ${ocupada ? "text-red-700" : "text-emerald-700"}`}>
                  Baia {baia.numero}
                </p>
                {ocupada ? (
                  <>
                    <p className="text-xs font-semibold text-gray-800 mt-2 truncate">
                      {internacao?.pet_nome ?? "Internado"}
                    </p>
                    <p className="text-[11px] text-gray-600 truncate">{internacao?.motivo ?? "Sem motivo"}</p>
                  </>
                ) : (
                  <p className="text-xs text-emerald-700 mt-2">Disponível</p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <p className="text-sm font-semibold text-gray-700 mb-2">Legenda</p>
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="px-2 py-1 rounded-full bg-red-100 text-red-700 border border-red-200">
            Baia ocupada
          </span>
          <span className="px-2 py-1 rounded-full bg-emerald-100 text-emerald-700 border border-emerald-200">
            Baia disponível
          </span>
        </div>
      </div>
    </div>
  );
}
