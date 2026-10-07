import { Lock } from "lucide-react";

export default function ConsultaReadonlyNotice({ assinatura }) {
  return (
    <div className="space-y-2 text-green-700 bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-sm">
      <div className="flex items-center gap-2">
        <Lock size={15} />
        <span>Consulta assinada. Você pode visualizar os dados, mas não pode alterá-los.</span>
      </div>
      {assinatura && !assinatura.hash_valido && (
        <p className="font-medium text-red-700">
          A verificação do prontuário encontrou uma divergência. Confira a assinatura antes de usar
          o documento.
        </p>
      )}
      {assinatura && (
        <details className="text-xs text-green-800">
          <summary className="cursor-pointer">Verificação da assinatura</summary>
          <div className="mt-2 rounded border border-green-200 bg-white/70 px-3 py-2">
            <div>
              Integridade do prontuário:{" "}
              <strong>{assinatura.hash_valido ? "válida" : "divergente"}</strong>
            </div>
            <div>
              Hash: <span className="font-mono break-all">{assinatura.hash_prontuario || "—"}</span>
            </div>
          </div>
        </details>
      )}
    </div>
  );
}
