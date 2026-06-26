import { FiAlertTriangle } from "react-icons/fi";

export default function OpsTenantsGuardrailsPanel() {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
        <FiAlertTriangle className="h-4 w-4 text-amber-600" />
        Guardrails do MVP
      </div>
      <div className="mt-3 space-y-2 text-sm text-slate-600">
        <p>O comando copia dados para outro tenant, mantendo cada cliente separado.</p>
        <p>
          Estoque, custo, margem, fornecedores e precos operacionais entram zerados ou vazios pela
          rotina de catalogo base.
        </p>
        <p>A importacao real so fica habilitada depois de uma simulacao sem erro.</p>
      </div>
    </section>
  );
}
