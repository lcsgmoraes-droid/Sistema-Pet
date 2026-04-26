import { useState } from "react";
import toast from "react-hot-toast";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage } from "../banhoTosaUtils";

export default function BanhoTosaDefaultsPanel({ onApplied }) {
  const [aplicando, setAplicando] = useState(false);
  const [resumo, setResumo] = useState(null);

  async function aplicarBase() {
    setAplicando(true);
    try {
      const response = await banhoTosaApi.aplicarDefaults();
      setResumo(response.data);
      toast.success("Base padrao aplicada.");
      await onApplied?.(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel aplicar a base padrao."));
    } finally {
      setAplicando(false);
    }
  }

  return (
    <div className="rounded-3xl border border-orange-100 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
            Base inicial editavel
          </p>
          <h2 className="mt-2 text-xl font-black text-slate-900">
            Parametros medios para comecar rapido
          </h2>
          <p className="mt-1 max-w-3xl text-sm text-slate-500">
            Cria portes, servicos, recursos e modelos de retorno com valores medios. Nao sobrescreve cadastros existentes; depois a loja pode ajustar tudo.
          </p>
        </div>
        <button
          type="button"
          onClick={aplicarBase}
          disabled={aplicando}
          className="rounded-2xl bg-orange-500 px-5 py-3 text-sm font-black text-white shadow-sm transition hover:bg-orange-600 disabled:opacity-60"
        >
          {aplicando ? "Aplicando..." : "Aplicar base padrao"}
        </button>
      </div>

      {resumo && (
        <div className="mt-4 grid gap-2 text-sm sm:grid-cols-4">
          <Resumo label="Portes" value={resumo.criados?.parametros} existing={resumo.existentes?.parametros} />
          <Resumo label="Servicos" value={resumo.criados?.servicos} existing={resumo.existentes?.servicos} />
          <Resumo label="Recursos" value={resumo.criados?.recursos} existing={resumo.existentes?.recursos} />
          <Resumo label="Templates" value={resumo.criados?.templates} existing={resumo.existentes?.templates} />
        </div>
      )}
    </div>
  );
}

function Resumo({ label, value = 0, existing = 0 }) {
  return (
    <div className="rounded-2xl bg-orange-50 px-4 py-3">
      <p className="text-xs font-bold uppercase tracking-[0.12em] text-orange-700">
        {label}
      </p>
      <p className="mt-1 font-black text-slate-900">
        {value || 0} criados
      </p>
      <p className="text-xs font-semibold text-slate-500">
        {existing || 0} ja existiam
      </p>
    </div>
  );
}
