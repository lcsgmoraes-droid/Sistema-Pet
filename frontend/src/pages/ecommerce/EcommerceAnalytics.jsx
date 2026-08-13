import { useEffect, useState } from "react";
import { AlertTriangle, BarChart3, PackageCheck, RefreshCw, ShoppingBag } from "lucide-react";
import { api } from "../../services/api";
import { formatMoneyBRL } from "../../utils/formatters";

const STATUS_LABEL = {
  criado: ["Aguardando", "#92400e", "#fef3c7"],
  pendente: ["Pagamento pendente", "#92400e", "#fef3c7"],
  aprovado: ["Aprovado", "#047857", "#d1fae5"],
  finalizado: ["Finalizado", "#047857", "#d1fae5"],
  pago: ["Pago", "#047857", "#d1fae5"],
  entregue: ["Entregue", "#4338ca", "#e0e7ff"],
  cancelado: ["Cancelado", "#b91c1c", "#fee2e2"],
};

function StatusBadge({ status }) {
  const [label, color, background] = STATUS_LABEL[status] || [status || "-", "#4b5563", "#f3f4f6"];
  return (
    <span
      style={{ background, color }}
      className="inline-flex rounded-full px-2.5 py-1 text-xs font-semibold"
    >
      {label}
    </span>
  );
}

function MetricCard({ label, value, sub, tone = "indigo" }) {
  const colors = {
    indigo: "text-indigo-700 bg-indigo-50",
    green: "text-emerald-700 bg-emerald-50",
    amber: "text-amber-700 bg-amber-50",
    red: "text-red-700 bg-red-50",
  };
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className={`inline-flex rounded-lg px-2.5 py-1 text-xs font-bold ${colors[tone]}`}>
        {label}
      </div>
      <div className="mt-3 text-2xl font-bold text-gray-900">{value}</div>
      {sub && <div className="mt-1 text-xs text-gray-500">{sub}</div>}
    </div>
  );
}

function Panel({ title, subtitle, children }) {
  return (
    <section className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      <div className="border-b border-gray-100 px-5 py-4">
        <h2 className="font-bold text-gray-900">{title}</h2>
        {subtitle && <p className="mt-1 text-xs text-gray-500">{subtitle}</p>}
      </div>
      {children}
    </section>
  );
}

