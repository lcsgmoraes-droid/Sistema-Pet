import { Search, Sparkles } from "lucide-react";

import OfertaProdutoCard from "./OfertaProdutoCard";
import { ESTRATEGIAS } from "./ofertasEstudioUtils";

const FILTROS = {
  todos: "Todos",
  validade: "Validade próxima",
  sem_imagem: "Sem imagem",
};

export default function OfertaSelecao({
  produtos,
  selecionados,
  busca,
  onBusca,
  filtro,
  onFiltro,
  estrategia,
  onEstrategia,
  dias,
  onDias,
  onSugerir,
  sugerindo,
  onToggle,
  onSelecionarTodos,
  onUpload,
  enviandoImagemId,
  carregando,
}) {
  const selecionadosIds = new Set(selecionados.map((item) => item.produto_id));
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <h2 className="font-black text-slate-950">Escolha os produtos</h2>
          <p className="text-xs text-slate-500">
            Somente produtos ativos, com estoque e não vencidos aparecem aqui.
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-2 rounded-xl bg-violet-50 p-3">
          <label className="text-[10px] font-black uppercase text-violet-800">
            Montar sugestão
            <select
              value={estrategia}
              onChange={(event) => onEstrategia(event.target.value)}
              className="mt-1 h-9 rounded-lg border border-violet-200 bg-white px-2 text-xs normal-case text-slate-800"
            >
              {Object.entries(ESTRATEGIAS).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-[10px] font-black uppercase text-violet-800">
            Período
            <select
              value={dias}
              onChange={(event) => onDias(Number(event.target.value))}
              className="mt-1 h-9 rounded-lg border border-violet-200 bg-white px-2 text-xs normal-case text-slate-800"
            >
              <option value={1}>Último dia</option>
              <option value={7}>Últimos 7 dias</option>
              <option value={30}>Últimos 30 dias</option>
              <option value={90}>Últimos 90 dias</option>
            </select>
          </label>
          <button
            type="button"
            onClick={onSugerir}
            disabled={sugerindo}
            className="inline-flex h-9 items-center gap-2 rounded-lg bg-violet-600 px-3 text-xs font-black text-white disabled:opacity-50"
          >
            <Sparkles size={15} /> {sugerindo ? "Montando..." : "Montar"}
          </button>
        </div>
      </div>

      <div className="mt-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="relative flex-1">
          <Search size={17} className="absolute left-3 top-3 text-slate-400" />
          <input
            value={busca}
            onChange={(event) => onBusca(event.target.value)}
            className="h-10 w-full rounded-lg border border-slate-300 pl-10 pr-3 text-sm"
            placeholder="Buscar por nome, código ou código de barras"
          />
        </div>
        <button
          type="button"
          onClick={onSelecionarTodos}
          disabled={!produtos.length}
          className="h-10 rounded-lg border border-slate-300 px-4 text-xs font-bold text-slate-700 disabled:opacity-50"
        >
          {produtos.every((produto) => selecionadosIds.has(produto.id))
            ? "Desmarcar exibidos"
            : "Selecionar exibidos"}
        </button>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {Object.entries(FILTROS).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => onFiltro(key)}
            className={`rounded-full px-3 py-1.5 text-xs font-bold ${filtro === key ? "bg-teal-700 text-white" : "bg-slate-100 text-slate-600"}`}
          >
            {label}
          </button>
        ))}
        <span className="ml-auto self-center text-xs font-bold text-slate-500">
          {selecionados.length} selecionado(s)
        </span>
      </div>

      {carregando ? (
        <div className="py-12 text-center text-sm text-slate-500">Carregando produtos...</div>
      ) : produtos.length ? (
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {produtos.map((produto) => (
            <OfertaProdutoCard
              key={produto.id}
              produto={produto}
              selecionado={selecionadosIds.has(produto.id)}
              onToggle={() => onToggle(produto)}
              onUpload={(file) => onUpload(produto, file)}
              enviandoImagem={enviandoImagemId === produto.id}
            />
          ))}
        </div>
      ) : (
        <div className="mt-4 rounded-xl bg-slate-50 py-12 text-center text-sm text-slate-500">
          Nenhum produto encontrado neste filtro.
        </div>
      )}
    </section>
  );
}
