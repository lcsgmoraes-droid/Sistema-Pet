import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage, toApiDecimal } from "../banhoTosaUtils";
import BanhoTosaParametrosLista from "./BanhoTosaParametrosLista";

const initialPorteForm = {
  porte: "",
  peso_min_kg: "",
  peso_max_kg: "",
  agua_padrao_litros: "0",
  energia_padrao_kwh: "0",
  tempo_banho_min: "0",
  tempo_secagem_min: "0",
  tempo_tosa_min: "0",
  multiplicador_preco: "1",
};

export default function BanhoTosaParametrosView({ config, parametros, onChanged }) {
  const [configForm, setConfigForm] = useState(null);
  const [porteForm, setPorteForm] = useState(initialPorteForm);
  const [savingConfig, setSavingConfig] = useState(false);
  const [savingPorte, setSavingPorte] = useState(false);

  useEffect(() => {
    if (!config) return;

    setConfigForm({
      horario_inicio: config.horario_inicio || "08:00",
      horario_fim: config.horario_fim || "18:00",
      dias_funcionamento: (config.dias_funcionamento || []).join(","),
      intervalo_slot_minutos: String(config.intervalo_slot_minutos || 30),
      custo_litro_agua: String(config.custo_litro_agua ?? "0"),
      vazao_chuveiro_litros_min: String(config.vazao_chuveiro_litros_min ?? "0"),
      custo_kwh: String(config.custo_kwh ?? "0"),
      custo_toalha_padrao: String(config.custo_toalha_padrao ?? "0"),
      custo_higienizacao_padrao: String(config.custo_higienizacao_padrao ?? "0"),
      percentual_taxas_padrao: String(config.percentual_taxas_padrao ?? "0"),
      custo_rateio_operacional_padrao: String(
        config.custo_rateio_operacional_padrao ?? "0",
      ),
      horas_produtivas_mes_padrao: String(config.horas_produtivas_mes_padrao ?? "176"),
    });
  }, [config?.id]);

  function updateConfig(field, value) {
    setConfigForm((prev) => ({ ...prev, [field]: value }));
  }

  function updatePorte(field, value) {
    setPorteForm((prev) => ({ ...prev, [field]: value }));
  }

  async function salvarConfig(event) {
    event.preventDefault();
    setSavingConfig(true);

    try {
      await banhoTosaApi.atualizarConfiguracao({
        horario_inicio: configForm.horario_inicio || null,
        horario_fim: configForm.horario_fim || null,
        dias_funcionamento: configForm.dias_funcionamento
          .split(",")
          .map((dia) => dia.trim())
          .filter(Boolean),
        intervalo_slot_minutos: Number(configForm.intervalo_slot_minutos || 30),
        custo_litro_agua: toApiDecimal(configForm.custo_litro_agua),
        vazao_chuveiro_litros_min: toApiDecimal(configForm.vazao_chuveiro_litros_min),
        custo_kwh: toApiDecimal(configForm.custo_kwh),
        custo_toalha_padrao: toApiDecimal(configForm.custo_toalha_padrao),
        custo_higienizacao_padrao: toApiDecimal(configForm.custo_higienizacao_padrao),
        percentual_taxas_padrao: toApiDecimal(configForm.percentual_taxas_padrao),
        custo_rateio_operacional_padrao: toApiDecimal(
          configForm.custo_rateio_operacional_padrao,
        ),
        horas_produtivas_mes_padrao: toApiDecimal(
          configForm.horas_produtivas_mes_padrao,
          "176",
        ),
      });
      toast.success("Parametros salvos.");
      await onChanged(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel salvar parametros."));
    } finally {
      setSavingConfig(false);
    }
  }

  async function criarPorte(event) {
    event.preventDefault();
    if (!porteForm.porte.trim()) {
      toast.error("Informe o porte.");
      return;
    }

    setSavingPorte(true);
    try {
      await banhoTosaApi.criarParametroPorte({
        porte: porteForm.porte.trim(),
        peso_min_kg: porteForm.peso_min_kg ? toApiDecimal(porteForm.peso_min_kg) : null,
        peso_max_kg: porteForm.peso_max_kg ? toApiDecimal(porteForm.peso_max_kg) : null,
        agua_padrao_litros: toApiDecimal(porteForm.agua_padrao_litros),
        energia_padrao_kwh: toApiDecimal(porteForm.energia_padrao_kwh),
        tempo_banho_min: Number(porteForm.tempo_banho_min || 0),
        tempo_secagem_min: Number(porteForm.tempo_secagem_min || 0),
        tempo_tosa_min: Number(porteForm.tempo_tosa_min || 0),
        multiplicador_preco: toApiDecimal(porteForm.multiplicador_preco, "1"),
        ativo: true,
      });
      toast.success("Porte cadastrado.");
      setPorteForm(initialPorteForm);
      await onChanged(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel cadastrar porte."));
    } finally {
      setSavingPorte(false);
    }
  }

  if (!configForm) {
    return (
      <div className="rounded-3xl border border-white/80 bg-white p-6 text-slate-500 shadow-sm">
        Carregando parametros...
      </div>
    );
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
      <div className="space-y-6">
        <form
          onSubmit={salvarConfig}
          className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm"
        >
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
            Parametros gerais
          </p>
          <h2 className="mt-2 text-xl font-black text-slate-900">
            Operacao e custos base
          </h2>

          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <TextField label="Inicio" type="time" value={configForm.horario_inicio} onChange={(value) => updateConfig("horario_inicio", value)} />
            <TextField label="Fim" type="time" value={configForm.horario_fim} onChange={(value) => updateConfig("horario_fim", value)} />
            <TextField label="Slot agenda (min)" type="number" value={configForm.intervalo_slot_minutos} onChange={(value) => updateConfig("intervalo_slot_minutos", value)} />
            <TextField label="Dias funcionamento" value={configForm.dias_funcionamento} onChange={(value) => updateConfig("dias_funcionamento", value)} />
            <TextField label="Custo litro agua" type="number" value={configForm.custo_litro_agua} onChange={(value) => updateConfig("custo_litro_agua", value)} />
            <TextField label="Vazao chuveiro L/min" type="number" value={configForm.vazao_chuveiro_litros_min} onChange={(value) => updateConfig("vazao_chuveiro_litros_min", value)} />
            <TextField label="Custo kWh" type="number" value={configForm.custo_kwh} onChange={(value) => updateConfig("custo_kwh", value)} />
            <TextField label="Toalha por banho" type="number" value={configForm.custo_toalha_padrao} onChange={(value) => updateConfig("custo_toalha_padrao", value)} />
            <TextField label="Higienizacao por banho" type="number" value={configForm.custo_higienizacao_padrao} onChange={(value) => updateConfig("custo_higienizacao_padrao", value)} />
            <TextField label="% taxas padrao" type="number" value={configForm.percentual_taxas_padrao} onChange={(value) => updateConfig("percentual_taxas_padrao", value)} />
            <TextField label="Rateio operacional" type="number" value={configForm.custo_rateio_operacional_padrao} onChange={(value) => updateConfig("custo_rateio_operacional_padrao", value)} />
            <TextField label="Horas produtivas mes" type="number" value={configForm.horas_produtivas_mes_padrao} onChange={(value) => updateConfig("horas_produtivas_mes_padrao", value)} />
          </div>

          <button
            type="submit"
            disabled={savingConfig}
            className="mt-6 w-full rounded-2xl bg-slate-900 px-5 py-3 text-sm font-bold text-white transition hover:bg-slate-700 disabled:opacity-60"
          >
            {savingConfig ? "Salvando..." : "Salvar parametros"}
          </button>
        </form>

        <form
          onSubmit={criarPorte}
          className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm"
        >
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
            Portes
          </p>
          <h2 className="mt-2 text-xl font-black text-slate-900">
            Novo parametro por porte
          </h2>

          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <TextField label="Porte" value={porteForm.porte} onChange={(value) => updatePorte("porte", value)} />
            <TextField label="Multiplicador preco" type="number" value={porteForm.multiplicador_preco} onChange={(value) => updatePorte("multiplicador_preco", value)} />
            <TextField label="Peso min kg" type="number" value={porteForm.peso_min_kg} onChange={(value) => updatePorte("peso_min_kg", value)} />
            <TextField label="Peso max kg" type="number" value={porteForm.peso_max_kg} onChange={(value) => updatePorte("peso_max_kg", value)} />
            <TextField label="Agua padrao L" type="number" value={porteForm.agua_padrao_litros} onChange={(value) => updatePorte("agua_padrao_litros", value)} />
            <TextField label="Energia padrao kWh" type="number" value={porteForm.energia_padrao_kwh} onChange={(value) => updatePorte("energia_padrao_kwh", value)} />
            <TextField label="Tempo banho min" type="number" value={porteForm.tempo_banho_min} onChange={(value) => updatePorte("tempo_banho_min", value)} />
            <TextField label="Tempo secagem min" type="number" value={porteForm.tempo_secagem_min} onChange={(value) => updatePorte("tempo_secagem_min", value)} />
            <TextField label="Tempo tosa min" type="number" value={porteForm.tempo_tosa_min} onChange={(value) => updatePorte("tempo_tosa_min", value)} />
          </div>

          <button
            type="submit"
            disabled={savingPorte}
            className="mt-6 w-full rounded-2xl bg-orange-500 px-5 py-3 text-sm font-bold text-white transition hover:bg-orange-600 disabled:opacity-60"
          >
            {savingPorte ? "Salvando..." : "Cadastrar porte"}
          </button>
        </form>
      </div>

      <BanhoTosaParametrosLista parametros={parametros} />
    </div>
  );
}

function TextField({ label, value, onChange, type = "text" }) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
        {label}
      </span>
      <input
        type={type}
        step={type === "number" ? "0.01" : undefined}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100"
      />
    </label>
  );
}
