import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { AlertTriangle, RefreshCw } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
import EmptyState from "../../../components/ui/EmptyState";
import { TextField } from "../../../components/ui/FormField";
import MetricCard from "../../../components/ui/MetricCard";
import MetricGrid from "../../../components/ui/MetricGrid";
import Panel from "../../../components/ui/Panel";
import { banhoTosaApi } from "../banhoTosaApi";
import { formatCurrency, formatNumber, getApiErrorMessage } from "../banhoTosaUtils";

const todayIso = () => new Date().toISOString().slice(0, 10);
const monthStartIso = () => {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
};

export default function BanhoTosaRelatoriosView() {
  const [dataInicio, setDataInicio] = useState(monthStartIso());
  const [dataFim, setDataFim] = useState(todayIso());
  const [relatorio, setRelatorio] = useState(null);
  const [loading, setLoading] = useState(false);

  async function carregarRelatorio() {
    setLoading(true);
    try {
      const response = await banhoTosaApi.relatorioOperacional({
        data_inicio: dataInicio,
        data_fim: dataFim,
      });
      setRelatorio(response.data || null);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel carregar relatorios."));
      setRelatorio(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    carregarRelatorio();
  }, []);

  const resumo = relatorio?.resumo || {};

  return (
    <div className="space-y-4">
      <Panel
        actions={
          <ActionButton icon={RefreshCw} intent="neutral" loading={loading} onClick={carregarRelatorio} tone="soft">
            Atualizar
          </ActionButton>
        }
        subtitle="Margem, ocupacao, produtividade e desperdicio do Banho & Tosa."
        title="Relatorios operacionais"
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <TextField label="Inicio" type="date" value={dataInicio} onChange={setDataInicio} />
          <TextField label="Fim" type="date" value={dataFim} onChange={setDataFim} />
        </div>
      </Panel>

      <MetricGrid className="xl:grid-cols-5">
        <MetricCard intent="emerald" label="Receita" value={formatCurrency(resumo.receita)} />
        <MetricCard intent="blue" label="Margem" subtitle={`${formatNumber(resumo.margem_percentual, 1)}%`} value={formatCurrency(resumo.margem_valor)} />
        <MetricCard intent="slate" label="Ticket medio" subtitle={`${resumo.atendimentos || 0} atendimentos`} value={formatCurrency(resumo.ticket_medio)} />
        <MetricCard intent="cyan" label="Ocupacao media" subtitle={`${resumo.agendamentos || 0} agendamentos`} value={`${formatNumber(resumo.ocupacao_media_percentual, 1)}%`} />
        <MetricCard intent="violet" label="NPS" subtitle={`${resumo.avaliacoes || 0} avaliacoes`} value={formatNumber(resumo.nps, 0)} />
      </MetricGrid>

      {relatorio?.alertas?.length > 0 ? (
        <Panel className="border-amber-200 bg-amber-50" padding="sm">
          <div className="flex items-start gap-2 text-sm font-medium text-amber-800">
            <AlertTriangle size={18} className="mt-0.5 shrink-0" />
            <div className="space-y-1">
              {relatorio.alertas.map((alerta) => (
                <p key={alerta}>{alerta}</p>
              ))}
            </div>
          </div>
        </Panel>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-2">
        <TableCard title="Margem por servico">
          <MarginRows items={relatorio?.margem_por_servico || []} />
        </TableCard>
        <TableCard title="Margem por porte">
          <MarginRows items={relatorio?.margem_por_porte || []} />
        </TableCard>
        <TableCard title="Produtividade">
          <ProdutividadeRows items={relatorio?.produtividade || []} />
        </TableCard>
        <TableCard title="Ocupacao por recurso">
          <OcupacaoRows items={relatorio?.ocupacao_recursos || []} />
        </TableCard>
        <TableCard title="Desperdicio de insumos" wide>
          <DesperdicioRows items={relatorio?.desperdicios || []} />
        </TableCard>
      </div>
    </div>
  );
}

function MarginRows({ items }) {
  if (!items.length) return <EmptyRows />;
  return items.slice(0, 8).map((item) => (
    <Row key={item.chave}>
      <Cell title={item.nome} subtitle={`${item.atendimentos} atend.`} />
      <Cell title={formatCurrency(item.receita)} subtitle="receita" align="right" />
      <Cell title={formatCurrency(item.margem_valor)} subtitle={`${formatNumber(item.margem_percentual, 1)}%`} align="right" />
    </Row>
  ));
}

function ProdutividadeRows({ items }) {
  if (!items.length) return <EmptyRows />;
  return items.slice(0, 8).map((item) => (
    <Row key={item.responsavel_id}>
      <Cell title={item.responsavel_nome} subtitle={`${item.atendimentos} atend.`} />
      <Cell title={`${formatNumber(item.horas_trabalhadas, 1)}h`} subtitle={`${item.etapas} etapas`} align="right" />
      <Cell title={`${item.minutos_trabalhados} min`} subtitle="tempo total" align="right" />
    </Row>
  ));
}

function OcupacaoRows({ items }) {
  if (!items.length) return <EmptyRows />;
  return items.slice(0, 8).map((item) => (
    <Row key={item.recurso_id}>
      <Cell title={item.recurso_nome} subtitle={item.recurso_tipo} />
      <Cell title={`${formatNumber(item.ocupacao_percentual, 1)}%`} subtitle="ocupacao" align="right" />
      <Cell title={`${item.minutos_ocupados} min`} subtitle={`${item.minutos_disponiveis} disp.`} align="right" />
    </Row>
  ));
}

function DesperdicioRows({ items }) {
  if (!items.length) return <EmptyRows />;
  return items.slice(0, 8).map((item) => (
    <Row key={item.produto_id}>
      <Cell title={item.produto_nome} subtitle={item.unidade || "unidade"} />
      <Cell title={formatNumber(item.quantidade_desperdicio, 3)} subtitle="qtd desperdicada" align="right" />
      <Cell title={formatCurrency(item.custo_desperdicio)} subtitle="custo" align="right" />
    </Row>
  ));
}

function TableCard({ title, children, wide = false }) {
  return (
    <Panel className={wide ? "xl:col-span-2" : ""} title={title}>
      <div className="divide-y divide-slate-100">{children}</div>
    </Panel>
  );
}

function Row({ children }) {
  return <div className="grid grid-cols-[1.2fr_0.8fr_0.8fr] gap-3 py-3">{children}</div>;
}

function Cell({ title, subtitle, align = "left" }) {
  const classes = align === "right" ? "text-right" : "text-left";
  return (
    <div className={classes}>
      <p className="truncate text-sm font-semibold text-slate-900">{title}</p>
      <p className="truncate text-xs text-slate-500">{subtitle}</p>
    </div>
  );
}

function EmptyRows() {
  return (
    <EmptyState
      compact
      className="my-2"
      description="Ajuste o periodo ou aguarde novos atendimentos."
      title="Sem dados no periodo"
    />
  );
}
