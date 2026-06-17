import { useEffect, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";
import { CalendarDays, Clock3, Plus, Settings, Smartphone, X } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
import { CheckboxField, TextField } from "../../../components/ui/FormField";
import LoadingState from "../../../components/ui/LoadingState";
import Panel from "../../../components/ui/Panel";
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
  const [configOpen, setConfigOpen] = useState(false);
  const [porteForm, setPorteForm] = useState(initialPorteForm);
  const [porteFormOpen, setPorteFormOpen] = useState(false);
  const [editingPorte, setEditingPorte] = useState(null);
  const [savingConfig, setSavingConfig] = useState(false);
  const [savingPorte, setSavingPorte] = useState(false);
  const configPanelRef = useRef(null);
  const portePanelRef = useRef(null);

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
      custo_rateio_operacional_padrao: String(config.custo_rateio_operacional_padrao ?? "0"),
      horas_produtivas_mes_padrao: String(config.horas_produtivas_mes_padrao ?? "176"),
      mostrar_calendario_cliente: Boolean(config.mostrar_calendario_cliente),
      whatsapp_agendamento: config.whatsapp_agendamento || "",
    });
  }, [config?.id]);

  const resumo = useMemo(() => {
    if (!configForm) return [];

    const dias = configForm.dias_funcionamento
      .split(",")
      .map((dia) => dia.trim())
      .filter(Boolean);

    return [
      {
        icon: Clock3,
        label: "Horario",
        value: `${configForm.horario_inicio || "--:--"} as ${configForm.horario_fim || "--:--"}`,
        detail: `${configForm.intervalo_slot_minutos || 30} min por slot`,
      },
      {
        icon: CalendarDays,
        label: "Funcionamento",
        value: dias.length ? `${dias.length} dia(s)` : "Nao definido",
        detail: dias.length ? dias.join(", ") : "Configure os dias de atendimento",
      },
      {
        icon: Smartphone,
        label: "App do cliente",
        value: configForm.mostrar_calendario_cliente ? "Visivel" : "Oculto",
        detail: configForm.whatsapp_agendamento || "WhatsApp nao informado",
      },
    ];
  }, [configForm]);

  function updateConfig(field, value) {
    setConfigForm((prev) => ({ ...prev, [field]: value }));
  }

  function updatePorte(field, value) {
    setPorteForm((prev) => ({ ...prev, [field]: value }));
  }

  function scrollTo(ref) {
    window.setTimeout(() => {
      ref.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 0);
  }

  function abrirConfig() {
    setConfigOpen(true);
    setPorteFormOpen(false);
    scrollTo(configPanelRef);
  }

  function abrirNovoPorte() {
    setEditingPorte(null);
    setPorteForm(initialPorteForm);
    setPorteFormOpen(true);
    setConfigOpen(false);
    scrollTo(portePanelRef);
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
        custo_rateio_operacional_padrao: toApiDecimal(configForm.custo_rateio_operacional_padrao),
        horas_produtivas_mes_padrao: toApiDecimal(configForm.horas_produtivas_mes_padrao, "176"),
        mostrar_calendario_cliente: Boolean(configForm.mostrar_calendario_cliente),
        whatsapp_agendamento: configForm.whatsapp_agendamento || null,
      });
      toast.success("Parametros salvos.");
      setConfigOpen(false);
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
    setPorteFormOpen(true);
    setConfigOpen(false);
    scrollTo(portePanelRef);
  }

  function cancelarEdicaoPorte() {
    setEditingPorte(null);
    setPorteForm(initialPorteForm);
    setPorteFormOpen(false);
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
    return <LoadingState label="Carregando parametros..." />;
  }

  return (
    <div className="space-y-4">
      <Panel
        actions={
          <>
            <ActionButton icon={Settings} intent="neutral" onClick={abrirConfig} tone="soft">
              Configuracoes gerais
            </ActionButton>
            <ActionButton icon={Plus} intent="create" onClick={abrirNovoPorte}>
              Novo porte
            </ActionButton>
          </>
        }
        className="border-slate-200"
        subtitle="Use esta tela para manter portes e custos esperados. As configuracoes completas ficam em edicao separada."
        title="Parametros de Banho & Tosa"
      >
        <div className="grid gap-3 md:grid-cols-3">
          {resumo.map((item) => (
            <ResumoItem key={item.label} {...item} />
          ))}
        </div>
      </Panel>

      {configOpen && (
        <Panel
          ref={configPanelRef}
          actions={
            <ActionButton
              aria-label="Fechar configuracoes gerais"
              icon={X}
              intent="neutral"
              onClick={() => setConfigOpen(false)}
              tone="ghost"
            >
              Fechar
            </ActionButton>
          }
          subtitle="Ajustes gerais de agenda, app do cliente e custos usados como base nos calculos."
          title="Configuracoes gerais"
        >
          <form onSubmit={salvarConfig} className="space-y-5">
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">Agenda no app do cliente</h3>
                  <p className="mt-1 text-sm text-slate-500">
                    O cliente ve horarios livres e ocupados sem nomes de pets e chama a loja pelo
                    WhatsApp.
                  </p>
                </div>
                <CheckboxField
                  checked={Boolean(configForm.mostrar_calendario_cliente)}
                  label="Mostrar no app"
                  labelAccessory={
                    <BanhoTosaHelpTooltip text="Quando ativo, o app mostra horarios livres/ocupados sem revelar nomes dos pets." />
                  }
                  onChange={(value) => updateConfig("mostrar_calendario_cliente", value)}
                />
              </div>
              <div className="mt-4">
                <TextField
                  label="WhatsApp de agendamento"
                  labelAccessory={tooltip(
                    "Numero usado no app para abrir a conversa de agendamento. Pode informar com DDD.",
                  )}
                  onChange={(value) => updateConfig("whatsapp_agendamento", value)}
                  value={configForm.whatsapp_agendamento}
                />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <TextField
                label="Inicio"
                onChange={(value) => updateConfig("horario_inicio", value)}
                type="time"
                value={configForm.horario_inicio}
              />
              <TextField
                label="Fim"
                onChange={(value) => updateConfig("horario_fim", value)}
                type="time"
                value={configForm.horario_fim}
              />
              <TextField
                label="Slot agenda (min)"
                labelAccessory={tooltip(
                  "Intervalo usado para montar a grade de horarios e sugerir encaixes.",
                )}
                onChange={(value) => updateConfig("intervalo_slot_minutos", value)}
                type="number"
                value={configForm.intervalo_slot_minutos}
              />
              <TextField
                label="Dias funcionamento"
                labelAccessory={tooltip(
                  "Informe os dias separados por virgula: segunda,terca,quarta...",
                )}
                onChange={(value) => updateConfig("dias_funcionamento", value)}
                value={configForm.dias_funcionamento}
              />
              <TextField
                label="Custo litro agua"
                labelAccessory={tooltip("Valor medio da agua e esgoto dividido por litro.")}
                onChange={(value) => updateConfig("custo_litro_agua", value)}
                type="number"
                value={configForm.custo_litro_agua}
              />
              <TextField
                label="Vazao chuveiro L/min"
                labelAccessory={tooltip(
                  "Quantos litros o chuveiro consome por minuto durante o banho.",
                )}
                onChange={(value) => updateConfig("vazao_chuveiro_litros_min", value)}
                type="number"
                value={configForm.vazao_chuveiro_litros_min}
              />
              <TextField
                label="Custo kWh"
                labelAccessory={tooltip(
                  "Valor medio do kWh usado para calcular secador, soprador e equipamentos.",
                )}
                onChange={(value) => updateConfig("custo_kwh", value)}
                type="number"
                value={configForm.custo_kwh}
              />
              <TextField
                label="Toalha por banho"
                labelAccessory={tooltip(
                  "Custo medio de lavanderia, desgaste ou aluguel de toalha por atendimento.",
                )}
                onChange={(value) => updateConfig("custo_toalha_padrao", value)}
                type="number"
                value={configForm.custo_toalha_padrao}
              />
              <TextField
                label="Higienizacao por banho"
                labelAccessory={tooltip(
                  "Produtos de limpeza, desinfeccao de mesa/banheira e descartaveis.",
                )}
                onChange={(value) => updateConfig("custo_higienizacao_padrao", value)}
                type="number"
                value={configForm.custo_higienizacao_padrao}
              />
              <TextField
                label="% taxas padrao"
                labelAccessory={tooltip(
                  "Percentual medio de cartao, app ou taxa operacional sobre a venda.",
                )}
                onChange={(value) => updateConfig("percentual_taxas_padrao", value)}
                type="number"
                value={configForm.percentual_taxas_padrao}
              />
              <TextField
                label="Rateio operacional"
                labelAccessory={tooltip(
                  "Parcela media de aluguel, recepcao, limpeza e despesas fixas por atendimento.",
                )}
                onChange={(value) => updateConfig("custo_rateio_operacional_padrao", value)}
                type="number"
                value={configForm.custo_rateio_operacional_padrao}
              />
              <TextField
                label="Horas produtivas mes"
                labelAccessory={tooltip(
                  "Horas mensais usadas para ratear salario/custo do funcionario nos atendimentos.",
                )}
                onChange={(value) => updateConfig("horas_produtivas_mes_padrao", value)}
                type="number"
                value={configForm.horas_produtivas_mes_padrao}
              />
            </div>

            <div className="flex flex-wrap justify-end gap-2">
              <ActionButton intent="neutral" onClick={() => setConfigOpen(false)} tone="soft">
                Cancelar
              </ActionButton>
              <ActionButton intent="edit" loading={savingConfig} type="submit">
                Salvar configuracoes
              </ActionButton>
            </div>
          </form>
        </Panel>
      )}

      {porteFormOpen && (
        <div ref={portePanelRef}>
          <BanhoTosaPorteForm
            editing={Boolean(editingPorte)}
            form={porteForm}
            onCancelEdit={cancelarEdicaoPorte}
            onChangeField={updatePorte}
            onSubmit={salvarPorte}
            saving={savingPorte}
          />
        </div>
      )}

      <BanhoTosaParametrosLista
        onDelete={excluirPorte}
        onEdit={editarPorte}
        onToggleAtivo={togglePorteAtivo}
        parametros={parametros}
      />
    </div>
  );
}

function ResumoItem({ detail, icon: Icon, label, value }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        <Icon className="h-4 w-4 text-blue-600" aria-hidden="true" />
        {label}
      </div>
      <div className="mt-2 text-base font-semibold text-slate-900">{value}</div>
      <div className="mt-1 truncate text-sm text-slate-500" title={detail}>
        {detail}
      </div>
    </div>
  );
}

function tooltip(text) {
  return <BanhoTosaHelpTooltip text={text} />;
}
