import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { banhoTosaApi } from "../banhoTosaApi";
import { formatCurrency, formatNumber, getApiErrorMessage } from "../banhoTosaUtils";

export default function BanhoTosaCustoPanel({ atendimentoId, refreshSignal = 0 }) {
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(false);
  const [recalculando, setRecalculando] = useState(false);

  async function carregarCusto() {
    if (!atendimentoId) return;
    setLoading(true);
    try {
      const response = await banhoTosaApi.obterCustoAtendimento(atendimentoId);
      setSnapshot(response.data || null);
    } catch {
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  }

  async function recalcular({ notify = true } = {}) {
    if (!atendimentoId) return;
    setRecalculando(true);
    try {
      const response = await banhoTosaApi.recalcularCustoAtendimento(atendimentoId);
      setSnapshot(response.data || null);
      if (notify) {
        toast.success("Custo recalculado.");
      }
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel recalcular custo."));
    } finally {
      setRecalculando(false);
    }
  }

  useEffect(() => {
    if (refreshSignal > 0) {
      recalcular({ notify: false });
      return;
    }
    carregarCusto();
  }, [atendimentoId, refreshSignal]);

  if (loading && !snapshot) {
    return (
      <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm font-semibold text-slate-500">
        Calculando margem operacional...
      </div>
    );
  }

  if (!snapshot) {
    return (
      <div className="mt-6 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-4">
        <p className="text-sm font-semibold text-slate-500">
          Ainda nao ha snapshot de custo para este atendimento.
        </p>
        <button
          type="button"
          onClick={() => recalcular()}
          disabled={recalculando}
          className="mt-3 rounded-xl bg-orange-500 px-4 py-2 text-sm font-bold text-white transition hover:bg-orange-600 disabled:opacity-60"
        >
          {recalculando ? "Calculando..." : "Calcular agora"}
        </button>
      </div>
    );
  }

  const margemBoa = Number(snapshot.margem_percentual || 0) >= 35;

  return (
    <div className="mt-6 rounded-3xl border border-orange-100 bg-orange-50/60 p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-600">
            Custo real
          </p>
          <h3 className="mt-2 text-lg font-black text-slate-900">
            Margem do atendimento
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            Baseado em etapas, responsaveis, recursos, agua, energia e parametros.
          </p>
        </div>
        <button
          type="button"
          onClick={() => recalcular()}
          disabled={recalculando}
          className="rounded-2xl bg-slate-900 px-4 py-2 text-sm font-bold text-white transition hover:bg-slate-700 disabled:opacity-60"
        >
          {recalculando ? "Recalculando..." : "Recalcular"}
        </button>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <Metric label="Valor cobrado" value={formatCurrency(snapshot.valor_cobrado)} />
        <Metric label="Custo total" value={formatCurrency(snapshot.custo_total)} />
        <Metric
          label="Margem"
          value={`${formatCurrency(snapshot.margem_valor)} (${formatNumber(snapshot.margem_percentual, 2)}%)`}
          tone={margemBoa ? "text-emerald-700" : "text-rose-700"}
        />
      </div>

      <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <Breakdown label="Mao de obra" value={snapshot.custo_mao_obra} />
        <Breakdown label="Energia" value={snapshot.custo_energia} />
        <Breakdown label="Agua" value={snapshot.custo_agua} />
        <Breakdown label="Insumos" value={snapshot.custo_insumos} />
        <Breakdown label="Taxi dog" value={snapshot.custo_taxi_dog} />
        <Breakdown label="Taxas" value={snapshot.custo_taxas_pagamento} />
        <Breakdown label="Rateio" value={snapshot.custo_rateio_operacional} />
        <Breakdown label="Comissao" value={snapshot.custo_comissao} />
      </div>
    </div>
  );
}

function Metric({ label, value, tone = "text-slate-900" }) {
  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">
        {label}
      </p>
      <p className={`mt-2 text-xl font-black ${tone}`}>{value}</p>
    </div>
  );
}

function Breakdown({ label, value }) {
  return (
    <div className="rounded-xl bg-white/80 px-3 py-2">
      <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">
        {label}
      </p>
      <p className="font-black text-slate-900">{formatCurrency(value)}</p>
    </div>
  );
}
