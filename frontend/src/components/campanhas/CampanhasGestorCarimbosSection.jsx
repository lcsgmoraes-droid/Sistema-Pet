import CampanhasGestorSection from "./CampanhasGestorSection";

export default function CampanhasGestorCarimbosSection({
  gestorSaldo,
  gestorSecao,
  setGestorSecao,
  gestorCarimboNota,
  setGestorCarimboNota,
  gestorLancandoCarimbo,
  lancarCarimboGestor,
  gestorCarimbos,
  gestorIncluirEstornados,
  setGestorIncluirEstornados,
  gestorRemovendo,
  estornarCarimboGestor,
}) {
  const isOpen = gestorSecao === "carimbos";

  return (
    <CampanhasGestorSection
      icon="\u{1F3F7}\uFE0F"
      title="Cartao Fidelidade"
      subtitle={`${gestorSaldo.total_carimbos} carimbo(s) ativo(s)`}
      isOpen={isOpen}
      onToggle={() => setGestorSecao(isOpen ? null : "carimbos")}
    >
      <div className="p-6 space-y-4">
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-sm font-medium text-green-800 mb-3">
            Lancar carimbo manual
          </p>
          <div className="flex gap-3 flex-wrap items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Observacao (opcional)
              </label>
              <input
                type="text"
                value={gestorCarimboNota}
                onChange={(e) => setGestorCarimboNota(e.target.value)}
                placeholder="Ex: Conversao de cartao fisico"
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <button
              onClick={lancarCarimboGestor}
              disabled={gestorLancandoCarimbo}
              className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
            >
              {gestorLancandoCarimbo ? "Lancando..." : "Lancar Carimbo"}
            </button>
          </div>
        </div>

        {gestorCarimbos && gestorCarimbos.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-600">
                    #ID
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-600">
                    Data
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-600">
                    Origem
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-600">
                    Obs
                  </th>
                  <th className="px-4 py-2 text-center text-xs font-medium text-gray-600">
                    Status
                  </th>
                  <th className="px-4 py-2 text-center text-xs font-medium text-gray-600">
                    Acao
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {gestorCarimbos
                  .filter(
                    (stamp) => !stamp.voided_at || gestorIncluirEstornados,
                  )
                  .map((stamp) => (
                    <tr
                      key={stamp.id}
                      className={
                        stamp.voided_at
                          ? "bg-red-50 opacity-60"
                          : "hover:bg-gray-50"
                      }
                    >
                      <td className="px-4 py-2 text-gray-500 font-mono text-xs">
                        {stamp.id}
                      </td>
                      <td className="px-4 py-2 text-gray-700 text-xs whitespace-nowrap">
                        {new Date(stamp.created_at).toLocaleString("pt-BR")}
                      </td>
                      <td className="px-4 py-2">
                        {stamp.is_manual ? (
                          <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">
                            Manual
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">
                            Automatico
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-gray-500 text-xs max-w-[180px] truncate">
                        {stamp.notes || "-"}
                      </td>
                      <td className="px-4 py-2 text-center">
                        {stamp.voided_at ? (
                          <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs rounded-full">
                            Estornado
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">
                            Ativo
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-center">
                        {!stamp.voided_at && (
                          <button
                            onClick={() => estornarCarimboGestor(stamp.id)}
                            disabled={gestorRemovendo === stamp.id}
                            className="px-2 py-1 bg-red-100 text-red-700 text-xs rounded-lg hover:bg-red-200 disabled:opacity-50"
                          >
                            {gestorRemovendo === stamp.id ? "..." : "Remover"}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-center text-gray-400 py-4 text-sm">
            Nenhum carimbo encontrado.
          </p>
        )}

        <label className="flex items-center gap-2 text-xs text-gray-500 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={gestorIncluirEstornados}
            onChange={(e) => setGestorIncluirEstornados(e.target.checked)}
            className="rounded"
          />
          Mostrar estornados
        </label>
      </div>
    </CampanhasGestorSection>
  );
}
