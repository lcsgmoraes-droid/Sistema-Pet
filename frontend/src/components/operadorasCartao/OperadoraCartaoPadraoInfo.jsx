import { Check } from "lucide-react";

function OperadoraCartaoPadraoInfo({ operadora }) {
  if (!operadora) return null;

  return (
    <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 mb-6">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-emerald-100 rounded-lg">
          <Check className="w-5 h-5 text-emerald-600" />
        </div>
        <div>
          <h3 className="font-medium text-emerald-900">Operadora Padrao</h3>
          <p className="text-sm text-emerald-700">
            <span className="font-medium">{operadora.nome}</span> sera
            pre-selecionada no PDV
          </p>
        </div>
      </div>
    </div>
  );
}

export default OperadoraCartaoPadraoInfo;
