import { useState } from "react";
import { Calculator, Settings } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
import MetricCard from "../../../components/ui/MetricCard";
import MetricGrid from "../../../components/ui/MetricGrid";
import Panel from "../../../components/ui/Panel";
import BanhoTosaDefaultsPanel from "./BanhoTosaDefaultsPanel";
import BanhoTosaSimulador from "./BanhoTosaSimulador";

export default function BanhoTosaDashboardView({ dashboard, config, parametros, onChanged }) {
  const [mostrarBase, setMostrarBase] = useState(false);
  const [mostrarSimulador, setMostrarSimulador] = useState(false);
  const parametrosAtivos = parametros.filter((item) => item.ativo).length;
  const fluxoVisual = montarFluxoVisual(config?.fluxo_etapas);

  return (
    <div className="space-y-4">
      <Panel
        actions={
          <>
            <ActionButton
              icon={Settings}
              intent="neutral"
              onClick={() => setMostrarBase((value) => !value)}
              tone="soft"
            >
              Base padrao
            </ActionButton>
            <ActionButton
              icon={Calculator}
              intent="info"
              onClick={() => setMostrarSimulador((value) => !value)}
              tone="soft"
            >
              Simular margem
            </ActionButton>
          </>
        }
        subtitle="Acompanhe o dia e acesse ferramentas quando precisar, sem carregar a tela com formularios."
        title="Painel operacional"
      >
        <MetricGrid>
          <MetricCard
            intent="amber"
            label="Agenda do dia"
            subtitle="Ainda nao finalizados"
            value={dashboard?.agendamentos_abertos ?? 0}
          />
          <MetricCard
            intent="blue"
            label="Em execucao"
            subtitle="Banho, secagem ou tosa"
            value={dashboard?.atendimentos_em_execucao ?? 0}
          />
          <MetricCard
            intent="emerald"
            label="Prontos"
            subtitle="Retirada ou taxi dog"
            value={dashboard?.atendimentos_prontos ?? 0}
          />
          <MetricCard
            intent="slate"
            label="Entregues hoje"
            subtitle="Atendimentos encerrados"
            value={dashboard?.atendimentos_entregues ?? 0}
          />
          <MetricCard
            intent="amber"
            label="Sem venda"
            subtitle="Aguardando envio ao PDV"
            value={dashboard?.atendimentos_prontos_sem_venda ?? 0}
          />
          <MetricCard
            intent="amber"
            label="Cobranca pend."
            subtitle="Venda ainda aberta"
            value={dashboard?.cobrancas_pendentes ?? 0}
          />
          <MetricCard
            intent="emerald"
            label="NPS hoje"
            subtitle={`${dashboard?.avaliacoes_hoje || 0} avaliacao(es)`}
            value={formatNps(dashboard?.nps_hoje)}
          />
          <MetricCard
            intent="blue"
            label="Servicos ativos"
            subtitle={`${parametrosAtivos} porte(s) ativos`}
            value={dashboard?.servicos_ativos ?? 0}
          />
        </MetricGrid>
      </Panel>

      {mostrarBase && <BanhoTosaDefaultsPanel onApplied={onChanged} />}

      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <Panel
          subtitle="Cada etapa alimenta tempo, consumo, mao de obra e margem."
          title="Fluxo operacional"
        >
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {fluxoVisual.map((etapa, index) => (
              <div
                key={etapa.codigo}
                className="rounded-lg border border-slate-200 bg-slate-50 p-4"
              >
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-sm font-semibold text-white">
                  {index + 1}
                </span>
                <p className="mt-3 font-semibold text-slate-900">{etapa.label}</p>
                <p className="mt-1 text-sm text-slate-500">{etapa.descricao}</p>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Base de precificacao">
          <dl className="space-y-3 text-sm">
            <div className="flex flex-col gap-1 rounded-lg bg-slate-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
              <dt className="text-slate-500">Servicos ativos</dt>
              <dd className="font-semibold text-slate-900">{dashboard?.servicos_ativos ?? 0}</dd>
            </div>
            <div className="flex flex-col gap-1 rounded-lg bg-slate-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
              <dt className="text-slate-500">Portes ativos</dt>
              <dd className="font-semibold text-slate-900">{parametrosAtivos}</dd>
            </div>
            <div className="flex flex-col gap-1 rounded-lg bg-slate-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
              <dt className="text-slate-500">Horario base</dt>
              <dd className="font-semibold text-slate-900">
                {config?.horario_inicio || "08:00"} - {config?.horario_fim || "18:00"}
              </dd>
            </div>
          </dl>
        </Panel>
      </div>

      {mostrarSimulador && <BanhoTosaSimulador config={config} />}
    </div>
  );
}

function formatNps(value) {
  const numero = Number(value || 0);
  return Number.isFinite(numero) ? numero.toFixed(0) : "0";
}

function montarFluxoVisual(fluxoConfigurado) {
  const descricoes = {
    chegou: "Check-in registra o pet na fila e preserva as atenções do cadastro.",
    preparo: "Organiza materiais, responsável e box antes do serviço.",
    banho: "Inicia o timer e acompanha responsável, recurso e consumo.",
    secagem: "Continua a cronometragem e evidencia atrasos da operação.",
    higiene: "Registra os cuidados complementares executados.",
    tosa: "Controla tempo, profissional e observações da finalização.",
    pronto: "Revisa ficha, fotos, ocorrências, custos e cobrança.",
  };
  const labels = {
    chegou: "Chegou",
    preparo: "Preparo",
    banho: "Banho",
    secagem: "Secagem",
    higiene: "Higiene",
    tosa: "Tosa",
    pronto: "Pronto",
  };
  const fluxo =
    Array.isArray(fluxoConfigurado) && fluxoConfigurado.length
      ? fluxoConfigurado
      : ["chegou", "banho", "secagem", "tosa", "pronto"];
  const etapas = fluxo
    .filter((codigo, index, lista) => labels[codigo] && lista.indexOf(codigo) === index)
    .map((codigo) => ({ codigo, label: labels[codigo], descricao: descricoes[codigo] }));
  return [
    {
      codigo: "agendamento",
      label: "Agendamento",
      descricao: "Reserva horário, profissional, serviço, valor e recurso.",
    },
    ...etapas,
    {
      codigo: "entregue",
      label: "Fechamento e entrega",
      descricao: "Gera a venda no PDV, sincroniza o financeiro e encerra o atendimento.",
    },
  ];
}
