import { FiCheckCircle } from "react-icons/fi";
import { formatarDataHora } from "./lembretesFormatters";

export default function LembretesBlingAutocadastros({ autocadastrosBling, onAbrirProduto }) {
  if (autocadastrosBling.total <= 0) return null;

  return (
    <section className="mb-5 overflow-hidden rounded-2xl border border-emerald-200 bg-white shadow-sm dark:border-emerald-500/30 dark:bg-slate-900">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-emerald-200 bg-emerald-50 px-5 py-4 dark:border-emerald-500/30 dark:bg-emerald-500/10">
        <div className="flex items-center gap-3">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-white text-emerald-700 shadow-sm ring-1 ring-emerald-200 dark:bg-slate-900 dark:text-emerald-300 dark:ring-emerald-500/30">
            <FiCheckCircle aria-hidden="true" />
          </span>
          <div>
            <h2 className="m-0 text-base font-semibold text-slate-900 dark:text-slate-100">
              Auto cadastro Bling
            </h2>
            <p className="mt-0.5 text-xs text-slate-600 dark:text-slate-400">Ultimas 24 horas</p>
          </div>
        </div>
        <span className="rounded-full bg-white px-2.5 py-1 text-xs font-bold text-emerald-800 ring-1 ring-inset ring-emerald-200 dark:bg-slate-900 dark:text-emerald-200 dark:ring-emerald-500/30">
          {autocadastrosBling.total} itens
        </span>
      </header>
      <div className="p-4 sm:p-5">
        <p className="mb-3 text-sm leading-5 text-slate-600 dark:text-slate-400">
          O sistema identificou SKU sem cadastro, criou o produto e seguiu com a baixa
          automaticamente. Este aviso desaparece apos 1 dia.
        </p>
        <div className="grid gap-2">
          {autocadastrosBling.items.slice(0, 8).map((item) => (
            <button
              key={item.produto_id}
              type="button"
              className="flex w-full flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-left text-sm transition hover:border-emerald-300 hover:bg-emerald-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-emerald-500/40 dark:hover:bg-emerald-500/10"
              onClick={() => onAbrirProduto(item)}
            >
              <span className="font-medium text-slate-800 dark:text-slate-200">
                {item.codigo} - {item.nome}
              </span>
              <span className="text-xs text-slate-500 dark:text-slate-400">
                {formatarDataHora(item.created_at)}
              </span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
