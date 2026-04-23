import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import {
  formatarData,
  formatarMoeda,
  getRelatorioValidadeProxima,
} from "../api/produtos";
import {
  criarExclusaoCampanhaValidade,
  removerExclusaoCampanhaValidade,
} from "../api/campanhasValidade";
import useProdutosCatalogos from "../hooks/useProdutosCatalogos";

const ITENS_POR_PAGINA_INICIAL = 20;

const filtrosIniciais = {
  busca: "",
  dias: 60,
  status_validade: "proximos",
  categoria_id: "",
  marca_id: "",
  departamento_id: "",
  fornecedor_id: "",
  apenas_com_estoque: true,
  ordenacao: "validade_asc",
  page_size: ITENS_POR_PAGINA_INICIAL,
};

const formatarQuantidade = (valor) =>
  new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(Number(valor || 0));

function ResumoCard({
  titulo,
  valor,
  descricao,
  destaque = "blue",
  valorClassName = "",
  descricaoClassName = "",
}) {
  const estilos = {
    blue: "border-blue-100 bg-blue-50 text-blue-900",
    emerald: "border-emerald-100 bg-emerald-50 text-emerald-900",
    amber: "border-amber-100 bg-amber-50 text-amber-900",
    rose: "border-rose-100 bg-rose-50 text-rose-900",
    violet: "border-violet-100 bg-violet-50 text-violet-900",
  };

  return (
    <div
      className={`rounded-2xl border p-5 shadow-sm ${estilos[destaque] || estilos.blue}`}
    >
      <p className="text-sm font-medium opacity-80">{titulo}</p>
      <p className={`mt-2 text-2xl font-bold ${valorClassName}`}>{valor}</p>
      <p className={`mt-2 text-xs opacity-75 ${descricaoClassName}`}>{descricao}</p>
    </div>
  );
}

function getStatusBadge(status) {
  const mapa = {
    vencido: {
      label: "Vencido",
      className: "bg-rose-100 text-rose-700 border border-rose-200",
    },
    urgente: {
      label: "Janela 7 dias",
      className: "bg-orange-100 text-orange-700 border border-orange-200",
    },
    alerta_30: {
      label: "Janela 30 dias",
      className: "bg-amber-100 text-amber-700 border border-amber-200",
    },
    alerta_60: {
      label: "Janela 60 dias",
      className: "bg-blue-100 text-blue-700 border border-blue-200",
    },
    monitorar: {
      label: "Monitorar",
      className: "bg-slate-100 text-slate-700 border border-slate-200",
    },
  };

  return (
    mapa[status] || {
      label: "Sem regra",
      className: "bg-slate-100 text-slate-700 border border-slate-200",
    }
  );
}

function getDiasRestantesVisual(diasParaVencer) {
  const dias = Number(diasParaVencer ?? 0);

  if (dias < 0) {
    const total = Math.abs(dias);
    return {
      destaque: `${total} dia${total === 1 ? "" : "s"}`,
      apoio: "em atraso",
      className: "text-rose-700",
      surfaceClassName: "border-rose-200 bg-rose-50",
    };
  }

  if (dias === 0) {
    return {
      destaque: "Hoje",
      apoio: "vence hoje",
      className: "text-orange-700",
      surfaceClassName: "border-orange-200 bg-orange-50",
    };
  }

  return {
    destaque: `${dias} dia${dias === 1 ? "" : "s"}`,
    apoio: "para vencer",
    className:
      dias <= 7
        ? "text-orange-700"
        : dias <= 30
          ? "text-amber-700"
          : "text-blue-700",
    surfaceClassName:
      dias <= 7
        ? "border-orange-200 bg-orange-50"
        : dias <= 30
          ? "border-amber-200 bg-amber-50"
          : "border-blue-200 bg-blue-50",
  };
}

function getFaixaCampanhaBadge(faixa) {
  const mapa = {
    vencido: {
      label: "Acao imediata",
      className: "bg-rose-100 text-rose-700 border border-rose-200",
    },
    "7_dias": {
      label: "Campanha 7 dias",
      className: "bg-orange-100 text-orange-700 border border-orange-200",
    },
    "30_dias": {
      label: "Campanha 30 dias",
      className: "bg-amber-100 text-amber-700 border border-amber-200",
    },
    "60_dias": {
      label: "Campanha 60 dias",
      className: "bg-emerald-100 text-emerald-700 border border-emerald-200",
    },
  };

  return (
    mapa[faixa] || {
      label: "Sem campanha sugerida",
      className: "bg-slate-100 text-slate-600 border border-slate-200",
    }
  );
}

