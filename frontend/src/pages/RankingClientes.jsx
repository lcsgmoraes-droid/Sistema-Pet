import { useEffect, useState } from "react";
import {
  Boxes,
  CalendarDays,
  DollarSign,
  RefreshCw,
  Search,
  ShoppingBag,
  Trophy,
  Users,
} from "lucide-react";

import api from "../api";
import RankingClientesDestaques from "../components/clientes/RankingClientesDestaques";
import RankingClientesTabela from "../components/clientes/RankingClientesTabela";
import LoadingState from "../components/ui/LoadingState";
import MetricCard from "../components/ui/MetricCard";
import PageHeader from "../components/ui/PageHeader";
import { formatMoneyBRL } from "../utils/formatters";
import { METRICAS_RANKING, obterPeriodoRanking } from "./clientes/rankingClientesUtils";

const ATALHOS_PERIODO = [
  ["hoje", "Hoje"],
  ["7_dias", "7 dias"],
  ["30_dias", "30 dias"],
  ["mes_atual", "Este mês"],
  ["mes_anterior", "Mês anterior"],
  ["ano_atual", "Este ano"],
];

const quantidade = (valor) =>
  Number(valor || 0).toLocaleString("pt-BR", {
    maximumFractionDigits: 3,
  });

export default function RankingClientes() {
  const periodoInicial = obterPeriodoRanking("mes_atual");
  const [periodoDigitado, setPeriodoDigitado] = useState(periodoInicial);
  const [filtros, setFiltros] = useState({
    ...periodoInicial,
    ordenar_por: "total_gasto",
    busca: "",
    pagina: 1,
  });
  const [buscaDigitada, setBuscaDigitada] = useState("");
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [atualizacao, setAtualizacao] = useState(0);

  useEffect(() => {
    let ativo = true;
    setCarregando(true);
    setErro("");

    api
      .get("/clientes/ranking-vendas", {
        params: {
          ...filtros,
          busca: filtros.busca || undefined,
          por_pagina: 50,
        },
      })
      .then(({ data }) => {
        if (ativo) setDados(data);
      })
      .catch((error) => {
        if (!ativo) return;
        const detalhe = error.response?.data?.detail;
        setDados(null);
        setErro(
          typeof detalhe === "string"
            ? detalhe
            : "Não foi possível carregar o ranking. Tente novamente.",
        );
      })
      .finally(() => {
        if (ativo) setCarregando(false);
      });

    return () => {
      ativo = false;
    };
  }, [atualizacao, filtros]);

  const aplicarPeriodo = (event) => {
    event?.preventDefault();
    if (periodoDigitado.data_inicio > periodoDigitado.data_fim) {
      setErro("A data inicial não pode ser posterior à data final.");
      return;
    }
    setFiltros((atual) => ({ ...atual, ...periodoDigitado, pagina: 1 }));
  };

  const usarAtalho = (tipo) => {
    const periodo = obterPeriodoRanking(tipo);
    setPeriodoDigitado(periodo);
    setFiltros((atual) => ({ ...atual, ...periodo, pagina: 1 }));
  };

  const buscar = (event) => {
    event.preventDefault();
    setFiltros((atual) => ({ ...atual, busca: buscaDigitada.trim(), pagina: 1 }));
  };

  const selecionarMetrica = (metrica) => {
    setFiltros((atual) => ({ ...atual, ordenar_por: metrica, pagina: 1 }));
  };

  const resumo = dados?.resumo || {};

  return (
    <div className="mx-auto max-w-[1500px] space-y-6 p-4 md:p-6">
      <PageHeader
        icon={Trophy}
        title="Ranking de clientes"
        subtitle="Veja rapidamente quem mais compra, mais gasta e leva mais itens em cada período."
        actions={
          <button
            type="button"
            onClick={() => setAtualizacao((valor) => valor + 1)}
            disabled={carregando}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
          >
            <RefreshCw className={`h-4 w-4 ${carregando ? "animate-spin" : ""}`} />
            Atualizar
          </button>
        }
      />

      <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-wrap gap-2">
          {ATALHOS_PERIODO.map(([tipo, label]) => (
            <button
              key={tipo}
              type="button"
              onClick={() => usarAtalho(tipo)}
              className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
            >
              {label}
            </button>
          ))}
        </div>

        <form onSubmit={aplicarPeriodo} className="grid gap-3 md:grid-cols-[1fr_1fr_auto]">
          <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
            Data inicial
            <input
              type="date"
              value={periodoDigitado.data_inicio}
              max={periodoDigitado.data_fim}
              onChange={(event) =>
                setPeriodoDigitado((atual) => ({
                  ...atual,
                  data_inicio: event.target.value,
                }))
              }
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700 dark:bg-slate-950"
            />
          </label>
          <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
            Data final
            <input
              type="date"
              value={periodoDigitado.data_fim}
              min={periodoDigitado.data_inicio}
              onChange={(event) =>
                setPeriodoDigitado((atual) => ({
                  ...atual,
                  data_fim: event.target.value,
                }))
              }
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700 dark:bg-slate-950"
            />
          </label>
          <button
            type="submit"
            className="mt-auto inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 py-2 font-semibold text-white hover:bg-blue-700"
          >
            <CalendarDays className="h-4 w-4" /> Aplicar período
          </button>
        </form>
      </section>

      {erro ? (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
        >
          {erro}
        </div>
      ) : null}

      {carregando && !dados ? (
        <LoadingState label="Calculando ranking de clientes..." />
      ) : dados ? (
        <>
          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              icon={<Users className="h-5 w-5" />}
              intent="blue"
              label="Clientes com compra"
              value={quantidade(resumo.clientes_com_compra)}
              subtitle="Vendas identificadas no período"
            />
            <MetricCard
              icon={<DollarSign className="h-5 w-5" />}
              intent="emerald"
              label="Faturamento identificado"
              value={formatMoneyBRL(resumo.faturamento_clientes)}
              subtitle="Somente vendas ligadas a clientes"
            />
            <MetricCard
              icon={<ShoppingBag className="h-5 w-5" />}
              intent="cyan"
              label="Compras"
              value={quantidade(resumo.total_compras)}
              subtitle="Quantidade de vendas finalizadas"
            />
            <MetricCard
              icon={<Boxes className="h-5 w-5" />}
              intent="violet"
              label="Itens vendidos"
              value={quantidade(resumo.total_itens)}
              subtitle="Soma das quantidades dos itens"
            />
          </section>

          <RankingClientesDestaques
            lideres={dados.lideres}
            onSelecionarMetrica={selecionarMetrica}
          />

          <section className="space-y-3">
            <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
              <div className="flex flex-wrap gap-2" role="group" aria-label="Ordenar ranking por">
                {Object.entries(METRICAS_RANKING).map(([metrica, config]) => (
                  <button
                    key={metrica}
                    type="button"
                    aria-pressed={filtros.ordenar_por === metrica}
                    onClick={() => selecionarMetrica(metrica)}
                    className={`rounded-lg border px-3 py-2 text-xs font-semibold transition ${
                      filtros.ordenar_por === metrica
                        ? "border-blue-600 bg-blue-600 text-white"
                        : "border-slate-200 bg-white text-slate-600 hover:border-blue-300 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
                    }`}
                  >
                    {config.label}
                  </button>
                ))}
              </div>

              <form onSubmit={buscar} className="flex min-w-0 gap-2 sm:min-w-[360px]">
                <label className="relative min-w-0 flex-1">
                  <span className="sr-only">Buscar cliente</span>
                  <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                  <input
                    type="search"
                    value={buscaDigitada}
                    onChange={(event) => setBuscaDigitada(event.target.value)}
                    placeholder="Nome, código ou telefone"
                    className="w-full rounded-lg border border-slate-200 py-2 pl-9 pr-3 text-sm dark:border-slate-700 dark:bg-slate-900"
                  />
                </label>
                <button
                  type="submit"
                  className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                >
                  Buscar
                </button>
              </form>
            </div>

            <RankingClientesTabela
              clientes={dados.clientes}
              metrica={filtros.ordenar_por}
              paginacao={dados.paginacao}
              onMudarPagina={(pagina) => setFiltros((atual) => ({ ...atual, pagina }))}
            />
          </section>
        </>
      ) : null}
    </div>
  );
}
