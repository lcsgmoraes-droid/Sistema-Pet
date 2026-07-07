import { useEffect, useMemo, useState } from "react";
import { BarChart3, CalendarDays, Filter, RefreshCw, X } from "lucide-react";
import toast from "react-hot-toast";

import api from "../../api";
import ActionButton from "../ui/ActionButton";
import FornecedorSelector, { getFornecedorNome } from "../fornecedores/FornecedorSelector";

const filtrosIniciais = {
  fornecedor_busca: "",
  fornecedor_ids: [],
  fornecedor_modo: "incluir",
  origem: "todos",
  tipo_despesa_id: "",
  tipo_custo: "todos",
  ocultar_taxas_cartao: true,
  apenas_taxas_cartao: false,
};

const resumoVazio = {
  resumo: {
    quantidade: 0,
    total_aberto: 0,
    vencido: { quantidade: 0, total_aberto: 0 },
    hoje: { quantidade: 0, total_aberto: 0 },
    amanha: { quantidade: 0, total_aberto: 0 },
    proximos_7_dias: { quantidade: 0, total_aberto: 0 },
    mes_atual: { quantidade: 0, total_aberto: 0 },
    proximos_12_meses: { quantidade: 0, total_aberto: 0 },
  },
  por_fornecedor: [],
  por_tipo_despesa: [],
  por_origem: [],
  por_tipo_custo: [],
  agenda_mensal: [],
};

function montarParamsAnalise(filtros) {
  const params = new URLSearchParams();
  params.append("_t", Date.now());
  params.append("fornecedor_modo", filtros.fornecedor_modo);
  params.append("ocultar_taxas_cartao", filtros.ocultar_taxas_cartao ? "true" : "false");
  params.append("apenas_taxas_cartao", filtros.apenas_taxas_cartao ? "true" : "false");

  filtros.fornecedor_ids.forEach((id) => params.append("fornecedor_ids", id));
  if (filtros.origem !== "todos") params.append("origem", filtros.origem);
  if (filtros.tipo_despesa_id) params.append("tipo_despesa_id", filtros.tipo_despesa_id);
  if (filtros.tipo_custo !== "todos") params.append("tipo_custo", filtros.tipo_custo);

  return params;
}

function PainelResumo({ titulo, valor, detalhe, destaque = "slate", onClick }) {
  const estilos = {
    slate: "border-slate-200 bg-white text-slate-900",
    amber: "border-amber-200 bg-amber-50 text-amber-950",
    blue: "border-blue-200 bg-blue-50 text-blue-950",
    emerald: "border-emerald-200 bg-emerald-50 text-emerald-950",
    red: "border-red-200 bg-red-50 text-red-950",
    violet: "border-violet-200 bg-violet-50 text-violet-950",
  };

  return (
    <button
      type="button"
      onClick={onClick}
      className={`min-h-[96px] rounded-lg border p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md ${
        estilos[destaque] || estilos.slate
      }`}
    >
      <div className="text-xs font-semibold uppercase">{titulo}</div>
      <div className="mt-2 text-xl font-bold leading-tight">{valor}</div>
      <div className="mt-1 text-xs opacity-80">{detalhe}</div>
    </button>
  );
}

