import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { banhoTosaApi } from "../banhoTosaApi";
import { formatCurrency, formatNumber, getApiErrorMessage, toApiDecimal } from "../banhoTosaUtils";

const initialForm = {
  valor_cobrado: "90",
  custo_insumos: "8",
  custo_litro_agua: "0.02",
  vazao_chuveiro_litros_min: "8",
  minutos_banho: "20",
  potencia_watts: "2400",
  minutos_energia: "30",
  custo_kwh: "1.00",
  custo_manutencao_hora: "0",
  custo_mensal_funcionario: "2200",
  horas_produtivas_mes: "176",
  minutos_trabalhados: "60",
  percentual_comissao: "0",
  percentual_taxas_pagamento: "3",
  custo_rateio_operacional: "0",
};

export default function BanhoTosaSimulador({ config }) {
  const [form, setForm] = useState(initialForm);
  const [resultado, setResultado] = useState(null);
  const [simulando, setSimulando] = useState(false);

  useEffect(() => {
    if (!config) return;

    setForm((prev) => ({
      ...prev,
      custo_litro_agua: String(config.custo_litro_agua ?? prev.custo_litro_agua),
      vazao_chuveiro_litros_min: String(
        config.vazao_chuveiro_litros_min ?? prev.vazao_chuveiro_litros_min,
      ),
      custo_kwh: String(config.custo_kwh ?? prev.custo_kwh),
      percentual_taxas_pagamento: String(
        config.percentual_taxas_padrao ?? prev.percentual_taxas_pagamento,
      ),
      custo_rateio_operacional: String(
        config.custo_rateio_operacional_padrao ?? prev.custo_rateio_operacional,
      ),
      horas_produtivas_mes: String(
        config.horas_produtivas_mes_padrao ?? prev.horas_produtivas_mes,
      ),
    }));
  }, [config?.id]);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function simular(event) {
    event.preventDefault();
    setSimulando(true);

    const valorCobrado = Number(toApiDecimal(form.valor_cobrado));
    const percentualTaxas = Number(toApiDecimal(form.percentual_taxas_pagamento));
    const custoTaxas = ((valorCobrado || 0) * (percentualTaxas || 0)) / 100;

    try {
      const response = await banhoTosaApi.simularCusto({
        valor_cobrado: toApiDecimal(form.valor_cobrado),
        insumos: [
          {
            quantidade_usada: "1",
            quantidade_desperdicio: "0",
            custo_unitario_snapshot: toApiDecimal(form.custo_insumos),
          },
        ],
        agua: {
          custo_litro_agua: toApiDecimal(form.custo_litro_agua),
          vazao_chuveiro_litros_min: toApiDecimal(form.vazao_chuveiro_litros_min),
          minutos_banho: toApiDecimal(form.minutos_banho),
        },
        energia: [
          {
            potencia_watts: toApiDecimal(form.potencia_watts),
            minutos_uso: toApiDecimal(form.minutos_energia),
            custo_kwh: toApiDecimal(form.custo_kwh),
            custo_manutencao_hora: toApiDecimal(form.custo_manutencao_hora),
          },
        ],
        mao_obra: [
          {
            custo_mensal_funcionario: toApiDecimal(form.custo_mensal_funcionario),
            horas_produtivas_mes: toApiDecimal(form.horas_produtivas_mes),
            minutos_trabalhados: toApiDecimal(form.minutos_trabalhados),
          },
        ],
        comissao: {
          modelo: "percentual_valor",
          valor_base: toApiDecimal(form.valor_cobrado),
          percentual: toApiDecimal(form.percentual_comissao),
          valor_fixo: "0",
        },
        taxi_dog: {
          km_real: "0",
          custo_km: "0",
          custo_motorista: "0",
          rateio_manutencao: "0",
        },
        custo_taxas_pagamento: custoTaxas.toFixed(2),
        custo_rateio_operacional: toApiDecimal(form.custo_rateio_operacional),
      });

      setResultado(response.data);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel simular o custo."));
    } finally {
      setSimulando(false);
    }
  }

  return (
    <form
      onSubmit={simular}
      className="rounded-3xl border border-orange-100 bg-white p-6 shadow-sm"
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
            Simulador de custo
          </p>
          <h2 className="mt-2 text-xl font-black text-slate-900">
            Margem por banho antes de vender
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Use valores reais ou estimados para validar preco, tempo e margem.
          </p>
        </div>
        <button
          type="submit"
          disabled={simulando}
          className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-slate-700 disabled:opacity-60"
        >
          {simulando ? "Simulando..." : "Simular margem"}
        </button>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <NumberField label="Valor cobrado" value={form.valor_cobrado} onChange={(value) => updateField("valor_cobrado", value)} />
        <NumberField label="Insumos totais" value={form.custo_insumos} onChange={(value) => updateField("custo_insumos", value)} />
        <NumberField label="Minutos de banho" value={form.minutos_banho} onChange={(value) => updateField("minutos_banho", value)} />
        <NumberField label="Vazao L/min" value={form.vazao_chuveiro_litros_min} onChange={(value) => updateField("vazao_chuveiro_litros_min", value)} />
        <NumberField label="Custo litro agua" value={form.custo_litro_agua} onChange={(value) => updateField("custo_litro_agua", value)} />
        <NumberField label="Potencia secador W" value={form.potencia_watts} onChange={(value) => updateField("potencia_watts", value)} />
        <NumberField label="Minutos energia" value={form.minutos_energia} onChange={(value) => updateField("minutos_energia", value)} />
        <NumberField label="Custo kWh" value={form.custo_kwh} onChange={(value) => updateField("custo_kwh", value)} />
        <NumberField label="Salario/custo mensal" value={form.custo_mensal_funcionario} onChange={(value) => updateField("custo_mensal_funcionario", value)} />
        <NumberField label="Horas produtivas mes" value={form.horas_produtivas_mes} onChange={(value) => updateField("horas_produtivas_mes", value)} />
        <NumberField label="Minutos mao de obra" value={form.minutos_trabalhados} onChange={(value) => updateField("minutos_trabalhados", value)} />
        <NumberField label="% taxas pagamento" value={form.percentual_taxas_pagamento} onChange={(value) => updateField("percentual_taxas_pagamento", value)} />
      </div>

      {resultado && (
        <div className="mt-6 grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="rounded-3xl bg-slate-900 p-5 text-white">
            <p className="text-sm text-slate-300">Custo total estimado</p>
            <p className="mt-2 text-4xl font-black">
              {formatCurrency(resultado.custo_total)}
            </p>
            <p className="mt-4 text-sm text-slate-300">Margem</p>
            <p className="text-2xl font-black">
              {formatCurrency(resultado.margem_valor)} ({formatNumber(resultado.margem_percentual, 2)}%)
            </p>
          </div>

          <div className="grid gap-2 sm:grid-cols-2">
            <Breakdown label="Insumos" value={resultado.custo_insumos} />
            <Breakdown label="Agua" value={resultado.custo_agua} />
            <Breakdown label="Energia" value={resultado.custo_energia} />
            <Breakdown label="Mao de obra" value={resultado.custo_mao_obra} />
            <Breakdown label="Comissao" value={resultado.custo_comissao} />
            <Breakdown label="Taxas" value={resultado.custo_taxas_pagamento} />
          </div>
        </div>
      )}
    </form>
  );
}

function NumberField({ label, value, onChange }) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
        {label}
      </span>
      <input
        type="number"
        step="0.01"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none transition focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100"
      />
    </label>
  );
}

function Breakdown({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
      <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
        {label}
      </p>
      <p className="mt-1 text-lg font-black text-slate-900">
        {formatCurrency(value)}
      </p>
    </div>
  );
}
