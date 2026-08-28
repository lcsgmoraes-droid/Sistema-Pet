import { Building2, Check, Copy } from "lucide-react";
import { useState } from "react";
import IconActionButton from "../ui/IconActionButton";

export default function UsuarioLojaLoginCard({ tenantReference }) {
  const [copiado, setCopiado] = useState(false);

  if (!tenantReference) return null;

  const copiarLoja = async () => {
    await navigator.clipboard.writeText(tenantReference);
    setCopiado(true);
    window.setTimeout(() => setCopiado(false), 2000);
  };

  return (
    <section className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <div className="rounded-lg bg-white p-2 text-teal-700 shadow-sm">
            <Building2 className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-teal-950">Identificacao da loja no login</p>
            <p className="mt-0.5 text-xs text-teal-800">
              Funcionarios que usam nome de usuario devem informar este valor no campo Loja.
            </p>
            <code className="mt-2 inline-block max-w-full break-all rounded-md border border-teal-200 bg-white px-3 py-1.5 text-sm font-semibold text-teal-950">
              {tenantReference}
            </code>
          </div>
        </div>
        <IconActionButton
          icon={copiado ? Check : Copy}
          intent="success"
          onClick={copiarLoja}
          title={copiado ? "Loja copiada" : "Copiar identificacao da loja"}
        />
      </div>
    </section>
  );
}
