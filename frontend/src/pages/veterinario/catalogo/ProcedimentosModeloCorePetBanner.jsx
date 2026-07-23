import { LibraryBig, Loader2 } from "lucide-react";

export default function ProcedimentosModeloCorePetBanner({
  importando,
  onImportar,
  status,
}) {
  const quantidade = status?.disponiveis_para_importar || 0;
  if (!status || quantidade <= 0) return null;

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-cyan-200 bg-cyan-50 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-3">
        <LibraryBig className="mt-0.5 shrink-0 text-cyan-700" size={19} />
        <div>
          <p className="text-sm font-semibold text-cyan-950">
            Há {quantidade} procedimento(s) do modelo CorePet disponíveis
          </p>
          <p className="mt-1 text-xs text-cyan-800">
            A importação é opcional e não preenche preços nem insumos. Você poderá editar ou
            excluir qualquer item depois.
          </p>
        </div>
      </div>
      <button
        type="button"
        onClick={onImportar}
        disabled={importando}
        className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-cyan-700 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-800 disabled:opacity-60"
      >
        {importando ? <Loader2 className="animate-spin" size={15} /> : null}
        Importar procedimentos
      </button>
    </div>
  );
}
