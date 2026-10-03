import { CheckCircle, FileText } from "lucide-react";

export default function ConsultaFinalizadaScreen({
  onVerConsultas,
  onNovaConsulta,
  onAbrirDocumentos,
}) {
  return (
    <div className="p-6 max-w-lg mx-auto text-center space-y-4">
      <div className="p-4 bg-green-50 rounded-xl border border-green-200">
        <CheckCircle size={40} className="mx-auto text-green-500 mb-2" />
        <h2 className="text-lg font-bold text-green-700">Consulta finalizada!</h2>
        <p className="text-sm text-gray-500 mt-1">
          O prontuário foi assinado digitalmente e não pode mais ser alterado.
        </p>
      </div>
      <button
        type="button"
        onClick={onAbrirDocumentos}
        className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
      >
        <FileText size={16} />
        Abrir prontuário e documentos PDF
      </button>
      <div className="flex gap-3 justify-center">
        <button
          onClick={onVerConsultas}
          className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          Ver todas as consultas
        </button>
        <button
          onClick={onNovaConsulta}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Nova consulta
        </button>
      </div>
    </div>
  );
}
