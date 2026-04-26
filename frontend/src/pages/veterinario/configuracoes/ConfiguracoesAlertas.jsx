import { AlertCircle, CheckCircle } from "lucide-react";

export default function ConfiguracoesAlertas({ erro, sucesso, onLimparErro }) {
  return (
    <>
      {erro && (
        <div className="flex items-center gap-2 text-red-600 bg-red-50 border border-red-200 rounded-lg p-4">
          <AlertCircle size={18} />
          <span>{erro}</span>
          <button onClick={onLimparErro} className="ml-auto text-red-400 hover:text-red-600">
            x
          </button>
        </div>
      )}

      {sucesso && (
        <div className="flex items-center gap-2 text-green-700 bg-green-50 border border-green-200 rounded-lg p-4">
          <CheckCircle size={18} />
          <span>{sucesso}</span>
        </div>
      )}
    </>
  );
}
