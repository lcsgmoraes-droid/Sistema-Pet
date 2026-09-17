import { ChevronLeft, ChevronRight, Medal } from "lucide-react";
import { useNavigate } from "react-router-dom";

import EmptyState from "../ui/EmptyState";
import { formatMoneyBRL } from "../../utils/formatters";
import { METRICAS_RANKING } from "../../pages/clientes/rankingClientesUtils";

const quantidade = (valor) =>
  Number(valor || 0).toLocaleString("pt-BR", {
    maximumFractionDigits: 3,
  });

const dataCurta = (valor) => {
  if (!valor) return "—";
  return new Date(valor).toLocaleDateString("pt-BR", { timeZone: "America/Sao_Paulo" });
};

function Posicao({ valor }) {
  const destaque = valor <= 3;
  return (
    <span
      className={`inline-flex h-8 min-w-8 items-center justify-center rounded-full px-2 text-sm font-bold ${
        destaque
          ? "bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-amber-200"
          : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
      }`}
    >
      {destaque ? <Medal className="mr-1 h-3.5 w-3.5" aria-hidden="true" /> : null}
      {valor}º
    </span>
  );
}

export default function RankingClientesTabela({ clientes, metrica, onMudarPagina, paginacao }) {
  const navigate = useNavigate();
  const totalClientes = Number(paginacao?.total || 0);

  if (!clientes?.length) {
    return (
      <EmptyState
        icon={Medal}
        title="Nenhum cliente encontrado"
        description="Não existem vendas finalizadas e identificadas para este período ou busca."
      />
    );
  }

  const posicao = (cliente) =>
    metrica === "ultima_compra" ? "—" : cliente.posicoes?.[metrica] || "—";

  return (
    <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-5 py-4 dark:border-slate-800">
        <div>
          <h2 className="font-semibold text-slate-900 dark:text-slate-100">
            Ranking por {METRICAS_RANKING[metrica]?.label.toLowerCase()}
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {totalClientes} {totalClientes === 1 ? "cliente encontrado" : "clientes encontrados"}
          </p>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          Clique no cliente para abrir o histórico
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[880px] text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-950/50 dark:text-slate-400">
            <tr>
              <th className="px-4 py-3 text-center">Posição</th>
              <th className="px-4 py-3 text-left">Cliente</th>
              <th className="px-4 py-3 text-right">Total gasto</th>
              <th className="px-4 py-3 text-center">Compras</th>
              <th className="px-4 py-3 text-center">Itens</th>
              <th className="px-4 py-3 text-right">Ticket médio</th>
              <th className="px-4 py-3 text-right">Última compra</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {clientes.map((cliente) => (
              <tr
                key={cliente.cliente_id}
                onClick={() => navigate(`/clientes/${cliente.cliente_id}/financeiro`)}
                className="cursor-pointer transition hover:bg-blue-50/60 dark:hover:bg-blue-500/5"
              >
                <td className="px-4 py-3 text-center">
                  {posicao(cliente) === "—" ? "—" : <Posicao valor={posicao(cliente)} />}
                </td>
                <td className="px-4 py-3">
                  <p className="font-semibold text-slate-900 dark:text-slate-100">{cliente.nome}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {cliente.codigo ? `Código ${cliente.codigo}` : `ID ${cliente.cliente_id}`}
                    {cliente.telefone ? ` · ${cliente.telefone}` : ""}
                  </p>
                </td>
                <td className="px-4 py-3 text-right font-semibold text-slate-900 dark:text-slate-100">
                  {formatMoneyBRL(cliente.total_gasto)}
                </td>
                <td className="px-4 py-3 text-center text-slate-700 dark:text-slate-300">
                  {quantidade(cliente.total_compras)}
                </td>
                <td className="px-4 py-3 text-center text-slate-700 dark:text-slate-300">
                  {quantidade(cliente.total_itens)}
                </td>
                <td className="px-4 py-3 text-right text-slate-700 dark:text-slate-300">
                  {formatMoneyBRL(cliente.ticket_medio)}
                </td>
                <td className="px-4 py-3 text-right text-slate-500 dark:text-slate-400">
                  {dataCurta(cliente.ultima_compra)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between gap-3 border-t border-slate-200 px-5 py-3 dark:border-slate-800">
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Página {paginacao.pagina} de {paginacao.total_paginas}
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            aria-label="Página anterior"
            disabled={paginacao.pagina <= 1}
            onClick={() => onMudarPagina(paginacao.pagina - 1)}
            className="rounded-lg border p-2 text-slate-600 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:text-slate-300"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <button
            type="button"
            aria-label="Próxima página"
            disabled={paginacao.pagina >= paginacao.total_paginas}
            onClick={() => onMudarPagina(paginacao.pagina + 1)}
            className="rounded-lg border p-2 text-slate-600 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:text-slate-300"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </section>
  );
}
