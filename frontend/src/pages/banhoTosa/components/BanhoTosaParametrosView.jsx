import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage, toApiDecimal } from "../banhoTosaUtils";
import BanhoTosaHelpTooltip from "./BanhoTosaHelpTooltip";
import BanhoTosaParametrosLista from "./BanhoTosaParametrosLista";
import BanhoTosaPorteForm, {
  formFromParametroPorte,
  initialPorteForm,
  payloadFromPorteForm,
} from "./BanhoTosaPorteForm";

export default function BanhoTosaParametrosView({ config, parametros, onChanged }) {
  const [configForm, setConfigForm] = useState(null);
  const [porteForm, setPorteForm] = useState(initialPorteForm);
  const [editingPorte, setEditingPorte] = useState(null);
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

  function editarPorte(item) {
    setEditingPorte(item);
    setPorteForm(formFromParametroPorte(item));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function cancelarEdicaoPorte() {
    setEditingPorte(null);
    setPorteForm(initialPorteForm);
  }

  async function salvarPorte(event) {
    event.preventDefault();
    if (!porteForm.porte.trim()) {
      toast.error("Informe o porte.");
      return;
    }

    setSavingPorte(true);
    try {
      const payload = payloadFromPorteForm(porteForm);
      if (editingPorte) {
        await banhoTosaApi.atualizarParametroPorte(editingPorte.id, payload);
        toast.success("Porte atualizado.");
      } else {
        await banhoTosaApi.criarParametroPorte(payload);
        toast.success("Porte cadastrado.");
      }
      cancelarEdicaoPorte();
      await onChanged(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel salvar porte."));
    } finally {
      setSavingPorte(false);
    }
  }

  async function togglePorteAtivo(item) {
    try {
      await banhoTosaApi.atualizarParametroPorte(item.id, { ativo: !item.ativo });
      await onChanged(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel atualizar o porte."));
    }
  }

  async function excluirPorte(item) {
    const confirmou = window.confirm(
      `Excluir o porte "${item.porte}"? Se ele ja tiver historico, o sistema vai apenas desativar.`,
    );
    if (!confirmou) return;

    try {
      const response = await banhoTosaApi.removerParametroPorte(item.id);
      toast.success(response.data?.message || "Porte excluido.");
      if (editingPorte?.id === item.id) {
        cancelarEdicaoPorte();
      }
      await onChanged(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel excluir o porte."));
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
            <TextField label="Slot agenda (min)" type="number" value={configForm.intervalo_slot_minutos} onChange={(value) => updateConfig("intervalo_slot_minutos", value)} help="Intervalo usado para montar a grade de horarios e sugerir encaixes." />
            <TextField label="Dias funcionamento" value={configForm.dias_funcionamento} onChange={(value) => updateConfig("dias_funcionamento", value)} help="Informe os dias separados por virgula: segunda,terca,quarta..." />
            <TextField label="Custo litro agua" type="number" value={configForm.custo_litro_agua} onChange={(value) => updateConfig("custo_litro_agua", value)} help="Valor medio da agua e esgoto dividido por litro. Exemplo: R$ 0,02 por litro." />
            <TextField label="Vazao chuveiro L/min" type="number" value={configForm.vazao_chuveiro_litros_min} onChange={(value) => updateConfig("vazao_chuveiro_litros_min", value)} help="Quantos litros o chuveiro consome por minuto durante o banho." />
            <TextField label="Custo kWh" type="number" value={configForm.custo_kwh} onChange={(value) => updateConfig("custo_kwh", value)} help="Valor medio do kWh usado para calcular secador, soprador e equipamentos." />
            <TextField label="Toalha por banho" type="number" value={configForm.custo_toalha_padrao} onChange={(value) => updateConfig("custo_toalha_padrao", value)} help="Custo medio de lavanderia, desgaste ou aluguel de toalha por atendimento." />
            <TextField label="Higienizacao por banho" type="number" value={configForm.custo_higienizacao_padrao} onChange={(value) => updateConfig("custo_higienizacao_padrao", value)} help="Produtos de limpeza, desinfeccao de mesa/banheira e descartaveis." />
            <TextField label="% taxas padrao" type="number" value={configForm.percentual_taxas_padrao} onChange={(value) => updateConfig("percentual_taxas_padrao", value)} help="Percentual medio de cartao, app ou taxa operacional sobre a venda." />
            <TextField label="Rateio operacional" type="number" value={configForm.custo_rateio_operacional_padrao} onChange={(value) => updateConfig("custo_rateio_operacional_padrao", value)} help="Parcela media de aluguel, recepcao, limpeza e despesas fixas por atendimento." />
            <TextField label="Horas produtivas mes" type="number" value={configForm.horas_produtivas_mes_padrao} onChange={(value) => updateConfig("horas_produtivas_mes_padrao", value)} help="Horas mensais usadas para ratear salario/custo do funcionario nos atendimentos." />
          </div>

          <button
            type="submit"
            disabled={savingConfig}
            className="mt-6 w-full rounded-2xl bg-slate-900 px-5 py-3 text-sm font-bold text-white transition hover:bg-slate-700 disabled:opacity-60"
          >
            {savingConfig ? "Salvando..." : "Salvar parametros"}
          </button>
        </form>

        <BanhoTosaPorteForm
          form={porteForm}
          editing={Boolean(editingPorte)}
          saving={savingPorte}
          onChangeField={updatePorte}
          onCancelEdit={cancelarEdicaoPorte}
          onSubmit={salvarPorte}
        />
      </div>

      <BanhoTosaParametrosLista
        parametros={parametros}
        onEdit={editarPorte}
        onDelete={excluirPorte}
        onToggleAtivo={togglePorteAtivo}
      />
    </div>
  );
}


function TextField({ label, value, onChange, type = "text", help }) {
  return (
    <label className="block">
      <span className="inline-flex items-center text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
        {label}
        <BanhoTosaHelpTooltip text={help} />
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
