export default function CampanhasDashboardAniversariosCard({ dashboard }) {
  return (
    <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b bg-pink-50 flex items-center justify-between">
        <h2 className="font-semibold text-gray-800">
          {"\u{1F382}"} Aniversarios de Hoje
        </h2>
        <span className="text-sm text-pink-600 font-medium">
          {dashboard.total_aniversarios} aniversario(s)
        </span>
      </div>
      {dashboard.aniversarios_hoje.length === 0 ? (
        <div className="p-6 text-center text-gray-400 text-sm">
          Nenhum aniversario hoje.
        </div>
      ) : (
        <div className="divide-y">
          {dashboard.aniversarios_hoje.map((a, i) => (
            <div key={i} className="px-6 py-3 flex items-center gap-3">
              <span className="text-xl">
                {a.tipo === "pet" ? "\u{1F415}" : "\u{1F464}"}
              </span>
              <div className="flex-1">
                <p className="font-medium text-gray-900">{a.nome}</p>
                <p className="text-xs text-gray-500">
                  {a.tipo === "pet" ? "Pet" : "Cliente"}
                  {a.idade ? ` - ${a.idade} ano(s)` : ""}
                </p>
              </div>
              <span className="text-xs bg-pink-100 text-pink-700 px-2 py-0.5 rounded-full">
                {"\u{1F382}"} Hoje!
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