function formatDate(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function EcommerceAnalytics() {
  const [days, setDays] = useState(30);
  const [channel, setChannel] = useState("ecommerce");
  const [data, setData] = useState({
    resumo: null,
    funil: [],
    saude: null,
    demanda: [],
    maisVendidos: [],
    pedidos: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      setError("");
      const params = { dias: days, canal: channel };
      try {
        const [resumo, funil, saude, demanda, maisVendidos, pedidos] = await Promise.all([
          api.get("/ecommerce-analytics/resumo", { params }),
          api.get("/ecommerce-analytics/funil", { params }),
          api.get("/ecommerce-analytics/catalogo-saude"),
          api.get("/ecommerce-analytics/demanda", { params: { dias: days } }),
          api.get("/ecommerce-analytics/mais-vendidos", { params }),
          api.get("/ecommerce-analytics/pedidos-recentes", { params }),
        ]);
        if (!active) return;
        setData({
          resumo: resumo.data,
          funil: funil.data?.etapas || [],
          saude: saude.data,
          demanda: demanda.data || [],
          maisVendidos: maisVendidos.data || [],
          pedidos: pedidos.data || [],
        });
      } catch (requestError) {
        if (active) {
          setError(
            requestError?.response?.data?.detail ||
              "Não foi possível carregar os dados do e-commerce.",
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    return () => {
      active = false;
    };
  }, [channel, days, refreshKey]);

  const { resumo, funil, saude, demanda, maisVendidos, pedidos } = data;

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-8">
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex items-center gap-2 text-indigo-700">
            <BarChart3 size={24} />
            <h1 className="text-2xl font-bold text-gray-900">Analytics do e-commerce</h1>
          </div>
          <p className="mt-1 text-sm text-gray-500">
            Vendas, funil de compra e qualidade do catálogo em uma única visão.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <select
            id="ecommerce-analytics-period"
            name="analytics_period"
            aria-label="Período do relatório"
            value={days}
            onChange={(event) => setDays(Number(event.target.value))}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
          >
            <option value={7}>Últimos 7 dias</option>
            <option value={30}>Últimos 30 dias</option>
            <option value={90}>Últimos 90 dias</option>
            <option value={365}>Último ano</option>
          </select>
          <select
            id="ecommerce-analytics-channel"
            name="analytics_channel"
            aria-label="Canal de vendas"
            value={channel}
            onChange={(event) => setChannel(event.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
          >
            <option value="ecommerce">Site</option>
            <option value="app">App</option>
            <option value="marketplace">Marketplace</option>
            <option value="todos">Todos os canais</option>
          </select>
          <button
            type="button"
            onClick={() => setRefreshKey((value) => value + 1)}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-semibold text-gray-700 disabled:opacity-50"
          >
            <RefreshCw size={15} className={loading ? "animate-spin" : ""} />
            Atualizar
          </button>
        </div>
      </header>

      {error && (
        <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertTriangle size={18} />
          {error}
        </div>
      )}

      {loading && !resumo ? (
        <div className="rounded-xl border border-gray-200 bg-white p-12 text-center text-gray-500">
          Carregando indicadores...
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              label="Pedidos pagos"
              value={resumo?.total_pedidos ?? 0}
              sub={`${resumo?.pedidos_hoje ?? 0} hoje`}
            />
            <MetricCard
              label="Receita"
              value={formatMoneyBRL(resumo?.receita_total)}
              sub={`Ticket médio: ${formatMoneyBRL(resumo?.ticket_medio)}`}
              tone="green"
            />
            <MetricCard
              label="Carrinhos abandonados"
              value={resumo?.carrinhos_abandonados ?? 0}
              sub="Sem finalizar há mais de uma hora"
              tone="amber"
            />
            <MetricCard
              label="Pedidos de reposição"
              value={resumo?.avise_me_pendentes ?? 0}
              sub="Clientes aguardando estoque"
              tone="red"
            />
          </div>

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <Panel
              title="Funil de compra"
              subtitle="Sessões anônimas; compras usam pedidos aprovados."
            >
              <div className="space-y-4 p-5">
                {funil.map((step, index) => {
                  const max = Math.max(funil[0]?.sessoes || 0, 1);
                  const width = Math.max((Number(step.sessoes || 0) / max) * 100, 2);
                  return (
                    <div key={step.evento}>
                      <div className="mb-1 flex items-center justify-between gap-3 text-sm">
                        <span className="font-medium text-gray-700">
                          {index + 1}. {step.label}
                        </span>
                        <span className="text-gray-500">
                          {step.sessoes} · {step.conversao_visita}% das visitas
                        </span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-gray-100">
                        <div
                          className="h-full rounded-full bg-indigo-500"
                          style={{ width: `${width}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </Panel>

            <Panel
              title="Saúde do catálogo"
              subtitle="Itens publicados e o que falta para vender com confiança."
            >
              <div className="grid grid-cols-2 gap-3 p-5 sm:grid-cols-3">
                <MetricCard
                  label="Prontos"
                  value={saude?.prontos_para_venda ?? 0}
                  sub={`${saude?.percentual_pronto ?? 0}% do catálogo`}
                  tone="green"
                />
                {[
                  ["Sem estoque", "sem_estoque"],
                  ["Sem imagem", "sem_imagem"],
                  ["Sem descrição", "sem_descricao"],
                  ["Sem categoria", "sem_categoria"],
                  ["Sem preço", "sem_preco"],
                ].map(([label, key]) => (
                  <MetricCard key={key} label={label} value={saude?.[key] ?? 0} tone="amber" />
                ))}
              </div>
            </Panel>
          </div>

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <Panel title="Mais vendidos" subtitle="Quantidade e receita dos produtos pagos.">
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
                    <tr>
                      <th className="px-4 py-3">Produto</th>
                      <th className="px-4 py-3 text-right">Qtd.</th>
                      <th className="px-4 py-3 text-right">Receita</th>
                    </tr>
                  </thead>
                  <tbody>
                    {maisVendidos.map((item) => (
                      <tr key={item.produto_id} className="border-t border-gray-100">
                        <td className="px-4 py-3 font-medium text-gray-800">{item.nome}</td>
                        <td className="px-4 py-3 text-right">{item.total_vendido}</td>
                        <td className="px-4 py-3 text-right text-emerald-700">
                          {formatMoneyBRL(item.receita)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!maisVendidos.length && (
                  <div className="p-8 text-center text-sm text-gray-400">
                    Nenhuma venda no período.
                  </div>
                )}
              </div>
            </Panel>

            <Panel title="Demanda reprimida" subtitle="Produtos que clientes pediram para avisar.">
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
                    <tr>
                      <th className="px-4 py-3">Produto</th>
                      <th className="px-4 py-3 text-center">Aguardando</th>
                      <th className="px-4 py-3 text-right">Estoque</th>
                    </tr>
                  </thead>
                  <tbody>
                    {demanda.map((item) => (
                      <tr key={item.product_id} className="border-t border-gray-100">
                        <td className="px-4 py-3">
                          <div className="font-medium text-gray-800">{item.product_name}</div>
                          <div className="text-xs text-gray-400">{item.codigo || "-"}</div>
                        </td>
                        <td className="px-4 py-3 text-center font-bold text-red-600">
                          {item.pendentes}
                        </td>
                        <td className="px-4 py-3 text-right">{item.estoque_atual}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!demanda.length && (
                  <div className="p-8 text-center text-sm text-gray-400">
                    Nenhum pedido de reposição no período.
                  </div>
                )}
              </div>
            </Panel>
          </div>

          <Panel
            title="Pedidos recentes"
            subtitle="Últimos pedidos pagos do período e canal selecionados."
          >
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
                  <tr>
                    <th className="px-4 py-3">Pedido</th>
                    <th className="px-4 py-3">Canal</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-center">Itens</th>
                    <th className="px-4 py-3 text-right">Total</th>
                    <th className="px-4 py-3 text-right">Data</th>
                  </tr>
                </thead>
                <tbody>
                  {pedidos.map((item) => (
                    <tr key={item.pedido_id} className="border-t border-gray-100">
                      <td className="px-4 py-3 font-mono text-xs text-gray-600">
                        {item.pedido_id?.slice(0, 10)}…
                      </td>
                      <td className="px-4 py-3 capitalize text-gray-600">{item.origem}</td>
                      <td className="px-4 py-3">
                        <StatusBadge status={item.status} />
                      </td>
                      <td className="px-4 py-3 text-center">{item.qtd_itens}</td>
                      <td className="px-4 py-3 text-right font-semibold">
                        {formatMoneyBRL(item.total)}
                      </td>
                      <td className="px-4 py-3 text-right text-xs text-gray-500">
                        {formatDate(item.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!pedidos.length && (
                <div className="flex items-center justify-center gap-2 p-10 text-sm text-gray-400">
                  <ShoppingBag size={18} /> Nenhum pedido pago no período.
                </div>
              )}
            </div>
          </Panel>

          <div className="flex items-start gap-3 rounded-xl border border-indigo-100 bg-indigo-50 p-4 text-sm text-indigo-800">
            <PackageCheck size={20} className="mt-0.5 shrink-0" />O funil interno funciona sem
            configurar o Google Analytics. Se um ID GA4 também for informado no ambiente, os dois
            rastreamentos funcionam juntos.
          </div>
        </>
      )}
    </div>
  );
}
