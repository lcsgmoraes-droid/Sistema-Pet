import {
  AlertTriangle,
  BellRing,
  ChevronLeft,
  ChevronRight,
  Download,
  ExternalLink,
  PackagePlus,
  PackageSearch,
  RefreshCw,
  SearchX,
  UserRoundSearch,
  WalletCards,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";

import { api } from "../services/api";
import { formatMoneyBRL } from "../utils/formatters";

const PAGE_SIZE = 50;
const STATUS_META = {
  bloqueado: { label: "Bloqueado no e-commerce", style: "bg-red-100 text-red-700" },
  esgotado: { label: "Esgotado", style: "bg-amber-100 text-amber-800" },
  pendencias: { label: "Dados a melhorar", style: "bg-blue-100 text-blue-700" },
  pronto: { label: "Disponível", style: "bg-emerald-100 text-emerald-700" },
};

function dataInput(data) {
  const ano = data.getFullYear();
  const mes = String(data.getMonth() + 1).padStart(2, "0");
  const dia = String(data.getDate()).padStart(2, "0");
  return `${ano}-${mes}-${dia}`;
}

function formatarNumero(valor) {
  return Number(valor || 0).toLocaleString("pt-BR", { maximumFractionDigits: 4 });
}

function csvCampo(valor) {
  return `"${String(valor ?? "").replaceAll('"', '""')}"`;
}

function baixarCsv(itens) {
  const cabecalho = [
    "Produto",
    "SKU",
    "Marca",
    "Fornecedor",
    "Cadastrado",
    "Situação no e-commerce",
    "Procuras no PDV",
    "Pessoas identificadas no PDV",
    "Procuras anônimas",
    "Aguardando no PDV",
    "Aguardando no e-commerce",
    "Total aguardando",
    "Quantidade procurada",
    "Valor estimado",
    "Última demanda",
  ];
  const linhas = itens.map((item) => {
    const status = item.cadastrado
      ? STATUS_META[item.ecommerce?.status]?.label || "Sem classificação"
      : "Produto ainda não cadastrado";
    return [
      item.produto_nome,
      item.sku,
      item.marca,
      item.fornecedor,
      item.cadastrado ? "Sim" : "Não",
      status,
      item.procuras_pdv,
      item.pessoas_identificadas_pdv,
      item.procuras_anonimas_pdv,
      item.aguardando_pdv,
      item.aguardando_ecommerce,
      item.aguardando_total,
      item.quantidade_procurada,
      item.valor_estimado_oportunidade,
      item.ultima_demanda_em,
    ];
  });
  const conteudo = [cabecalho, ...linhas]
    .map((linha) => linha.map(csvCampo).join(";"))
    .join("\r\n");
  const url = URL.createObjectURL(
    new Blob([`\uFEFF${conteudo}`], { type: "text/csv;charset=utf-8" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = `demanda-nao-atendida-${dataInput(new Date())}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function ResumoCard({ icon: Icon, label, value, detail, tone = "slate" }) {
  const tones = {
    slate: "border-slate-200 bg-white text-slate-900",
    blue: "border-blue-200 bg-blue-50 text-blue-900",
    amber: "border-amber-200 bg-amber-50 text-amber-900",
    violet: "border-violet-200 bg-violet-50 text-violet-900",
    red: "border-red-200 bg-red-50 text-red-900",
  };
  return (
    <div className={`rounded-xl border p-4 shadow-sm ${tones[tone]}`}>
      <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide opacity-70">
        <Icon size={16} /> {label}
      </div>
      <p className="mt-2 text-2xl font-bold">{value}</p>
      <p className="mt-1 text-xs opacity-70">{detail}</p>
    </div>
  );
}

function SituacaoProduto({ item }) {
  if (!item.cadastrado) {
    return (
      <span className="inline-flex rounded-full bg-violet-100 px-2 py-1 text-xs font-bold text-violet-700">
        Não cadastrado
      </span>
    );
  }
  const meta = STATUS_META[item.ecommerce?.status] || STATUS_META.pendencias;
  return (
    <div className="space-y-1.5">
      <span className={`inline-flex rounded-full px-2 py-1 text-xs font-bold ${meta.style}`}>
        {meta.label}
      </span>
      <div className="flex max-w-xs flex-wrap gap-1">
        {(item.ecommerce?.bloqueios || []).slice(0, 2).map((issue) => (
          <span
            key={issue.codigo}
            className="rounded bg-red-50 px-1.5 py-0.5 text-[11px] text-red-700"
          >
            {issue.label}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function DemandaNaoAtendida() {
  const hoje = new Date();
  const inicioPadrao = new Date(hoje);
  inicioPadrao.setDate(inicioPadrao.getDate() - 29);
  const [filtros, setFiltros] = useState({
    data_inicio: dataInput(inicioPadrao),
    data_fim: dataInput(hoje),
    busca: "",
    origem: "todos",
    situacao: "todos",
  });
  const [pagina, setPagina] = useState(1);
  const [refreshKey, setRefreshKey] = useState(0);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exportando, setExportando] = useState(false);
  const [erro, setErro] = useState("");

  const paramsAtuais = useCallback(
    (extras = {}) => ({
      data_inicio: filtros.data_inicio,
      data_fim: filtros.data_fim,
      busca: filtros.busca || undefined,
      origem: filtros.origem,
      situacao: filtros.situacao,
      offset: (pagina - 1) * PAGE_SIZE,
      limit: PAGE_SIZE,
      ...extras,
    }),
    [filtros, pagina],
  );

  useEffect(() => {
    let ativo = true;
    const timer = window.setTimeout(
      async () => {
        setLoading(true);
        setErro("");
        try {
          const response = await api.get("/nao-vendas/central-demanda", {
            params: paramsAtuais(),
          });
          if (ativo) setData(response.data);
        } catch (error) {
          if (ativo) {
            setErro(error.response?.data?.detail || "Não foi possível carregar a central.");
          }
        } finally {
          if (ativo) setLoading(false);
        }
      },
      filtros.busca ? 250 : 0,
    );
    return () => {
      ativo = false;
      window.clearTimeout(timer);
    };
  }, [filtros.busca, paramsAtuais, refreshKey]);

  function alterarFiltro(campo, valor) {
    setFiltros((atuais) => ({ ...atuais, [campo]: valor }));
    setPagina(1);
  }

  async function exportar() {
    try {
      setExportando(true);
      const response = await api.get("/nao-vendas/central-demanda", {
        params: paramsAtuais({ offset: 0, limit: 500 }),
      });
      baixarCsv(response.data?.itens || []);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Não foi possível gerar o arquivo.");
    } finally {
      setExportando(false);
    }
  }

  const resumo = data?.resumo || {};
  const itens = data?.itens || [];
  const totalPaginas = Math.max(Math.ceil(Number(data?.total || 0) / PAGE_SIZE), 1);

  return (
    <div className="mx-auto max-w-[1500px] space-y-6 p-4 md:p-8">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <PackageSearch className="text-violet-600" size={28} />
            <h1 className="text-2xl font-bold text-slate-900">Central de demanda não atendida</h1>
          </div>
          <p className="mt-1 max-w-3xl text-sm text-slate-500">
            Veja o que foi procurado no PDV e quantas pessoas aguardam produtos na loja ou no
            e-commerce. Use esses sinais para corrigir o catálogo e planejar reposições.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            to="/produtos/novo"
            className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-3 py-2 text-sm font-semibold text-white hover:bg-violet-700"
          >
            <PackagePlus size={16} /> Cadastrar produto
          </Link>
          <button
            type="button"
            onClick={() => void exportar()}
            disabled={exportando || !data?.total}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 disabled:opacity-50"
          >
            <Download size={16} /> {exportando ? "Gerando..." : "Baixar CSV"}
          </button>
          <button
            type="button"
            onClick={() => setRefreshKey((valor) => valor + 1)}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700"
          >
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} /> Atualizar
          </button>
        </div>
      </header>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <ResumoCard
          icon={BellRing}
          label="Inscrições ativas"
          value={resumo.inscricoes_ativas || 0}
          detail={`${resumo.inscricoes_pdv || 0} no PDV · ${resumo.inscricoes_ecommerce || 0} online`}
          tone="amber"
        />
        <ResumoCard
          icon={SearchX}
          label="Procuras no PDV"
          value={resumo.procuras_pdv || 0}
          detail={`${resumo.atendimentos_pdv || 0} atendimento(s) no período`}
          tone="blue"
        />
        <ResumoCard
          icon={UserRoundSearch}
          label="Pessoas identificadas"
          value={resumo.pessoas_identificadas_pdv || 0}
          detail={`${resumo.procuras_anonimas_pdv || 0} procura(s) anônima(s)`}
        />
        <ResumoCard
          icon={PackageSearch}
          label="Produtos ou termos"
          value={resumo.produtos_com_demanda || 0}
          detail={`${resumo.produtos_nao_cadastrados || 0} ainda não cadastrado(s)`}
          tone="violet"
        />
        <ResumoCard
          icon={WalletCards}
          label="Oportunidade estimada"
          value={formatMoneyBRL(resumo.valor_estimado_oportunidade || 0)}
          detail="informada no registro do PDV"
        />
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <label>
            <span className="mb-1 block text-xs font-medium text-slate-600">Procuras de</span>
            <input
              type="date"
              value={filtros.data_inicio}
              onChange={(event) => alterarFiltro("data_inicio", event.target.value)}
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
            />
          </label>
          <label>
            <span className="mb-1 block text-xs font-medium text-slate-600">Até</span>
            <input
              type="date"
              value={filtros.data_fim}
              onChange={(event) => alterarFiltro("data_fim", event.target.value)}
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
            />
          </label>
          <label>
            <span className="mb-1 block text-xs font-medium text-slate-600">Canal</span>
            <select
              value={filtros.origem}
              onChange={(event) => alterarFiltro("origem", event.target.value)}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"
            >
              <option value="todos">PDV e e-commerce</option>
              <option value="pdv">Somente PDV</option>
              <option value="ecommerce">Somente e-commerce</option>
            </select>
          </label>
          <label>
            <span className="mb-1 block text-xs font-medium text-slate-600">Situação</span>
            <select
              value={filtros.situacao}
              onChange={(event) => alterarFiltro("situacao", event.target.value)}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"
            >
              <option value="todos">Todas</option>
              <option value="aguardando">Com pessoas aguardando</option>
              <option value="nao_cadastrado">Ainda não cadastrado</option>
              <option value="ausente_ecommerce">Ausente do e-commerce</option>
              <option value="bloqueado">Bloqueado no e-commerce</option>
              <option value="esgotado">Esgotado</option>
              <option value="pendencias">Com dados a melhorar</option>
              <option value="pronto">Disponível no e-commerce</option>
            </select>
          </label>
          <label>
            <span className="mb-1 block text-xs font-medium text-slate-600">Buscar</span>
            <input
              value={filtros.busca}
              onChange={(event) => alterarFiltro("busca", event.target.value)}
              placeholder="Produto, SKU, marca..."
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
            />
          </label>
        </div>
        <p className="mt-3 text-xs text-slate-500">
          O período filtra as procuras registradas no PDV. As listas de espera sempre mostram todas
          as inscrições que continuam ativas.
        </p>
      </section>

      {erro && (
        <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <AlertTriangle size={18} /> {erro}
        </div>
      )}

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Produto procurado</th>
                <th className="px-4 py-3">Situação</th>
                <th className="px-4 py-3 text-center">Procuras no PDV</th>
                <th className="px-4 py-3 text-center">Pessoas aguardando</th>
                <th className="px-4 py-3 text-right">Quantidade</th>
                <th className="px-4 py-3">Último sinal</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {itens.map((item) => (
                <tr
                  key={item.produto_id || `${item.produto_nome}-${item.sku || "livre"}`}
                  className="border-t border-slate-100 align-top"
                >
                  <td className="px-4 py-3">
                    <p className="font-semibold text-slate-900">{item.produto_nome}</p>
                    <p className="text-xs text-slate-500">
                      {item.sku || "Sem SKU"} · {item.marca || "Sem marca"}
                    </p>
                    {item.fornecedor && (
                      <p className="mt-1 text-xs text-slate-400">{item.fornecedor}</p>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <SituacaoProduto item={item} />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <p className="text-lg font-bold text-blue-700">{item.procuras_pdv}</p>
                    <p className="text-xs text-slate-500">
                      {item.pessoas_identificadas_pdv} identificada(s) ·{" "}
                      {item.procuras_anonimas_pdv} anônima(s)
                    </p>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <p className="text-lg font-bold text-amber-700">{item.aguardando_total}</p>
                    <p className="text-xs text-slate-500">
                      {item.aguardando_pdv} PDV · {item.aguardando_ecommerce} online
                    </p>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <p className="font-semibold text-slate-800">
                      {formatarNumero(item.quantidade_procurada)} procurada
                    </p>
                    {item.quantidade_aguardada_pdv > 0 && (
                      <p className="text-xs text-slate-500">
                        {formatarNumero(item.quantidade_aguardada_pdv)} aguardada no PDV
                      </p>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500">
                    {item.ultima_demanda_em
                      ? new Date(item.ultima_demanda_em).toLocaleString("pt-BR")
                      : "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {item.produto_id ? (
                      <Link
                        to={`/produtos/${item.produto_id}/editar`}
                        className="inline-flex items-center gap-1 font-semibold text-violet-700 hover:text-violet-900"
                      >
                        Abrir <ExternalLink size={13} />
                      </Link>
                    ) : (
                      <Link
                        to="/produtos/novo"
                        className="inline-flex items-center gap-1 font-semibold text-violet-700 hover:text-violet-900"
                      >
                        Cadastrar <PackagePlus size={13} />
                      </Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {loading && <div className="p-10 text-center text-sm text-slate-500">Carregando...</div>}
        {!loading && !itens.length && (
          <div className="p-10 text-center text-sm text-slate-500">
            Nenhuma demanda corresponde aos filtros selecionados.
          </div>
        )}
        <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3 text-sm text-slate-600">
          <span>{data?.total || 0} produto(s) ou termo(s)</span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={pagina <= 1}
              onClick={() => setPagina((valor) => Math.max(valor - 1, 1))}
              className="rounded border border-slate-300 p-2 disabled:opacity-40"
              aria-label="Página anterior"
            >
              <ChevronLeft size={16} />
            </button>
            <span>
              {pagina} de {totalPaginas}
            </span>
            <button
              type="button"
              disabled={pagina >= totalPaginas}
              onClick={() => setPagina((valor) => valor + 1)}
              className="rounded border border-slate-300 p-2 disabled:opacity-40"
              aria-label="Próxima página"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </section>

      <div className="flex flex-col gap-2 rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900 md:flex-row md:items-center md:justify-between">
        <span>
          Produtos cadastrados ausentes ou bloqueados no e-commerce também aparecem na Saúde do
          Catálogo, com o motivo exato para correção.
        </span>
        <Link to="/ecommerce/catalogo-saude" className="font-bold underline">
          Abrir Saúde do Catálogo
        </Link>
      </div>
    </div>
  );
}