function TabelaResumo({ titulo, subtitulo, itens, formatarMoeda }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 px-4 py-3">
        <h3 className="text-sm font-semibold text-slate-900">{titulo}</h3>
        <p className="text-xs text-slate-500">{subtitulo}</p>
      </div>
      <div className="max-h-[340px] overflow-auto">
        {itens.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-slate-500">Sem dados no filtro.</div>
        ) : (
          <table className="min-w-full divide-y divide-slate-100">
            <tbody className="divide-y divide-slate-100">
              {itens.map((item) => (
                <tr key={`${item.id}-${item.nome}`} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{item.nome}</div>
                    <div className="text-xs text-slate-500">{item.quantidade} conta(s)</div>
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-slate-900">
                    {formatarMoeda(item.total_aberto)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}

export default function ContasPagarAnalise({
  fornecedores,
  formatarMoeda,
  onAbrirListaComFiltros,
  tiposDespesaOrdenados,
}) {
  const [dados, setDados] = useState(resumoVazio);
  const [filtros, setFiltros] = useState(filtrosIniciais);
  const [fornecedoresSelecionados, setFornecedoresSelecionados] = useState([]);
  const [loading, setLoading] = useState(false);

  const fornecedoresSelecionadosResolvidos = useMemo(() => {
    const porId = new Map();
    fornecedoresSelecionados.forEach((fornecedor) => {
      if (fornecedor?.id) porId.set(String(fornecedor.id), fornecedor);
    });
    fornecedores.forEach((fornecedor) => {
      if (filtros.fornecedor_ids.includes(String(fornecedor.id))) {
        porId.set(String(fornecedor.id), fornecedor);
      }
    });
    return Array.from(porId.values());
  }, [filtros.fornecedor_ids, fornecedores, fornecedoresSelecionados]);

  const carregarAnalise = async (filtrosParaAplicar = filtros) => {
    try {
      setLoading(true);
      const response = await api.get("/contas-pagar/analise-abertos", {
        params: montarParamsAnalise(filtrosParaAplicar),
      });
      setDados({ ...resumoVazio, ...response.data });
    } catch (error) {
      console.error("Erro ao carregar analise de contas a pagar:", error);
      toast.error(error?.response?.data?.detail || "Erro ao carregar analise");
      setDados(resumoVazio);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void carregarAnalise(filtros);
  }, []);

  const selecionarFornecedor = (fornecedor) => {
    if (!fornecedor?.id) return;
    const fornecedorId = String(fornecedor.id);
    setFornecedoresSelecionados((atuais) => {
      if (atuais.some((item) => String(item.id) === fornecedorId)) return atuais;
      return [...atuais, fornecedor];
    });
    setFiltros((atuais) => ({
      ...atuais,
      fornecedor_busca: "",
      fornecedor_ids: atuais.fornecedor_ids.includes(fornecedorId)
        ? atuais.fornecedor_ids
        : [...atuais.fornecedor_ids, fornecedorId],
    }));
  };

  const removerFornecedor = (fornecedorId) => {
    setFornecedoresSelecionados((atuais) =>
      atuais.filter((fornecedor) => String(fornecedor.id) !== String(fornecedorId)),
    );
    setFiltros((atuais) => ({
      ...atuais,
      fornecedor_ids: atuais.fornecedor_ids.filter((id) => String(id) !== String(fornecedorId)),
    }));
  };

  const aplicarFiltros = (event) => {
    event.preventDefault();
    void carregarAnalise(filtros);
  };

  const limparFiltros = () => {
    setFornecedoresSelecionados([]);
    setFiltros(filtrosIniciais);
    void carregarAnalise(filtrosIniciais);
  };

  const abrirListaPeriodo = (periodo) => {
    onAbrirListaComFiltros?.({
      fornecedor_ids: filtros.fornecedor_ids,
      fornecedor_modo: filtros.fornecedor_modo,
      ocultar_taxas_cartao: filtros.ocultar_taxas_cartao,
      apenas_taxas_cartao: filtros.apenas_taxas_cartao,
      origem: filtros.origem,
      tipo_despesa_id: filtros.tipo_despesa_id,
      tipo_custo: filtros.tipo_custo,
      periodo_analise: periodo,
    });
  };

  const resumo = dados.resumo || resumoVazio.resumo;
  const modoTexto =
    filtros.fornecedor_modo === "excluir" && fornecedoresSelecionadosResolvidos.length > 0
      ? `Tudo menos ${fornecedoresSelecionadosResolvidos.map(getFornecedorNome).join(", ")}`
      : "Todos os fornecedores selecionados";

  return (
    <div className="space-y-5">
      <form onSubmit={aplicarFiltros} className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
              <BarChart3 className="h-5 w-5 text-blue-600" />
              Analise de contas em aberto
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Totalize vencimentos por fornecedor, tipo, origem e agenda mensal.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <ActionButton type="button" tone="soft" onClick={limparFiltros}>
              Limpar filtros
            </ActionButton>
            <ActionButton type="submit" icon={RefreshCw} loading={loading}>
              Atualizar analise
            </ActionButton>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-6">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Fornecedor</label>
            <select
              value={filtros.fornecedor_modo}
              onChange={(event) => setFiltros({ ...filtros, fornecedor_modo: event.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
            >
              <option value="incluir">Incluir selecionados</option>
              <option value="excluir">Excluir selecionados</option>
            </select>
          </div>
          <div className="md:col-span-2">
            <FornecedorSelector
              allowCreate={false}
              fornecedores={fornecedores}
              fornecedorId=""
              fornecedorSelecionado={null}
              label="Adicionar fornecedor"
              placeholder="Buscar fornecedor para incluir/excluir..."
              value={filtros.fornecedor_busca}
              onInputChange={(termo) => setFiltros({ ...filtros, fornecedor_busca: termo })}
              onSelect={selecionarFornecedor}
              onClear={() => setFiltros({ ...filtros, fornecedor_busca: "" })}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Origem</label>
            <select
              value={filtros.origem}
              onChange={(event) => setFiltros({ ...filtros, origem: event.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
            >
              <option value="todos">Todas</option>
              <option value="nota_entrada">Nota de entrada</option>
              <option value="caixa_pdv">Caixa/PDV</option>
              <option value="manual">Manual</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Tipo despesa</label>
            <select
              value={filtros.tipo_despesa_id}
              onChange={(event) => setFiltros({ ...filtros, tipo_despesa_id: event.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
            >
              <option value="">Todos</option>
              {tiposDespesaOrdenados.map((tipo) => (
                <option key={tipo.id} value={tipo.id}>
                  {tipo.nome}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Tipo custo</label>
            <select
              value={filtros.tipo_custo}
              onChange={(event) => setFiltros({ ...filtros, tipo_custo: event.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
            >
              <option value="todos">Todos</option>
              <option value="fixo">Fixo</option>
              <option value="variavel">Variavel</option>
            </select>
          </div>
        </div>

        <div className="mt-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-wrap gap-2">
            {fornecedoresSelecionadosResolvidos.map((fornecedor) => (
              <span
                key={fornecedor.id}
                className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-sm font-medium text-blue-800"
              >
                {getFornecedorNome(fornecedor)}
                <button
                  type="button"
                  onClick={() => removerFornecedor(fornecedor.id)}
                  className="rounded-full p-0.5 hover:bg-blue-100"
                  title="Remover fornecedor"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </span>
            ))}
            {fornecedoresSelecionadosResolvidos.length === 0 ? (
              <span className="text-sm text-slate-500">Nenhum fornecedor selecionado.</span>
            ) : null}
          </div>
          <label className="inline-flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={filtros.ocultar_taxas_cartao}
              onChange={(event) =>
                setFiltros({
                  ...filtros,
                  ocultar_taxas_cartao: event.target.checked,
                  apenas_taxas_cartao: false,
                })
              }
              className="h-4 w-4"
            />
            Ocultar taxas de cartao
          </label>
        </div>

        <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
          <Filter className="mr-2 inline h-4 w-4 text-slate-500" />
          {modoTexto}
        </div>
      </form>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-6">
        <PainelResumo
          titulo="Total aberto"
          valor={formatarMoeda(resumo.total_aberto)}
          detalhe={`${resumo.quantidade} conta(s)`}
          destaque="slate"
          onClick={() => abrirListaPeriodo("todos")}
        />
        <PainelResumo
          titulo="Vencido"
          valor={formatarMoeda(resumo.vencido?.total_aberto)}
          detalhe={`${resumo.vencido?.quantidade || 0} conta(s)`}
          destaque="red"
          onClick={() => abrirListaPeriodo("vencido")}
        />
        <PainelResumo
          titulo="Hoje"
          valor={formatarMoeda(resumo.hoje?.total_aberto)}
          detalhe={`${resumo.hoje?.quantidade || 0} conta(s)`}
          destaque="blue"
          onClick={() => abrirListaPeriodo("hoje")}
        />
        <PainelResumo
          titulo="Amanha"
          valor={formatarMoeda(resumo.amanha?.total_aberto)}
          detalhe={`${resumo.amanha?.quantidade || 0} conta(s)`}
          destaque="emerald"
          onClick={() => abrirListaPeriodo("amanha")}
        />
        <PainelResumo
          titulo="Mes atual"
          valor={formatarMoeda(resumo.mes_atual?.total_aberto)}
          detalhe={`${resumo.mes_atual?.quantidade || 0} conta(s)`}
          destaque="amber"
          onClick={() => abrirListaPeriodo("mes")}
        />
        <PainelResumo
          titulo="Proximos 12 meses"
          valor={formatarMoeda(resumo.proximos_12_meses?.total_aberto)}
          detalhe={`${resumo.proximos_12_meses?.quantidade || 0} conta(s)`}
          destaque="violet"
          onClick={() => abrirListaPeriodo("proximos_12_meses")}
        />
      </div>

      <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center gap-2 border-b border-slate-200 px-4 py-3">
          <CalendarDays className="h-4 w-4 text-blue-600" />
          <h3 className="text-sm font-semibold text-slate-900">Agenda mensal</h3>
        </div>
        <div className="grid grid-cols-1 gap-2 p-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
          {dados.agenda_mensal.map((mes) => (
            <div key={mes.mes} className="rounded-lg border border-slate-200 p-3">
              <div className="text-xs font-semibold uppercase text-slate-500">{mes.label}</div>
              <div className="mt-1 font-bold text-slate-900">{formatarMoeda(mes.total_aberto)}</div>
              <div className="text-xs text-slate-500">{mes.quantidade} conta(s)</div>
            </div>
          ))}
        </div>
      </section>

      <div className="grid gap-4 xl:grid-cols-2">
        <TabelaResumo
          titulo="Por fornecedor"
          subtitulo="Quem concentra o contas a pagar em aberto."
          itens={dados.por_fornecedor || []}
          formatarMoeda={formatarMoeda}
        />
        <TabelaResumo
          titulo="Por tipo de despesa"
          subtitulo="Separacao gerencial dos compromissos."
          itens={dados.por_tipo_despesa || []}
          formatarMoeda={formatarMoeda}
        />
        <TabelaResumo
          titulo="Por origem"
          subtitulo="Nota de entrada, caixa/PDV ou lancamento manual."
          itens={dados.por_origem || []}
          formatarMoeda={formatarMoeda}
        />
        <TabelaResumo
          titulo="Por tipo de custo"
          subtitulo="Fixo, variavel ou sem classificacao."
          itens={dados.por_tipo_custo || []}
          formatarMoeda={formatarMoeda}
        />
      </div>
    </div>
  );
}
