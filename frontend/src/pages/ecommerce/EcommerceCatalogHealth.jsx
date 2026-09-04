import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  AlertTriangle,
  BellRing,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  PackageSearch,
  RefreshCw,
} from "lucide-react";
import { api } from "../../services/api";
import { formatMoneyBRL } from "../../utils/formatters";

const PAGE_SIZE = 50;
const STATUS_META = {
  bloqueado: { label: "Bloqueado", className: "bg-red-100 text-red-700" },
  esgotado: { label: "Esgotado", className: "bg-amber-100 text-amber-800" },
  pendencias: { label: "Vendável com pendências", className: "bg-blue-100 text-blue-700" },
  pronto: { label: "Completo", className: "bg-emerald-100 text-emerald-700" },
};

function SummaryButton({ label, value, active, tone, onClick }) {
  const tones = {
    red: "border-red-200 bg-red-50 text-red-800",
    amber: "border-amber-200 bg-amber-50 text-amber-800",
    blue: "border-blue-200 bg-blue-50 text-blue-800",
    green: "border-emerald-200 bg-emerald-50 text-emerald-800",
    gray: "border-gray-200 bg-white text-gray-800",
  };
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-xl border p-4 text-left shadow-sm transition hover:-translate-y-0.5 ${
        tones[tone]
      } ${active ? "ring-2 ring-indigo-500 ring-offset-2" : ""}`}
    >
      <span className="block text-xs font-bold uppercase tracking-wide opacity-75">{label}</span>
      <span className="mt-1 block text-2xl font-bold">{value ?? 0}</span>
    </button>
  );
}

function IssueChip({ issue, blocking }) {
  return (
    <span
      className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${
        blocking ? "bg-red-50 text-red-700" : "bg-gray-100 text-gray-600"
      }`}
    >
      {issue.label}
    </span>
  );
}

