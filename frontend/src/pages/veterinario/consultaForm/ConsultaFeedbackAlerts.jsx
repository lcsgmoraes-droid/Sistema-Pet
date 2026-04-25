import { AlertCircle, CheckCircle, X } from "lucide-react";

export default function ConsultaFeedbackAlerts({
  erro,
  sucesso,
  onClearErro,
  onClearSucesso,
}) {
  return (
    <>
      {erro && (
        <div className="flex items-center gap-2 text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm">
          <AlertCircle size={16} />
          <span>{erro}</span>
          <button className="ml-auto" onClick={onClearErro}><X size={14} /></button>
        </div>
      )}

      {sucesso && (
        <div className="flex items-center gap-2 text-green-700 bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-sm">
          <CheckCircle size={16} />
          <span>{sucesso}</span>
          <button className="ml-auto" onClick={onClearSucesso}><X size={14} /></button>
        </div>
      )}
    </>
  );
}
