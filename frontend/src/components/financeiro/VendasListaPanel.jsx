import MetricCard from "../ui/MetricCard";
import MetricGrid from "../ui/MetricGrid";
import VendasFinanceiroListaTable from "./VendasFinanceiroListaTable";
import {
  CANAL_LOJA_FISICA,
  normalizeSalesChannel,
} from "../../utils/salesChannel";
import { VENDAS_FINANCEIRO_CHANNEL_FILTERS } from "./vendasFinanceiroChannels";

const formatCurrencyCompact = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
});

function obterCanalVenda(venda) {
  return normalizeSalesChannel(
    venda?.canal_venda ||
      venda?.origem_canal_venda ||
      venda?.canal ||
      venda?.origem ||
      venda?.origem_loja_virtual,
    CANAL_LOJA_FISICA,
  );
}

function montarResumoCanais(vendas = []) {
  const resumo = new Map();
  VENDAS_FINANCEIRO_CHANNEL_FILTERS.forEach((canal) => {
    resumo.set(canal.value, { quantidade: 0, total: 0 });
  });

  vendas.forEach((venda) => {
    const canal = obterCanalVenda(venda);
    const total = Number(venda?.venda_bruta || venda?.valor_total || 0);

    const consolidado = resumo.get("");
    consolidado.quantidade += 1;
    consolidado.total += total;

    const atual = resumo.get(canal) || { quantidade: 0, total: 0 };
    atual.quantidade += 1;
    atual.total += total;
    resumo.set(canal, atual);
  });

  return resumo;
}

export default function VendasListaPanel({
  abrirVendaNoPdv,
  cardsTotalizadoresLista,
  filtroCanalVenda,
  filtroStatusLista,
  formatarData,
  formatarMoeda,
  getStatusVendaMeta,
  limparFiltroStatusLista,
  listaVendasFiltrada,
  listaVendasVisiveis,
  mostrarImpostoTodasVendas,
  setFiltroCanalVenda,
  setFiltroStatusLista,
  setMostrarImpostoTodasVendas,
  toggleVendaExpandida,
  vendasExpandidas,
}) {
  const resumoCanais = montarResumoCanais(listaVendasVisiveis);

  return (
    <div className="rounded-lg bg-white shadow">
      <div className="rounded-t-lg bg-gray-600 px-3 py-2 font-semibold text-white sm:px-4">
        Lista de Vendas com Analise de Rentabilidade
      </div>
      <div className="border-b border-gray-100 px-3 py-3 sm:px-4">
        <div className="mb-2 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="text-sm font-semibold text-slate-800">Canal da venda</div>
            <div className="text-xs text-slate-500">
              Filtre sem adicionar novas colunas na tabela.
            </div>
          </div>
          <div className="text-xs text-slate-500">
            {filtroCanalVenda ? "Visao filtrada por canal" : "Visao consolidada"}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
          {VENDAS_FINANCEIRO_CHANNEL_FILTERS.map((canal) => {
            const ativo = filtroCanalVenda === canal.value;
            const resumo = resumoCanais.get(canal.value) || { quantidade: 0, total: 0 };

            return (
              <button
                key={canal.value || "consolidado"}
                type="button"
                onClick={() => setFiltroCanalVenda(canal.value)}
                className={`rounded-lg border px-3 py-2 text-left transition ${ativo ? canal.activeClass : canal.idleClass}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-bold">{canal.label}</span>
                  <span className="rounded-full bg-white/70 px-2 py-0.5 text-xs font-bold text-slate-700">
                    {resumo.quantidade}
                  </span>
                </div>
                <div className="mt-0.5 text-xs opacity-80">{canal.description}</div>
                <div className="mt-1 text-xs font-semibold">
                  {formatCurrencyCompact.format(resumo.total)}
                </div>
              </button>
            );
          })}
        </div>
      </div>
      <div className="flex flex-col gap-3 border-b border-gray-100 px-3 py-3 lg:flex-row lg:items-center lg:justify-between sm:px-4">
        <div className="grid w-full grid-cols-2 gap-2 sm:flex sm:flex-wrap sm:items-center lg:w-auto">
          <button
            type="button"
            onClick={limparFiltroStatusLista}
            className={`w-full rounded-full px-3 py-2 text-sm font-semibold transition sm:w-auto sm:py-1 ${
              filtroStatusLista === ""
                ? "bg-blue-600 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            Todas
          </button>
          <button
            type="button"
            onClick={() => setFiltroStatusLista("em_aberto")}
            className={`w-full rounded-full px-3 py-2 text-sm font-semibold transition sm:w-auto sm:py-1 ${
              filtroStatusLista === "em_aberto"
                ? "bg-red-600 text-white"
                : "bg-red-50 text-red-700 hover:bg-red-100"
            }`}
          >
            Em aberto
          </button>
          <label
            className="col-span-2 inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm sm:w-auto sm:py-1"
            title="Marcado: mostra imposto estimado em todas as vendas. Desmarcado: mostra imposto somente em vendas com NF/NFC-e vinculada."
          >
            <input
              type="checkbox"
              checked={mostrarImpostoTodasVendas}
              onChange={(event) => setMostrarImpostoTodasVendas(event.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            Mostrar TUDO com imposto
          </label>
        </div>
        <div className="text-xs text-slate-500 sm:text-sm">
          Mostrando {listaVendasFiltrada.length} de {listaVendasVisiveis.length} venda(s)
        </div>
      </div>
      <MetricGrid className="border-b border-gray-100 bg-slate-50 px-3 py-3 sm:grid-cols-2 sm:px-4 md:grid-cols-4 xl:grid-cols-8">
        {cardsTotalizadoresLista.map((card) => (
          <MetricCard
            key={card.label}
            intent={card.intent}
            label={card.label}
            size="compact"
            value={card.value}
          />
        ))}
      </MetricGrid>
      <VendasFinanceiroListaTable
        abrirVendaNoPdv={abrirVendaNoPdv}
        formatarData={formatarData}
        formatarMoeda={formatarMoeda}
        getStatusVendaMeta={getStatusVendaMeta}
        onToggleVenda={toggleVendaExpandida}
        vendas={listaVendasFiltrada}
        vendasExpandidas={vendasExpandidas}
      />
    </div>
  );
}
