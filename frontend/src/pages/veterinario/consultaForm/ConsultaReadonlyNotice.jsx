import { Lock } from "lucide-react";

export default function ConsultaReadonlyNotice({
  assinatura,
  baixandoPdf,
  onBaixarProntuario,
  onBaixarReceita,
}) {
  return (
    <div className="space-y-2 text-green-700 bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-sm">
      <div className="flex items-center gap-2">
        <Lock size={15} />
        <span>Consulta assinada digitalmente. Você pode visualizar todos os dados, mas não pode editar.</span>
      </div>
      {assinatura && (
        <div className="text-xs text-green-800 bg-white/70 border border-green-200 rounded px-3 py-2">
          <div>
            Integridade do prontuário: <strong>{assinatura.hash_valido ? "válida" : "divergente"}</strong>
          </div>
          <div>
            Hash: <span className="font-mono">{assinatura.hash_prontuario || "—"}</span>
          </div>
        </div>
      )}
      <div className="flex flex-wrap gap-2 pt-1">
        <button
          type="button"
          onClick={onBaixarProntuario}
          disabled={baixandoPdf}
          className="px-3 py-1.5 text-xs border border-green-300 rounded-md hover:bg-green-100 disabled:opacity-60"
        >
          {baixandoPdf ? "Baixando..." : "Baixar prontuário PDF"}
        </button>
        <button
          type="button"
          onClick={onBaixarReceita}
          disabled={baixandoPdf}
          className="px-3 py-1.5 text-xs border border-green-300 rounded-md hover:bg-green-100 disabled:opacity-60"
        >
          {baixandoPdf ? "Baixando..." : "Baixar receita PDF"}
        </button>
      </div>
    </div>
  );
}
