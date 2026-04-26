import { useEffect, useState } from "react";
import toast from "react-hot-toast";
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
    <div className="space-y-6">
      <section className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
              Relatorios
            </p>
            <h2 className="mt-2 text-2xl font-black text-slate-900">
              Performance operacional
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Margem, ocupacao, produtividade e desperdicio do Banho & Tosa.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
            <DateField label="Inicio" value={dataInicio} onChange={setDataInicio} />
            <DateField label="Fim" value={dataFim} onChange={setDataFim} />
            <button
              type="button"
              disabled={loading}
              onClick={carregarRelatorio}
              className="self-end rounded-2xl bg-slate-900 px-5 py-3 text-sm font-bold text-white transition hover:bg-slate-700 disabled:opacity-60"
            >
              {loading ? "Carregando..." : "Atualizar"}
            </button>
          </div>
        </div>
      </section>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Receita" value={formatCurrency(resumo.receita)} />
        <MetricCard label="Margem" value={formatCurrency(resumo.margem_valor)} detail={`${formatNumber(resumo.margem_percentual, 1)}%`} />
        <MetricCard label="Ticket medio" value={formatCurrency(resumo.ticket_medio)} detail={`${resumo.atendimentos || 0} atendimentos`} />
        <MetricCard label="Ocupacao media" value={`${formatNumber(resumo.ocupacao_media_percentual, 1)}%`} detail={`${resumo.agendamentos || 0} agendamentos`} />
        <MetricCard label="NPS" value={formatNumber(resumo.nps, 0)} detail={`${resumo.avaliacoes || 0} avaliacoes`} />
      </div>

      {relatorio?.alertas?.length > 0 && (
        <div className="rounded-3xl border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-800">
          {relatorio.alertas.map((alerta) => (
            <p key={alerta}>{alerta}</p>
          ))}
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-2">
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

function MetricCard({ label, value, detail }) {
  return (
    <div className="rounded-3xl border border-white/80 bg-white p-5 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">{label}</p>
      <p className="mt-2 text-2xl font-black text-slate-900">{value}</p>
      {detail && <p className="mt-1 text-sm font-semibold text-slate-500">{detail}</p>}
    </div>
  );
}

function TableCard({ title, children, wide = false }) {
  return (
    <section className={`rounded-3xl border border-white/80 bg-white p-5 shadow-sm ${wide ? "xl:col-span-2" : ""}`}>
      <h3 className="text-lg font-black text-slate-900">{title}</h3>
      <div className="mt-4 divide-y divide-slate-100">{children}</div>
    </section>
  );
}

function Row({ children }) {
  return <div className="grid grid-cols-[1.2fr_0.8fr_0.8fr] gap-3 py-3">{children}</div>;
}

function Cell({ title, subtitle, align = "left" }) {
  const classes = align === "right" ? "text-right" : "text-left";
  return (
    <div className={classes}>
      <p className="truncate text-sm font-black text-slate-900">{title}</p>
      <p className="truncate text-xs font-semibold text-slate-400">{subtitle}</p>
    </div>
  );
}

function EmptyRows() {
  return (
    <p className="rounded-2xl border border-dashed border-slate-300 p-4 text-sm text-slate-500">
      Sem dados no periodo.
    </p>
  );
}

function DateField({ label, value, onChange }) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{label}</span>
      <input
        type="date"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100"
      />
    </label>
  );
}
