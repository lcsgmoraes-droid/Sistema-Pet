import { useState } from "react";
import toast from "react-hot-toast";
import ActionButton from "../../../components/ui/ActionButton";
import Panel from "../../../components/ui/Panel";
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
    <Panel
      actions={
        <ActionButton intent="create" loading={aplicando} onClick={aplicarBase}>
          Aplicar base padrao
        </ActionButton>
      }
      subtitle="Cria portes, servicos, recursos e modelos de retorno com valores medios. Nao sobrescreve cadastros existentes."
      title="Base inicial editavel"
    >

      {resumo && (
        <div className="mt-4 grid gap-2 text-sm sm:grid-cols-4">
          <Resumo label="Portes" value={resumo.criados?.parametros} existing={resumo.existentes?.parametros} />
          <Resumo label="Servicos" value={resumo.criados?.servicos} existing={resumo.existentes?.servicos} />
          <Resumo label="Recursos" value={resumo.criados?.recursos} existing={resumo.existentes?.recursos} />
          <Resumo label="Templates" value={resumo.criados?.templates} existing={resumo.existentes?.templates} />
        </div>
      )}
    </Panel>
  );
}

function Resumo({ label, value = 0, existing = 0 }) {
  return (
    <div className="rounded-lg bg-slate-50 px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p className="mt-1 font-semibold text-slate-900">
        {value || 0} criados
      </p>
      <p className="text-xs text-slate-500">
        {existing || 0} ja existiam
      </p>
    </div>
  );
}
