import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import toast from "react-hot-toast";
import api from "../../api";
import { formatBRL, formatMoneyBRL } from "../../utils/formatters";
import { dataKeyLocal } from "./vendasFinanceiro/vendasFinanceiroDatas";
import { getDashboardPeriodFromSearch } from "../../pages/dashboard/dashboardOverview";
import { VENDAS_FINANCEIRO_CHANNEL_FILTERS } from "./vendasFinanceiroChannels";
import { exportarPlanilhasExcel } from "./vendasFinanceiro/vendasFinanceiroExcel";
import { dataRecebimentoBR, planilhasRecebimentos } from "./recebimentosVendasUtils";

const campoClass = "rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900";
const botaoClass =
  "rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 disabled:opacity-50";

export default function RecebimentosVendas() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [filtros, setFiltros] = useState(() => {
    const periodo = getDashboardPeriodFromSearch(searchParams);
    const hoje = new Date();
    return {
      data_inicio: periodo?.start || dataKeyLocal(new Date(hoje.getFullYear(), hoje.getMonth(), 1)),
      data_fim: periodo?.end || dataKeyLocal(hoje),
      canal_venda: "",
    };
  });
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState("");
  const [loading, setLoading] = useState(true);
  const [exportando, setExportando] = useState(false);
  const [atualizacao, setAtualizacao] = useState(0);
  const [pagina, setPagina] = useState(1);
  const chave = JSON.stringify(filtros);
  const relatorio = resultado?.chave === chave ? resultado.data : null;
  const canalLabel =
    VENDAS_FINANCEIRO_CHANNEL_FILTERS.find((c) => c.value === filtros.canal_venda)?.filterLabel ||
    "Todos os canais";

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setErro("");
    setPagina(1);
    if (!filtros.data_inicio || !filtros.data_fim || filtros.data_fim < filtros.data_inicio) {
      setErro("Selecione um período válido.");
      setLoading(false);
      return () => controller.abort();
    }
    api
      .get("/relatorios/vendas/recebimentos", { params: filtros, signal: controller.signal })
      .then(({ data }) => {
        if (!controller.signal.aborted) setResultado({ chave, data });
      })
      .catch((error) => {
        if (!controller.signal.aborted)
          setErro(
            typeof error?.response?.data?.detail === "string"
              ? error.response.data.detail
              : "Não foi possível carregar os recebimentos.",
          );
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [filtros, chave, atualizacao]);

  const movimentos = relatorio?.movimentos || [];
  const totalPaginas = Math.max(1, Math.ceil(movimentos.length / 50));
  const linhas = useMemo(
    () => movimentos.slice((pagina - 1) * 50, pagina * 50),
    [movimentos, pagina],
  );
  const alterar = (campo, valor) => setFiltros((anterior) => ({ ...anterior, [campo]: valor }));
  const mes = (deslocamento) => {
    const hoje = new Date();
    const inicio = new Date(hoje.getFullYear(), hoje.getMonth() + deslocamento, 1);
    const fim =
      deslocamento === 0 ? hoje : new Date(inicio.getFullYear(), inicio.getMonth() + 1, 0);
    setFiltros((anterior) => ({
      ...anterior,
      data_inicio: dataKeyLocal(inicio),
      data_fim: dataKeyLocal(fim),
    }));
  };
  const exportar = async (tipo) => {
    if (!relatorio || loading || erro) return;
    setExportando(true);
    try {
      const nome = `recebimentos_${relatorio.data_inicio}_${relatorio.data_fim}`;
      if (tipo === "excel") {
        await exportarPlanilhasExcel(planilhasRecebimentos(relatorio, canalLabel), `${nome}.xlsx`);
      } else {
        const { data } = await api.get("/relatorios/vendas/recebimentos/pdf", {
          params: filtros,
          responseType: "blob",
        });
        const url = URL.createObjectURL(data);
        const link = document.createElement("a");
        link.href = url;
        link.download = `${nome}.pdf`;
        link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
    } catch {
      toast.error("Não foi possível exportar os recebimentos.");
    } finally {
      setExportando(false);
    }
  };

  return (
    <div className="space-y-5 p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Recebimentos de vendas</h1>
          <p className="mt-1 text-sm text-gray-600">
            Pela data do recebimento, inclusive de vendas de meses anteriores.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            className={botaoClass}
            disabled={!relatorio || loading || !!erro || exportando}
            onClick={() => exportar("excel")}
          >
            Exportar Excel
          </button>
          <button
            className={botaoClass}
            disabled={!relatorio || loading || !!erro || exportando}
            onClick={() => exportar("pdf")}
          >
            Exportar PDF
          </button>
        </div>
      </div>
      <div className="flex flex-wrap items-end gap-3 rounded-xl border border-gray-200 bg-white p-4">
        <label className="grid gap-1 text-sm text-gray-700">
          Recebido de
          <input
            aria-label="Recebido de"
            type="date"
            className={campoClass}
            value={filtros.data_inicio}
            onChange={(e) => alterar("data_inicio", e.target.value)}
          />
        </label>
        <label className="grid gap-1 text-sm text-gray-700">
          Até
          <input
            aria-label="Recebido até"
            type="date"
            className={campoClass}
            value={filtros.data_fim}
            onChange={(e) => alterar("data_fim", e.target.value)}
          />
        </label>
        <label className="grid gap-1 text-sm text-gray-700">
          Canal da venda
          <select
            className={campoClass}
            value={filtros.canal_venda}
            onChange={(e) => alterar("canal_venda", e.target.value)}
          >
            {VENDAS_FINANCEIRO_CHANNEL_FILTERS.map((canal) => (
              <option key={canal.value} value={canal.value}>
                {canal.filterLabel}
              </option>
            ))}
          </select>
        </label>
        <button className={botaoClass} onClick={() => mes(-1)}>
          Mês anterior
        </button>
        <button className={botaoClass} onClick={() => mes(0)}>
          Este mês
        </button>
        <button className={botaoClass} onClick={() => setAtualizacao((n) => n + 1)}>
          Atualizar
        </button>
      </div>
      {erro ? (
        <div role="alert" className="rounded-lg bg-red-50 p-4 text-red-700">
          {erro}
        </div>
      ) : loading || !relatorio ? (
        <p role="status" className="p-6 text-gray-500">
          Carregando recebimentos...
        </p>
      ) : (
        <>
          <div className="rounded-xl border border-teal-200 bg-teal-50 p-5">
            <p className="text-sm font-semibold text-teal-800">Recebimentos de vendas no período</p>
            <p className="mt-1 text-3xl font-bold text-teal-950 dark:text-teal-100">
              {formatMoneyBRL(relatorio.resumo.total)}
            </p>
            <p className="mt-2 text-sm text-teal-800">
              {dataRecebimentoBR(relatorio.data_inicio)} a {dataRecebimentoBR(relatorio.data_fim)} ·{" "}
              {canalLabel}
            </p>
            {relatorio.resumo.devolucoes > 0 && (
              <p className="mt-1 text-sm text-teal-800">
                {formatMoneyBRL(relatorio.resumo.recebimentos)} recebidos, menos{" "}
                {formatMoneyBRL(relatorio.resumo.devolucoes)} devolvidos em dinheiro.
              </p>
            )}
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="mb-4 font-semibold text-gray-900">Recebimentos por dia</h2>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={relatorio.por_dia}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="data"
                    tickFormatter={(data) => dataRecebimentoBR(data).slice(0, 5)}
                    minTickGap={30}
                  />
                  <YAxis tickFormatter={formatBRL} width={85} />
                  <Tooltip
                    labelFormatter={dataRecebimentoBR}
                    formatter={(valor) => [formatMoneyBRL(valor), "Recebimentos"]}
                  />
                  <Bar dataKey="valor" fill="#0f8b8d" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
            <div className="p-4">
              <h2 className="font-semibold text-gray-900">Movimentos do período</h2>
              <p className="mt-1 text-sm text-gray-500">
                Cada parcela aparece na data em que foi recebida. Créditos e cashback utilizados não
                são dinheiro novo.
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-50 text-gray-600">
                  <tr>
                    {[
                      "Recebimento",
                      "Venda",
                      "Data da venda",
                      "Cliente",
                      "Forma",
                      "Movimento",
                      "Valor",
                    ].map((titulo) => (
                      <th key={titulo} className="whitespace-nowrap px-4 py-3">
                        {titulo}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {linhas.map((m) => (
                    <tr key={m.id}>
                      <td className="px-4 py-3">{dataRecebimentoBR(m.data_recebimento)}</td>
                      <td className="px-4 py-3">
                        <button
                          className="text-teal-700 underline"
                          onClick={() => navigate(`/pdv?venda_id=${m.venda_id}`)}
                        >
                          {m.numero_venda}
                        </button>
                      </td>
                      <td className="px-4 py-3">{dataRecebimentoBR(m.data_venda)}</td>
                      <td className="px-4 py-3">{m.cliente_nome}</td>
                      <td className="px-4 py-3">{m.forma_pagamento}</td>
                      <td className="px-4 py-3">
                        {m.tipo === "devolucao" ? "Devolução" : "Recebimento"}
                      </td>
                      <td
                        className={`whitespace-nowrap px-4 py-3 text-right font-medium ${m.valor < 0 ? "text-red-700" : "text-gray-900"}`}
                      >
                        {formatMoneyBRL(m.valor)}
                      </td>
                    </tr>
                  ))}
                  {movimentos.length === 0 && (
                    <tr>
                      <td colSpan={7} className="p-8 text-center text-gray-500">
                        Nenhum recebimento de venda neste período.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between gap-2 border-t border-gray-200 p-4 text-sm text-gray-600">
              <span>
                {movimentos.length} movimentos · Página {pagina} de {totalPaginas}
              </span>
              <div className="flex gap-2">
                <button
                  className={botaoClass}
                  disabled={pagina <= 1}
                  onClick={() => setPagina((n) => n - 1)}
                >
                  Anterior
                </button>
                <button
                  className={botaoClass}
                  disabled={pagina >= totalPaginas}
                  onClick={() => setPagina((n) => n + 1)}
                >
                  Próxima
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
