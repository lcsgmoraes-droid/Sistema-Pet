import { FiAlertTriangle, FiPackage, FiRefreshCw, FiTrash2 } from "react-icons/fi";
import { formatarDataValidade, formatarMoeda } from "./lembretesFormatters";

export default function LembretesValidadeSection({ controller }) {
  return (
    <>
      {controller.validadeInativa && <ValidadeInativa controller={controller} />}
      {controller.validadeAtivaSemPendencias && <ValidadeAtiva controller={controller} />}
      {controller.validadePendencias.length > 0 && <ValidadePendencias controller={controller} />}
    </>
  );
}

function ValidadeInativa({ controller }) {
  return (
    <div className="mb-5 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 shadow-sm dark:border-amber-500/30 dark:bg-amber-500/10">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white text-amber-700 shadow-sm ring-1 ring-amber-200 dark:bg-slate-900 dark:text-amber-300 dark:ring-amber-500/30">
          <FiAlertTriangle aria-hidden="true" />
        </span>
        <div>
          <p className="m-0 font-semibold text-amber-900 dark:text-amber-200">
            Protecao por validade desativada
          </p>
          <p className="mt-1 text-sm leading-5 text-amber-800 dark:text-amber-100/80">
            Ative a protecao para retirar automaticamente os lotes que vencem em ate{" "}
            {controller.validadeConfig.dias || 15} dia(s) e gerar pendencias aqui.
          </p>
        </div>
      </div>
      <button
        type="button"
        className="inline-flex items-center justify-center rounded-xl border border-amber-300 bg-white px-4 py-2 text-sm font-semibold text-amber-800 shadow-sm transition hover:bg-amber-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-600 dark:border-amber-500/40 dark:bg-slate-900 dark:text-amber-200 dark:hover:bg-slate-800"
        onClick={controller.irConfiguracoesEstoque}
      >
        Abrir configuracoes
      </button>
    </div>
  );
}

function ValidadeAtiva({ controller }) {
  return (
    <div className="mb-5 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-teal-200 bg-teal-50 px-5 py-4 shadow-sm dark:border-teal-500/30 dark:bg-teal-500/10">
      <div>
        <p className="m-0 font-semibold text-teal-900 dark:text-teal-200">
          Protecao por validade ativa
        </p>
        <p className="mt-1 text-sm leading-5 text-teal-800 dark:text-teal-100/80">
          A busca automatica considera lotes que vencem em ate{" "}
          {controller.validadeConfig.dias || 15} dia(s).
        </p>
      </div>
      <VerificarValidadeButton controller={controller} />
    </div>
  );
}

function ValidadePendencias({ controller }) {
  return (
    <section className="mb-5 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-amber-200 bg-amber-50 px-5 py-4 dark:border-amber-500/30 dark:bg-amber-500/10">
        <div className="flex items-center gap-3">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-white text-amber-700 shadow-sm ring-1 ring-amber-200 dark:bg-slate-900 dark:text-amber-300 dark:ring-amber-500/30">
            <FiAlertTriangle aria-hidden="true" />
          </span>
          <div>
            <p className="m-0 font-semibold text-slate-900 dark:text-slate-100">
              Produtos removidos por validade
            </p>
            <p className="mt-0.5 text-xs text-slate-600 dark:text-slate-400">
              Revise cada item e registre a decisao.
            </p>
          </div>
          <span className="rounded-full bg-white px-2.5 py-1 text-xs font-bold text-amber-800 shadow-sm ring-1 ring-amber-200 dark:bg-slate-900 dark:text-amber-200 dark:ring-amber-500/30">
            {controller.validadePendencias.length} itens
          </span>
        </div>
        <VerificarValidadeButton controller={controller} />
      </header>
      <div className="grid gap-3 p-4 sm:p-5">
        {controller.validadePendencias.map((item) => (
          <ValidadePendenciaCard
            key={item.id}
            item={item}
            onResolver={controller.resolverValidade}
          />
        ))}
      </div>
    </section>
  );
}

function VerificarValidadeButton({ controller }) {
  return (
    <button
      type="button"
      className="inline-flex items-center justify-center gap-2 rounded-xl border border-teal-200 bg-teal-50 px-3.5 py-2 text-sm font-semibold text-teal-700 shadow-sm transition hover:border-teal-300 hover:bg-teal-100 disabled:cursor-wait disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 dark:border-teal-500/30 dark:bg-teal-500/10 dark:text-teal-200 dark:hover:bg-teal-500/20"
      disabled={controller.processandoValidade}
      onClick={() => controller.carregarValidadePendencias({ processar: true, mostrarToast: true })}
    >
      <FiRefreshCw className={controller.processandoValidade ? "animate-spin" : ""} />
      {controller.processandoValidade ? "Verificando..." : "Verificar validade agora"}
    </button>
  );
}

function ValidadePendenciaCard({ item, onResolver }) {
  return (
    <article className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-300 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-slate-600">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="m-0 font-semibold text-slate-900 dark:text-slate-100">
            {item.produto_nome || "Produto sem nome"}
          </p>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Lote {item.lote_nome || item.lote_id} - vence em{" "}
            {formatarDataValidade(item.data_validade)}
          </p>
        </div>
        <div className="sm:text-right">
          <p className="m-0 font-semibold text-slate-900 dark:text-slate-100">
            {Number(item.quantidade_bloqueada || 0).toLocaleString("pt-BR")} un.
          </p>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Custo estimado: {formatarMoeda(item.custo_total_estimado)}
          </p>
        </div>
      </div>
      <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-3 dark:border-slate-800">
        <button
          type="button"
          onClick={() => onResolver(item, "descartar")}
          className="inline-flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-200 dark:hover:bg-red-500/20"
        >
          <FiTrash2 aria-hidden="true" />
          Descartar
        </button>
        <button
          type="button"
          onClick={() => onResolver(item, "trocar")}
          className="inline-flex items-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-semibold text-indigo-700 transition hover:bg-indigo-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 dark:border-indigo-500/30 dark:bg-indigo-500/10 dark:text-indigo-200 dark:hover:bg-indigo-500/20"
        >
          <FiPackage aria-hidden="true" />
          Registrar troca
        </button>
        <button
          type="button"
          onClick={() => onResolver(item, "retornar")}
          className="inline-flex items-center gap-2 rounded-lg border border-teal-700 bg-teal-700 px-3 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600"
        >
          <FiRefreshCw aria-hidden="true" />
          Retornar ao estoque
        </button>
      </div>
    </article>
  );
}
