import { Edit2, Trash2 } from "lucide-react";
import { getIconeOperadora } from "./operadorasCartaoUtils";

function OperadoraCartaoCard({ operadora, onEditar, onExcluir }) {
  const iconeOperadora = getIconeOperadora(operadora.icone);

  return (
    <div
      className={`border rounded-lg p-4 hover:shadow-md transition-shadow ${
        !operadora.ativo ? "bg-gray-50 border-gray-300" : "bg-white border-gray-200"
      } ${operadora.padrao ? "ring-2 ring-emerald-500" : ""}`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div
            className="w-12 h-12 rounded-lg flex items-center justify-center text-2xl"
            style={{ backgroundColor: `${operadora.cor}20` }}
          >
            {iconeOperadora}
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              {operadora.nome}
              {operadora.padrao && (
                <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full">
                  Padrao
                </span>
              )}
            </h3>
            {operadora.codigo && (
              <p className="text-xs text-gray-500 font-mono">{operadora.codigo}</p>
            )}
          </div>
        </div>

        <div
          className={`px-2 py-1 rounded text-xs font-medium ${
            operadora.ativo ? "bg-green-100 text-green-700" : "bg-gray-200 text-gray-600"
          }`}
        >
          {operadora.ativo ? "Ativo" : "Inativo"}
        </div>
      </div>

      <div className="space-y-2 mb-4 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">Parcelas maximas:</span>
          <span className="font-medium text-gray-900">{operadora.max_parcelas}x</span>
        </div>

        {operadora.api_enabled && (
          <div className="mt-2 pt-2 border-t border-gray-200">
            <span className="text-xs text-blue-600 flex items-center gap-1">
              <span className="w-2 h-2 bg-blue-600 rounded-full"></span>
              API Integrada
            </span>
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => onEditar(operadora)}
          className="flex-1 bg-blue-50 text-blue-600 px-3 py-2 rounded hover:bg-blue-100 flex items-center justify-center gap-2 transition-colors text-sm"
        >
          <Edit2 className="w-4 h-4" />
          Editar
        </button>
        <button
          onClick={() => onExcluir(operadora.id)}
          className="flex-1 bg-red-50 text-red-600 px-3 py-2 rounded hover:bg-red-100 flex items-center justify-center gap-2 transition-colors text-sm"
        >
          <Trash2 className="w-4 h-4" />
          Excluir
        </button>
      </div>
    </div>
  );
}

export default OperadoraCartaoCard;