function montarParametros(filtros, pagina, pageSizeOverride) {
  const params = {
    page: pagina,
    page_size: Number(pageSizeOverride || filtros.page_size) || ITENS_POR_PAGINA_INICIAL,
    dias: Number(filtros.dias) || 60,
    status_validade: filtros.status_validade || "proximos",
    apenas_com_estoque: Boolean(filtros.apenas_com_estoque),
    ordenacao: filtros.ordenacao || "validade_asc",
  };

  if (filtros.busca?.trim()) params.busca = filtros.busca.trim();
  if (filtros.categoria_id) params.categoria_id = filtros.categoria_id;
  if (filtros.marca_id) params.marca_id = filtros.marca_id;
  if (filtros.departamento_id) params.departamento_id = filtros.departamento_id;
  if (filtros.fornecedor_id) params.fornecedor_id = filtros.fornecedor_id;

  return params;
}

function normalizarValorCsv(valor) {
  if (valor === null || valor === undefined) return "";
  if (typeof valor === "number") return String(valor).replace(".", ",");
  return String(valor).replaceAll('"', '""');
}

function baixarCsv(nomeArquivo, linhas) {
  const csv = linhas.join("\n");
  const blob = new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", nomeArquivo);
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export default function ProdutosValidadeProxima({
  embedded = false,
  reloadSignal = 0,
}) {
  const navigate = useNavigate();
  const { categorias, fornecedores, marcas, departamentos } = useProdutosCatalogos();

  const [loading, setLoading] = useState(false);
  const [exportando, setExportando] = useState(false);
  const [acaoCampanhaLoteId, setAcaoCampanhaLoteId] = useState(null);
  const [paginaAtual, setPaginaAtual] = useState(1);
  const [filtrosForm, setFiltrosForm] = useState(filtrosIniciais);
  const [filtrosAplicados, setFiltrosAplicados] = useState(filtrosIniciais);
  const [dados, setDados] = useState({
    items: [],
    total: 0,
    page: 1,
    page_size: ITENS_POR_PAGINA_INICIAL,
    pages: 0,
    totais: {
      total_lotes: 0,
      total_produtos: 0,
      total_quantidade: 0,
      lotes_vencidos: 0,
      lotes_ate_7_dias: 0,
      lotes_ate_30_dias: 0,
      lotes_ate_60_dias: 0,
      valor_custo_em_risco: 0,
      valor_venda_em_risco: 0,
    },
  });

  useEffect(() => {
    void carregarRelatorio(filtrosAplicados, paginaAtual);
  }, [filtrosAplicados, paginaAtual, reloadSignal]);

  const quickDays = useMemo(() => [30, 60, 90, 120], []);

  const carregarRelatorio = async (filtros, pagina) => {
    try {
      setLoading(true);
      const response = await getRelatorioValidadeProxima(
        montarParametros(filtros, pagina),
      );
      setDados(response.data);
    } catch (error) {
      console.error("Erro ao carregar validade proxima:", error);
      toast.error(
        error?.response?.data?.detail ||
          "Nao foi possivel carregar os lotes com validade proxima.",
      );
      setDados({
        items: [],
        total: 0,
        page: 1,
        page_size: Number(filtros.page_size) || ITENS_POR_PAGINA_INICIAL,
        pages: 0,
        totais: {
          total_lotes: 0,
          total_produtos: 0,
          total_quantidade: 0,
          lotes_vencidos: 0,
          lotes_ate_7_dias: 0,
          lotes_ate_30_dias: 0,
          lotes_ate_60_dias: 0,
          valor_custo_em_risco: 0,
          valor_venda_em_risco: 0,
        },
      });
    } finally {
      setLoading(false);
    }
  };

  const atualizarFiltro = (campo, valor) => {
    setFiltrosForm((prev) => ({
      ...prev,
      [campo]: valor,
    }));
  };

  const aplicarFiltros = (event) => {
    event.preventDefault();
    setPaginaAtual(1);
    setFiltrosAplicados({
      ...filtrosForm,
      dias: Number(filtrosForm.dias) || 60,
      page_size: Number(filtrosForm.page_size) || ITENS_POR_PAGINA_INICIAL,
    });
  };

  const limparFiltros = () => {
    setPaginaAtual(1);
    setFiltrosForm(filtrosIniciais);
    setFiltrosAplicados(filtrosIniciais);
  };

  const exportarCsv = async () => {
    try {
      setExportando(true);
      toast.loading("Montando relatorio CSV...", { id: "csv-validade" });

      let pagina = 1;
      let totalPaginas = 1;
      const itens = [];

      while (pagina <= totalPaginas) {
        const response = await getRelatorioValidadeProxima(
          montarParametros(filtrosAplicados, pagina, 200),
        );
        const payload = response.data || {};
        const linhasPagina = Array.isArray(payload.items) ? payload.items : [];
        itens.push(...linhasPagina);
        totalPaginas = Number(payload.pages || 0) || 1;
        if (!linhasPagina.length) {
          break;
        }
        pagina += 1;
      }

      if (!itens.length) {
        toast.error("Nenhum lote encontrado para exportacao.", {
          id: "csv-validade",
        });
        return;
      }

      const cabecalho = [
        "Produto",
        "Codigo",
        "SKU",
        "Categoria",
        "Marca",
        "Fornecedor",
        "Lote",
        "Validade",
        "Dias para vencer",
        "Quantidade",
        "Custo unitario",
        "Preco venda",
        "Valor custo lote",
        "Valor venda lote",
        "Status validade",
        "Faixa campanha",
        "Promocao ativa",
        "Campanha validade ativa",
        "Campanha validade excluida",
        "Canais campanha",
        "Desconto campanha",
        "Preco campanha app",
        "Preco campanha site",
        "Quantidade promocional",
      ]
        .map((coluna) => `"${coluna}"`)
        .join(";");

      const linhas = itens.map((item) =>
        [
          item.nome,
          item.codigo || "",
          item.sku || "",
          item.categoria_nome || "",
          item.marca_nome || "",
          item.fornecedor_nome || "",
          item.nome_lote || "",
          formatarData(item.data_validade),
          item.dias_para_vencer,
          item.quantidade_disponivel,
          item.custo_unitario,
          item.preco_venda,
          item.valor_custo_lote,
          item.valor_venda_lote,
          item.status_validade,
          item.faixa_campanha || "",
          item.promocao_ativa ? "Sim" : "Nao",
          item.campanha_validade_ativa ? "Sim" : "Nao",
          item.campanha_validade_excluida ? "Sim" : "Nao",
          Array.isArray(item.campanha_validade_canais)
            ? item.campanha_validade_canais.join(", ")
            : "",
          item.percentual_desconto_validade,
          item.preco_promocional_validade_app,
          item.preco_promocional_validade_ecommerce,
          item.quantidade_promocional,
        ]
          .map((valor) => `"${normalizarValorCsv(valor)}"`)
          .join(";"),
      );

      const dataArquivo = new Date().toISOString().slice(0, 10);
      baixarCsv(
        `validade_proxima_${dataArquivo}.csv`,
        [cabecalho, ...linhas],
      );
      toast.success(`CSV gerado com ${itens.length} lote(s).`, {
        id: "csv-validade",
      });
    } catch (error) {
      console.error("Erro ao exportar CSV de validade:", error);
      toast.error("Nao foi possivel gerar o CSV de validade.", {
        id: "csv-validade",
      });
    } finally {
      setExportando(false);
    }
  };

  const inicioItem =
    dados.total === 0 ? 0 : (dados.page - 1) * dados.page_size + 1;
  const fimItem =
    dados.total === 0 ? 0 : Math.min(dados.page * dados.page_size, dados.total);
  const totalPaginas = dados.pages || 0;
  const loteMaisUrgente = useMemo(() => {
    if (!Array.isArray(dados.items) || dados.items.length === 0) {
      return null;
    }

    return dados.items.reduce((maisUrgente, itemAtual) => {
      const diasMaisUrgente = Number(maisUrgente?.dias_para_vencer ?? Infinity);
      const diasAtual = Number(itemAtual?.dias_para_vencer ?? Infinity);
      return diasAtual < diasMaisUrgente ? itemAtual : maisUrgente;
    }, dados.items[0]);
  }, [dados.items]);
  const prazoMaisCurto = loteMaisUrgente
    ? getDiasRestantesVisual(loteMaisUrgente.dias_para_vencer)
    : null;

  const atualizarPainelAtual = async () => {
    await carregarRelatorio(filtrosAplicados, paginaAtual);
  };

  const excluirDaCampanha = async (item) => {
    try {
      setAcaoCampanhaLoteId(item.lote_id);
      await criarExclusaoCampanhaValidade({
        produto_id: item.produto_id,
        lote_id: item.lote_id,
        motivo: "Remocao manual da campanha de validade",
        observacao: `Lote ${item.nome_lote} removido manualmente pela tela de validade.`,
      });
      toast.success("Lote removido da campanha automatica.");
      await atualizarPainelAtual();
    } catch (error) {
      console.error("Erro ao excluir lote da campanha:", error);
      toast.error(
        error?.response?.data?.detail ||
          "Nao foi possivel remover o lote da campanha.",
      );
    } finally {
      setAcaoCampanhaLoteId(null);
    }
  };

  const reincluirNaCampanha = async (item) => {
    if (!item.campanha_validade_exclusao_id) {
      return;
    }
    try {
      setAcaoCampanhaLoteId(item.lote_id);
      await removerExclusaoCampanhaValidade(item.campanha_validade_exclusao_id);
      toast.success("Lote reincluido na campanha automatica.");
      await atualizarPainelAtual();
    } catch (error) {
      console.error("Erro ao reincluir lote na campanha:", error);
      toast.error(
        error?.response?.data?.detail ||
          "Nao foi possivel reincluir o lote na campanha.",
      );
    } finally {
      setAcaoCampanhaLoteId(null);
    }
  };

  return (
    <div className={embedded ? "space-y-6" : "space-y-6 p-6"}>
      {!embedded && (
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              Produtos com validade proxima
            </h1>
            <p className="mt-2 max-w-4xl text-sm text-gray-600">
              A tela considera o lote mais urgente primeiro, pagina em blocos
              leves e deixa pronto o trabalho comercial: enxergar o risco,
              priorizar o que vence antes e abrir campanhas sem perder tempo.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => navigate("/campanhas?aba=validade")}
              className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700 transition-colors hover:bg-emerald-100"
            >
              Abrir campanhas
            </button>
            <button
              onClick={exportarCsv}
              disabled={exportando}
              className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {exportando ? "Exportando..." : "Exportar CSV"}
            </button>
            <button
              onClick={() => navigate("/produtos")}
              className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
            >
              Voltar para produtos
            </button>
          </div>
        </div>
      )}

      <div className="rounded-2xl border border-emerald-100 bg-gradient-to-r from-emerald-50 via-white to-amber-50 p-5 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              Regra automatica por validade
            </h2>
            <p className="mt-1 text-sm text-gray-600">
              60 dias para planejar giro, 30 dias para acelerar oferta e 7 dias
              para acao forte. Quando a campanha estiver ativa, o lote entra
              sozinho com limite de quantidade do proprio lote.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            {embedded && (
              <button
                type="button"
                onClick={exportarCsv}
                disabled={exportando}
                className="rounded-full bg-white px-3 py-1.5 text-sm font-medium text-blue-700 ring-1 ring-blue-200 transition-colors hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {exportando ? "Exportando..." : "Exportar CSV"}
              </button>
            )}
            {embedded && (
              <button
                type="button"
                onClick={() => navigate("/campanhas?aba=validade")}
                className="rounded-full bg-white px-3 py-1.5 text-sm font-medium text-emerald-700 ring-1 ring-emerald-200 transition-colors hover:bg-emerald-50"
              >
                Abrir campanhas
              </button>
            )}
            {quickDays.map((dia) => (
              <button
                key={dia}
                type="button"
                onClick={() => atualizarFiltro("dias", dia)}
                className={`rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
                  Number(filtrosForm.dias) === dia
                    ? "bg-emerald-600 text-white"
                    : "bg-white text-emerald-700 ring-1 ring-emerald-200 hover:bg-emerald-50"
                }`}
              >
                Ate {dia} dias
              </button>
            ))}
          </div>
        </div>
      </div>

      <form
        onSubmit={aplicarFiltros}
        className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm"
      >
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
          <div className="xl:col-span-2">
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Busca
            </label>
            <input
              type="text"
              value={filtrosForm.busca}
              onChange={(event) => atualizarFiltro("busca", event.target.value)}
              placeholder="Produto, codigo, SKU ou lote"
              className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Janela
            </label>
            <select
              value={filtrosForm.dias}
              onChange={(event) => atualizarFiltro("dias", Number(event.target.value))}
              className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              {[30, 60, 90, 120, 180].map((dia) => (
                <option key={dia} value={dia}>
                  Ate {dia} dias
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Status
            </label>
            <select
              value={filtrosForm.status_validade}
              onChange={(event) =>
                atualizarFiltro("status_validade", event.target.value)
              }
              className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              <option value="proximos">Somente proximos</option>
              <option value="vencidos">Somente vencidos</option>
              <option value="todos">Vencidos + proximos</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Ordenacao
            </label>
            <select
              value={filtrosForm.ordenacao}
              onChange={(event) => atualizarFiltro("ordenacao", event.target.value)}
              className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              <option value="validade_asc">Validade mais proxima</option>
              <option value="validade_desc">Validade mais distante</option>
              <option value="quantidade_desc">Maior quantidade</option>
              <option value="valor_desc">Maior valor em risco</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Categoria
            </label>
            <select
              value={filtrosForm.categoria_id}
              onChange={(event) =>
                atualizarFiltro("categoria_id", event.target.value)
              }
              className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              <option value="">Todas as categorias</option>
              {categorias.map((categoria) => (
                <option key={categoria.id} value={categoria.id}>
                  {categoria.nome}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Marca
            </label>
            <select
              value={filtrosForm.marca_id}
              onChange={(event) => atualizarFiltro("marca_id", event.target.value)}
              className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              <option value="">Todas as marcas</option>
              {marcas.map((marca) => (
                <option key={marca.id} value={marca.id}>
                  {marca.nome}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Setor
            </label>
            <select
              value={filtrosForm.departamento_id}
              onChange={(event) =>
                atualizarFiltro("departamento_id", event.target.value)
              }
              className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              <option value="">Todos os setores</option>
              {departamentos.map((departamento) => (
                <option key={departamento.id} value={departamento.id}>
                  {departamento.nome}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Fornecedor
            </label>
            <select
              value={filtrosForm.fornecedor_id}
              onChange={(event) =>
                atualizarFiltro("fornecedor_id", event.target.value)
              }
              className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              <option value="">Todos os fornecedores</option>
              {fornecedores.map((fornecedor) => (
                <option key={fornecedor.id} value={fornecedor.id}>
                  {fornecedor.nome}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-col gap-3 md:flex-row md:items-center">
            <label className="inline-flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={filtrosForm.apenas_com_estoque}
                onChange={(event) =>
                  atualizarFiltro("apenas_com_estoque", event.target.checked)
                }
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              Somente lotes com saldo
            </label>

            <div className="flex items-center gap-2 text-sm text-gray-700">
              <span>Itens por pagina</span>
              <select
                value={filtrosForm.page_size}
                onChange={(event) =>
                  atualizarFiltro("page_size", Number(event.target.value))
                }
                className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                {[20, 50, 100].map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={limparFiltros}
              className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
            >
              Limpar filtros
            </button>
            <button
              type="submit"
              className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-700"
            >
              Atualizar painel
            </button>
          </div>
        </div>
      </form>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-6">
        <ResumoCard
          titulo="Lotes no filtro"
          valor={dados.totais.total_lotes}
          descricao={`${dados.totais.total_produtos || 0} produto(s) com risco comercial no recorte atual.`}
          destaque="blue"
        />
        <ResumoCard
          titulo="Vencidos"
          valor={dados.totais.lotes_vencidos}
          descricao="Itens que ja precisam de tratativa imediata."
          destaque="rose"
        />
        <ResumoCard
          titulo="Na campanha"
          valor={dados.totais.lotes_em_campanha || 0}
          descricao={`Excluidos manualmente: ${dados.totais.lotes_excluidos_campanha || 0}.`}
          destaque="emerald"
        />
        <ResumoCard
          titulo="Custo em risco"
          valor={formatarMoeda(dados.totais.valor_custo_em_risco)}
          descricao={`Quantidade total: ${formatarQuantidade(dados.totais.total_quantidade)}`}
          destaque="violet"
        />
        <ResumoCard
          titulo="Prazo mais curto"
          valor={prazoMaisCurto ? prazoMaisCurto.destaque : "--"}
          descricao={
            prazoMaisCurto && loteMaisUrgente
              ? `${prazoMaisCurto.apoio} • ${loteMaisUrgente.nome}`
              : "Sem lotes no recorte atual."
          }
          destaque={
            loteMaisUrgente?.dias_para_vencer < 0
              ? "rose"
              : loteMaisUrgente?.dias_para_vencer <= 30
                ? "amber"
                : "blue"
          }
          valorClassName="text-3xl"
          descricaoClassName="line-clamp-2"
        />
        <ResumoCard
          titulo="Potencial de venda"
          valor={formatarMoeda(dados.totais.valor_venda_em_risco)}
          descricao={`Ate 60 dias: ${dados.totais.lotes_ate_60_dias || 0} lote(s) no radar.`}
          destaque="emerald"
        />
      </div>

      <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
        <div className="flex flex-col gap-3 border-b border-gray-200 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              Lotes ordenados por vencimento
            </h2>
            <p className="text-sm text-gray-600">
              {loading
                ? "Atualizando dados..."
                : `Exibindo ${inicioItem}-${fimItem} de ${dados.total} lote(s).`}
            </p>
          </div>

          <div className="flex flex-wrap gap-2 text-xs text-gray-500">
            <span className="rounded-full bg-slate-100 px-3 py-1.5">
              Ordenacao padrao: validade crescente
            </span>
            <span className="rounded-full bg-slate-100 px-3 py-1.5">
              Paginacao leve para uso operacional
            </span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Produto
                </th>
                <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Lote
                </th>
                <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Prazo / validade
                </th>
                <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Quantidade
                </th>
                <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Valor em risco
                </th>
                <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Campanha automatica
                </th>
                <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Acoes
                </th>
              </tr>
            </thead>

            <tbody className="divide-y divide-gray-100 bg-white">
              {!loading && dados.items.length === 0 && (
                <tr>
                  <td
                    colSpan={7}
                    className="px-5 py-10 text-center text-sm text-gray-500"
                  >
                    Nenhum lote encontrado para os filtros aplicados.
                  </td>
                </tr>
              )}

              {dados.items.map((item) => {
                const statusBadge = getStatusBadge(item.status_validade);
                const faixaBadge = getFaixaCampanhaBadge(item.faixa_campanha);
                const diasRestantes = getDiasRestantesVisual(item.dias_para_vencer);
                const processandoCampanha = acaoCampanhaLoteId === item.lote_id;

                return (
                  <tr key={item.lote_id} className="hover:bg-gray-50">
                    <td className="px-5 py-4 align-top">
                      <div className="space-y-1">
                        <div className="text-sm font-semibold text-gray-900">
                          {item.nome}
                        </div>
                        <div className="text-xs text-gray-500">
                          {(item.codigo || item.sku || "Sem codigo")}
                          {item.marca_nome ? ` • ${item.marca_nome}` : ""}
                          {item.categoria_nome ? ` • ${item.categoria_nome}` : ""}
                        </div>
                        {item.fornecedor_nome && (
                          <div className="text-xs text-gray-500">
                            Fornecedor: {item.fornecedor_nome}
                          </div>
                        )}
                      </div>
                    </td>

                    <td className="px-5 py-4 align-top">
                      <div className="space-y-2">
                        <div className="text-sm font-medium text-gray-900">
                          {item.nome_lote}
                        </div>
                        <div className="text-xs text-gray-500">
                          Setor: {item.departamento_nome || "Nao informado"}
                        </div>
                        {item.campanha_validade_excluida ? (
                          <span className="inline-flex rounded-full bg-slate-200 px-2.5 py-1 text-xs font-medium text-slate-700">
                            Fora da campanha
                          </span>
                        ) : item.campanha_validade_ativa ? (
                          <span className="inline-flex rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700">
                            Na campanha
                          </span>
                        ) : item.promocao_ativa ? (
                          <span className="inline-flex rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700">
                            Promocao ativa
                          </span>
                        ) : null}
                      </div>
                    </td>

                    <td className="px-5 py-4 align-top">
                      <div className="space-y-2">
                        <div
                          className={`inline-flex min-w-[120px] flex-col rounded-2xl border px-3 py-2 ${diasRestantes.surfaceClassName}`}
                        >
                          <span
                            className={`text-xl font-bold leading-tight ${diasRestantes.className}`}
                          >
                            {diasRestantes.destaque}
                          </span>
                          <span className="text-[11px] font-semibold uppercase tracking-wide text-gray-600">
                            {diasRestantes.apoio}
                          </span>
                        </div>
                        <span
                          className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${statusBadge.className}`}
                        >
                          {statusBadge.label}
                        </span>
                        <div className="text-xs font-medium text-gray-700">
                          Validade: {formatarData(item.data_validade)}
                        </div>
                      </div>
                    </td>

                    <td className="px-5 py-4 text-right align-top">
                      <div className="text-sm font-semibold text-gray-900">
                        {formatarQuantidade(item.quantidade_disponivel)}
                      </div>
                      <div className="text-xs text-gray-500">
                        Custo unit.: {formatarMoeda(item.custo_unitario)}
                      </div>
                    </td>

                    <td className="px-5 py-4 text-right align-top">
                      <div className="text-sm font-semibold text-gray-900">
                        {formatarMoeda(item.valor_custo_lote)}
                      </div>
                      <div className="text-xs text-gray-500">
                        Venda: {formatarMoeda(item.valor_venda_lote)}
                      </div>
                    </td>

                    <td className="px-5 py-4 align-top">
                      <div className="space-y-2">
                        {item.campanha_validade_excluida ? (
                          <>
                            <span className="inline-flex rounded-full bg-slate-200 px-2.5 py-1 text-xs font-medium text-slate-700">
                              Removido manualmente
                            </span>
                            <p className="max-w-xs text-xs text-gray-500">
                              Esse lote foi tirado da campanha automatica, mas pode ser reincluido a qualquer momento.
                            </p>
                          </>
                        ) : item.campanha_validade_ativa ? (
                          <>
                            <span className="inline-flex rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700">
                              {item.percentual_desconto_validade || 0}% OFF
                            </span>
                            <div className="space-y-1 text-xs text-gray-600">
                              <p>
                                {item.mensagem_promocional ||
                                  `Ate ${formatarQuantidade(item.quantidade_promocional)} unidade(s) por esse preco.`}
                              </p>
                              {item.preco_promocional_validade_app !== null &&
                                item.preco_promocional_validade_app !== undefined && (
                                  <p>App: {formatarMoeda(item.preco_promocional_validade_app)}</p>
                                )}
                              {item.preco_promocional_validade_ecommerce !== null &&
                                item.preco_promocional_validade_ecommerce !== undefined && (
                                  <p>Site: {formatarMoeda(item.preco_promocional_validade_ecommerce)}</p>
                                )}
                            </div>
                          </>
                        ) : (
                          <>
                            <span
                              className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${faixaBadge.className}`}
                            >
                              {faixaBadge.label}
                            </span>
                            <p className="max-w-xs text-xs text-gray-500">
                              {item.faixa_campanha
                                ? "Lote elegivel para a campanha automatica quando a regra estiver ativa."
                                : "Ainda fora da janela automatica sugerida."}
                            </p>
                          </>
                        )}
                      </div>
                    </td>

                    <td className="px-5 py-4 align-top">
                      <div className="flex justify-end gap-2">
                        {item.campanha_validade_excluida ? (
                          <button
                            type="button"
                            disabled={processandoCampanha}
                            onClick={() => reincluirNaCampanha(item)}
                            className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 transition-colors hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            {processandoCampanha ? "Reincluindo..." : "Reincluir"}
                          </button>
                        ) : item.faixa_campanha ? (
                          <button
                            type="button"
                            disabled={processandoCampanha}
                            onClick={() => excluirDaCampanha(item)}
                            className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 transition-colors hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            {processandoCampanha ? "Removendo..." : "Tirar da campanha"}
                          </button>
                        ) : null}
                        <button
                          onClick={() => navigate(`/produtos/${item.produto_id}/editar`)}
                          className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 transition-colors hover:bg-blue-100"
                        >
                          Editar
                        </button>
                        <button
                          onClick={() => navigate("/campanhas?aba=validade")}
                          className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 transition-colors hover:bg-emerald-100"
                        >
                          Campanhas
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="flex flex-col gap-3 border-t border-gray-200 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="text-sm text-gray-600">
            {dados.total > 0
              ? `Mostrando ${inicioItem}-${fimItem} de ${dados.total} lote(s).`
              : "Nenhum lote para exibir."}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setPaginaAtual((prev) => Math.max(prev - 1, 1))}
              disabled={paginaAtual <= 1 || loading}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Anterior
            </button>
            <span className="text-sm text-gray-600">
              Pagina {paginaAtual} de {Math.max(totalPaginas, 1)}
            </span>
            <button
              onClick={() =>
                setPaginaAtual((prev) => Math.min(prev + 1, Math.max(totalPaginas, 1)))
              }
              disabled={loading || paginaAtual >= totalPaginas}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Proxima
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
