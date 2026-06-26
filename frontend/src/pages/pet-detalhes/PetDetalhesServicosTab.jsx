import { PawPrint } from "lucide-react";

export default function PetDetalhesServicosTab({ carteirinha }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-900">HistÃ³rico de ServiÃ§os</h2>
        <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm font-medium">
          + Registrar ServiÃ§o
        </button>
      </div>
      {Array.isArray(carteirinha?.alertas) && carteirinha.alertas.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <h3 className="text-sm font-semibold text-amber-900 mb-2">
            Alertas para banho, tosa e serviÃ§os
          </h3>
          <div className="space-y-2 text-sm text-amber-900">
            {carteirinha.alertas.slice(0, 5).map((alerta, idx) => (
              <p key={`servico_alerta_${idx}`}>â€¢ {alerta.mensagem}</p>
            ))}
          </div>
        </div>
      )}
      <div className="text-center py-12 text-gray-500">
        <PawPrint size={48} className="mx-auto mb-4 text-gray-300" />
        <p className="text-lg font-medium mb-2">MÃ³dulo em desenvolvimento</p>
        <p className="text-sm">Em breve vocÃª poderÃ¡ gerenciar banho, tosa e outros serviÃ§os</p>
      </div>
    </div>
  );
}
