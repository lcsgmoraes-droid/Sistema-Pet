import { Filter, RotateCcw, Search } from "lucide-react";
import { CANAIS_VENDA, PERIODOS_ANALISE } from "./analiseProdutosUtils";

const inputClass =
  "w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100";

function nomeOpcao(item) {
  return item.nome || item.razao_social || item.nome_fantasia || `Registro ${item.id}`;
}

export default function AnaliseProdutosFiltros({
  catalogos,
  periodoAtivo,
  filtros,
  onPeriodoChange,
  onChange,
  onSubmit,
  onLimpar,
}) {
  return (
    <form
      onSubmit={onSubmit}
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex flex-wrap gap-2" aria-label="Períodos rápidos">
          {PERIODOS_ANALISE.map((periodo) => (
            <button
              key={periodo.id}
              type="button"
              onClick={() => onPeriodoChange(periodo)}
              className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
                periodoAtivo === periodo.id
                  ? "bg-blue-600 text-white shadow-sm"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              {periodo.label}
            </button>
          ))}
        </div>
        <p className="text-xs text-slate-500">
          A comparação usa o período anterior com a mesma quantidade de dias.
        </p>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <label className="text-sm font-medium text-slate-700">
          Data inicial
          <input
            type="date"
            value={filtros.data_inicio}
            onChange={(event) => onChange("data_inicio", event.target.value)}
            className={`${inputClass} mt-1`}
          />
        </label>
        <label className="text-sm font-medium text-slate-700">
          Data final
          <input
            type="date"
            value={filtros.data_fim}
            onChange={(event) => onChange("data_fim", event.target.value)}
            className={`${inputClass} mt-1`}
          />
        </label>
        <label className="text-sm font-medium text-slate-700">
          Categoria
          <select
            value={filtros.categoria_id}
            onChange={(event) => onChange("categoria_id", event.target.value)}
            className={`${inputClass} mt-1`}
          >
            <option value="">Todas as categorias</option>
            {catalogos.categorias.map((item) => (
              <option key={item.id} value={item.id}>
                {nomeOpcao(item)}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-medium text-slate-700">
          Marca
          <select
            value={filtros.marca_id}
            onChange={(event) => onChange("marca_id", event.target.value)}
            className={`${inputClass} mt-1`}
          >
            <option value="">Todas as marcas</option>
            {catalogos.marcas.map((item) => (
              <option key={item.id} value={item.id}>
                {nomeOpcao(item)}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-medium text-slate-700">
          Departamento
          <select
            value={filtros.departamento_id}
            onChange={(event) => onChange("departamento_id", event.target.value)}
            className={`${inputClass} mt-1`}
          >
            <option value="">Todos os departamentos</option>
            {catalogos.departamentos.map((item) => (
              <option key={item.id} value={item.id}>
                {nomeOpcao(item)}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-medium text-slate-700">
          Fornecedor
          <select
            value={filtros.fornecedor_id}
            onChange={(event) => onChange("fornecedor_id", event.target.value)}
            className={`${inputClass} mt-1`}
          >
            <option value="">Todos os fornecedores</option>
            {catalogos.fornecedores.map((item) => (
              <option key={item.id} value={item.id}>
                {nomeOpcao(item)}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-medium text-slate-700">
          Canal de venda
          <select
            value={filtros.canal}
            onChange={(event) => onChange("canal", event.target.value)}
            className={`${inputClass} mt-1`}
          >
            {CANAIS_VENDA.map((canal) => (
              <option key={canal.value || "todos"} value={canal.value}>
                {canal.label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-medium text-slate-700">
          Produto
          <span className="relative mt-1 block">
            <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" aria-hidden="true" />
            <input
              type="search"
              value={filtros.busca}
              onChange={(event) => onChange("busca", event.target.value)}
              placeholder="Nome, código ou código de barras"
              className={`${inputClass} pl-9`}
            />
          </span>
        </label>
      </div>

      <div className="mt-5 flex flex-wrap justify-end gap-3">
        <button
          type="button"
          onClick={onLimpar}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
        >
          <RotateCcw className="h-4 w-4" aria-hidden="true" />
          Limpar
        </button>
        <button
          type="submit"
          className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
        >
          <Filter className="h-4 w-4" aria-hidden="true" />
          Aplicar filtros
        </button>
      </div>
    </form>
  );
}