export default function EcommerceCatalogHealth() {
  const [searchParams, setSearchParams] = useSearchParams();
  const channel = searchParams.get("canal") === "app" ? "app" : "ecommerce";
  const situation = searchParams.get("situacao") || "todos";
  const problem = searchParams.get("problema") || "";
  const search = searchParams.get("busca") || "";
  const page = Math.max(Number(searchParams.get("pagina") || 1), 1);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  function updateParams(changes) {
    const next = new URLSearchParams(searchParams);
    Object.entries(changes).forEach(([key, value]) => {
      if (value && value !== "todos") next.set(key, value);
      else next.delete(key);
    });
    if (!("pagina" in changes)) next.delete("pagina");
    setSearchParams(next);
  }

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(
      async () => {
        setLoading(true);
        setError("");
        try {
          const response = await api.get("/ecommerce-analytics/catalogo-saude/produtos", {
            params: {
              canal: channel,
              situacao: situation,
              problema: problem || undefined,
              busca: search || undefined,
              offset: (page - 1) * PAGE_SIZE,
              limit: PAGE_SIZE,
            },
          });
          if (active) setData(response.data);
        } catch (requestError) {
          if (active) {
            setError(
              requestError?.response?.data?.detail ||
                "Não foi possível carregar a saúde do catálogo.",
            );
          }
        } finally {
          if (active) setLoading(false);
        }
      },
      search ? 250 : 0,
    );
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [channel, page, problem, refreshKey, search, situation]);

  const summary = data?.resumo || {};
  const totalPages = Math.max(Math.ceil(Number(data?.total || 0) / PAGE_SIZE), 1);

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-8">
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <PackageSearch className="text-indigo-600" size={26} />
            <h1 className="text-2xl font-bold text-gray-900">Saúde do catálogo</h1>
          </div>
          <p className="mt-1 text-sm text-gray-500">
            Veja o que bloqueia uma publicação e quais informações podem melhorar seus filtros.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            to="/produtos/demanda-nao-atendida"
            className="inline-flex items-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-semibold text-indigo-700"
          >
            <BellRing size={15} /> Ver demanda dos clientes
          </Link>
          <select
            aria-label="Canal do catálogo"
            value={channel}
            onChange={(event) => updateParams({ canal: event.target.value })}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
          >
            <option value="ecommerce">E-commerce</option>
            <option value="app">App</option>
          </select>
          <button
            type="button"
            onClick={() => setRefreshKey((value) => value + 1)}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-semibold text-gray-700"
          >
            <RefreshCw size={15} className={loading ? "animate-spin" : ""} /> Atualizar
          </button>
        </div>
      </header>

      {data?.configuracao?.exibir_esgotados === false && (
        <div className="flex flex-col gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 md:flex-row md:items-center md:justify-between">
          <span>
            Produtos esgotados estão ocultos pela configuração atual e não recebem novos pedidos de
            Avise-me.
          </span>
          <Link className="font-bold text-amber-950 underline" to="/ecommerce/configuracoes">
            Alterar configuração
          </Link>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <SummaryButton
          label="Publicados"
          value={summary.publicados}
          active={situation === "todos"}
          tone="gray"
          onClick={() => updateParams({ situacao: "todos", problema: "" })}
        />
        <SummaryButton
          label="Bloqueados"
          value={summary.bloqueados}
          active={situation === "bloqueado"}
          tone="red"
          onClick={() => updateParams({ situacao: "bloqueado", problema: "" })}
        />
        <SummaryButton
          label="Esgotados"
          value={summary.esgotados}
          active={situation === "esgotado"}
          tone="amber"
          onClick={() => updateParams({ situacao: "esgotado", problema: "" })}
        />
        <SummaryButton
          label="Dados faltantes"
          value={summary.com_pendencias}
          active={situation === "pendencias"}
          tone="blue"
          onClick={() => updateParams({ situacao: "pendencias", problema: "" })}
        />
        <SummaryButton
          label="Completos"
          value={summary.sem_pendencias}
          active={situation === "pronto"}
          tone="green"
          onClick={() => updateParams({ situacao: "pronto", problema: "" })}
        />
      </div>

      <section className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <input
            aria-label="Buscar produto no catálogo"
            value={search}
            onChange={(event) => updateParams({ busca: event.target.value })}
            placeholder="Buscar por nome ou código..."
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
          <select
            aria-label="Filtrar situação do catálogo"
            value={situation}
            onChange={(event) => updateParams({ situacao: event.target.value })}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="todos">Todas as situações</option>
            <option value="bloqueado">Bloqueados</option>
            <option value="esgotado">Esgotados</option>
            <option value="pendencias">Vendáveis com dados faltantes</option>
            <option value="pronto">Completos</option>
          </select>
          <select
            aria-label="Filtrar dado faltante"
            value={problem}
            onChange={(event) => updateParams({ problema: event.target.value })}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="">Todos os motivos</option>
            <option value="sem_preco">Sem preço (bloqueante)</option>
            <option value="sem_estoque">Sem estoque</option>
            <option value="sem_imagem">Sem imagem</option>
            <option value="sem_descricao">Sem descrição</option>
            <option value="sem_categoria">Sem categoria</option>
            <option value="sem_marca">Sem marca</option>
          </select>
        </div>
      </section>

      {error && (
        <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <AlertTriangle size={18} /> {error}
        </div>
      )}

      <section className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3">Produto</th>
                <th className="px-4 py-3">Situação</th>
                <th className="px-4 py-3">Motivos / dados faltantes</th>
                <th className="px-4 py-3 text-center">Avise-me</th>
                <th className="px-4 py-3 text-right">Estoque</th>
                <th className="px-4 py-3 text-right">Preço</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {(data?.itens || []).map((item) => {
                const meta = STATUS_META[item.status] || STATUS_META.pendencias;
                return (
                  <tr key={item.id} className="border-t border-gray-100 align-top">
                    <td className="px-4 py-3">
                      <div className="font-semibold text-gray-900">{item.nome}</div>
                      <div className="text-xs text-gray-400">
                        {item.codigo || "Sem código"} · {item.marca_nome || "Sem marca"}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-1 text-xs font-bold ${meta.className}`}
                      >
                        {meta.label}
                      </span>
                    </td>
                    <td className="max-w-md px-4 py-3">
                      <div className="flex flex-wrap gap-1.5">
                        {item.bloqueios.map((issue) => (
                          <IssueChip key={issue.codigo} issue={issue} blocking />
                        ))}
                        {item.pendencias.map((issue) => (
                          <IssueChip key={issue.codigo} issue={issue} />
                        ))}
                        {!item.bloqueios.length && !item.pendencias.length && (
                          <span className="inline-flex items-center gap-1 text-emerald-700">
                            <CheckCircle2 size={15} /> Sem pendências
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {item.avise_me_pendentes > 0 ? (
                        <span className="inline-flex items-center gap-1 font-bold text-indigo-700">
                          <BellRing size={15} /> {item.avise_me_pendentes}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-medium">{item.estoque}</td>
                    <td className="px-4 py-3 text-right">{formatMoneyBRL(item.preco)}</td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/produtos/${item.id}/editar`}
                        className="inline-flex items-center gap-1 font-semibold text-indigo-700 hover:text-indigo-900"
                      >
                        Corrigir <ExternalLink size={13} />
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {loading && <div className="p-10 text-center text-sm text-gray-500">Carregando...</div>}
        {!loading && !(data?.itens || []).length && (
          <div className="p-10 text-center text-sm text-gray-500">
            Nenhum produto corresponde a estes filtros.
          </div>
        )}
        <div className="flex items-center justify-between border-t border-gray-100 px-4 py-3 text-sm text-gray-600">
          <span>{data?.total || 0} produto(s)</span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => updateParams({ pagina: String(page - 1) })}
              className="rounded border border-gray-300 p-2 disabled:opacity-40"
              aria-label="Página anterior"
            >
              <ChevronLeft size={16} />
            </button>
            <span>
              {page} de {totalPages}
            </span>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => updateParams({ pagina: String(page + 1) })}
              className="rounded border border-gray-300 p-2 disabled:opacity-40"
              aria-label="Próxima página"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
