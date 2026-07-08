import { useEffect, useMemo, useState } from "react";
import { BarChart3, CalendarDays, Filter, RefreshCw, X } from "lucide-react";
import toast from "react-hot-toast";

import api from "../../api";
import { safeArray } from "../../utils/safeArray";
import ActionButton from "../ui/ActionButton";

const CANAIS_RECEBER = [
  { id: "todos", label: "Todos" },
  { id: "loja_fisica", label: "Loja fisica" },
  { id: "mercado_livre", label: "Mercado Livre" },
  { id: "shopee", label: "Shopee" },
  { id: "amazon", label: "Amazon" },
  { id: "ecommerce", label: "E-commerce" },
  { id: "transferencia_parceiro", label: "Transferencia parceiro" },
];

const filtrosIniciais = {
  cliente_busca: "",
  cliente_ids: [],
  cliente_modo: "incluir",
  forma_pagamento_id: "",
  canal: "todos",
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
  por_cliente: [],
  por_forma_pagamento: [],
  por_canal: [],
  agenda_mensal: [],
};

export function getClienteNome(cliente) {
  return (
    cliente?.nome || cliente?.razao_social || cliente?.nome_fantasia || cliente?.fantasia || ""
  );
}

function montarParamsAnalise(filtros) {
  const params = new URLSearchParams();
  params.append("_t", Date.now());
  params.append("cliente_modo", filtros.cliente_modo);

  filtros.cliente_ids.forEach((id) => params.append("cliente_ids", id));
  if (filtros.forma_pagamento_id) {
    params.append("forma_pagamento_id", filtros.forma_pagamento_id);
  }
  if (filtros.canal !== "todos") {
    params.append("canal", filtros.canal);
  }

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

export default function ContasReceberAnalise({
  clientes,
  formasPagamento,
  formatarMoeda,
  onAbrirListaComFiltros,
}) {
  const [dados, setDados] = useState(resumoVazio);
  const [filtros, setFiltros] = useState(filtrosIniciais);
  const [clientesSelecionados, setClientesSelecionados] = useState([]);
  const [loading, setLoading] = useState(false);

  const clientesSelecionadosResolvidos = useMemo(() => {
    const porId = new Map();
    clientesSelecionados.forEach((cliente) => {
      if (cliente?.id) porId.set(String(cliente.id), cliente);
    });
    safeArray(clientes).forEach((cliente) => {
      if (filtros.cliente_ids.includes(String(cliente.id))) {
        porId.set(String(cliente.id), cliente);
      }
    });
    return Array.from(porId.values());
  }, [clientes, clientesSelecionados, filtros.cliente_ids]);

  const clientesFiltrados = useMemo(() => {
    const termo = filtros.cliente_busca.trim().toLocaleLowerCase("pt-BR");
    if (termo.length < 2) return [];

    return safeArray(clientes)
      .filter((cliente) => {
        if (filtros.cliente_ids.includes(String(cliente.id))) return false;
        const haystack = [
          cliente?.nome,
          cliente?.razao_social,
          cliente?.nome_fantasia,
          cliente?.fantasia,
          cliente?.cpf,
          cliente?.cnpj,
          cliente?.telefone,
          cliente?.celular,
        ]
          .filter(Boolean)
          .join(" ")
          .toLocaleLowerCase("pt-BR");
        return haystack.includes(termo);
      })
      .slice(0, 12);
  }, [clientes, filtros.cliente_busca, filtros.cliente_ids]);

  const carregarAnalise = async (filtrosParaAplicar = filtros) => {
    try {
      setLoading(true);
      const response = await api.get("/contas-receber/analise-abertos", {
        params: montarParamsAnalise(filtrosParaAplicar),
      });
      setDados({ ...resumoVazio, ...response.data });
    } catch (error) {
      console.error("Erro ao carregar analise de contas a receber:", error);
      toast.error(error?.response?.data?.detail || "Erro ao carregar analise");
      setDados(resumoVazio);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void carregarAnalise(filtros);
  }, []);

  const selecionarCliente = (cliente) => {
    if (!cliente?.id) return;
    const clienteId = String(cliente.id);
    setClientesSelecionados((atuais) => {
      if (atuais.some((item) => String(item.id) === clienteId)) return atuais;
      return [...atuais, cliente];
    });
    setFiltros((atuais) => ({
      ...atuais,
      cliente_busca: "",
      cliente_ids: atuais.cliente_ids.includes(clienteId)
        ? atuais.cliente_ids
        : [...atuais.cliente_ids, clienteId],
    }));
  };

  const removerCliente = (clienteId) => {
    setClientesSelecionados((atuais) =>
      atuais.filter((cliente) => String(cliente.id) !== String(clienteId)),
    );
    setFiltros((atuais) => ({
      ...atuais,
      cliente_ids: atuais.cliente_ids.filter((id) => String(id) !== String(clienteId)),
    }));
  };

  const aplicarFiltros = (event) => {
    event.preventDefault();
    void carregarAnalise(filtros);
  };

  const limparFiltros = () => {
    setClientesSelecionados([]);
    setFiltros(filtrosIniciais);
    void carregarAnalise(filtrosIniciais);
  };

  const abrirListaPeriodo = (periodo) => {
    onAbrirListaComFiltros?.({
      cliente_ids: filtros.cliente_ids,
      cliente_modo: filtros.cliente_modo,
      forma_pagamento_id: filtros.forma_pagamento_id,
      canal: filtros.canal,
      periodo_analise: periodo,
    });
  };

  const resumo = dados.resumo || resumoVazio.resumo;
  const modoTexto =
    filtros.cliente_modo === "excluir" && clientesSelecionadosResolvidos.length > 0
      ? `Tudo menos ${clientesSelecionadosResolvidos.map(getClienteNome).join(", ")}`
      : "Clientes selecionados";

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
              Totalize vencimentos por cliente, forma de pagamento, canal e agenda mensal.
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
            <label className="mb-1 block text-sm font-medium text-slate-700">Cliente</label>
            <select
              value={filtros.cliente_modo}
              onChange={(event) => setFiltros({ ...filtros, cliente_modo: event.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
            >
              <option value="incluir">Incluir selecionados</option>
              <option value="excluir">Excluir selecionados</option>
            </select>
          </div>
          <div className="relative md:col-span-2">
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Adicionar cliente
            </label>
            <input
              type="text"
              value={filtros.cliente_busca}
              onChange={(event) => setFiltros({ ...filtros, cliente_busca: event.target.value })}
              placeholder="Buscar cliente para incluir/excluir..."
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
            />
            {clientesFiltrados.length > 0 ? (
              <div className="absolute z-20 mt-2 max-h-72 w-full overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-lg">
                {clientesFiltrados.map((cliente) => (
                  <button
                    key={cliente.id}
                    type="button"
                    onClick={() => selecionarCliente(cliente)}
                    className="w-full border-b border-slate-100 px-4 py-3 text-left last:border-b-0 hover:bg-slate-50"
                  >
                    <div className="font-medium text-slate-900">{getClienteNome(cliente)}</div>
                    <div className="text-xs text-slate-500">
                      {[cliente.cpf || cliente.cnpj, cliente.telefone || cliente.celular]
                        .filter(Boolean)
                        .join(" - ")}
                    </div>
                  </button>
                ))}
              </div>
            ) : null}
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Forma pagamento</label>
            <select
              value={filtros.forma_pagamento_id}
              onChange={(event) =>
                setFiltros({ ...filtros, forma_pagamento_id: event.target.value })
              }
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
            >
              <option value="">Todas</option>
              {safeArray(formasPagamento).map((forma) => (
                <option key={forma.id} value={forma.id}>
                  {forma.nome}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Canal</label>
            <select
              value={filtros.canal}
              onChange={(event) => setFiltros({ ...filtros, canal: event.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
            >
              {CANAIS_RECEBER.map((canal) => (
                <option key={canal.id} value={canal.id}>
                  {canal.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {clientesSelecionadosResolvidos.map((cliente) => (
            <span
              key={cliente.id}
              className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-sm font-medium text-blue-800"
            >
              {getClienteNome(cliente)}
              <button
                type="button"
                onClick={() => removerCliente(cliente.id)}
                className="rounded-full p-0.5 hover:bg-blue-100"
                title="Remover cliente"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </span>
          ))}
          {clientesSelecionadosResolvidos.length === 0 ? (
            <span className="text-sm text-slate-500">Nenhum cliente selecionado.</span>
          ) : null}
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
          titulo="Por cliente"
          subtitulo="Quem concentra o contas a receber em aberto."
          itens={dados.por_cliente || []}
          formatarMoeda={formatarMoeda}
        />
        <TabelaResumo
          titulo="Por forma de pagamento"
          subtitulo="Separacao por dinheiro, cartao, Pix, boleto ou outros meios."
          itens={dados.por_forma_pagamento || []}
          formatarMoeda={formatarMoeda}
        />
        <TabelaResumo
          titulo="Por canal"
          subtitulo="Loja, marketplaces, e-commerce ou transferencia parceiro."
          itens={dados.por_canal || []}
          formatarMoeda={formatarMoeda}
        />
      </div>
    </div>
  );
}
