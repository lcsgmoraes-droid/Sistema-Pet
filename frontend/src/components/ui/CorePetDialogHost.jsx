import { AlertTriangle, CheckCircle2, HelpCircle, Info, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { assinarCorePetDialog, resolverCorePetDialog } from "../../services/corepetDialog";

const VARIANTES = {
  danger: {
    icon: AlertTriangle,
    iconClass: "bg-red-50 text-red-600 dark:bg-red-500/15 dark:text-red-300",
    buttonClass: "bg-red-600 hover:bg-red-700 focus:ring-red-500",
  },
  warning: {
    icon: AlertTriangle,
    iconClass: "bg-amber-50 text-amber-600 dark:bg-amber-500/15 dark:text-amber-300",
    buttonClass: "bg-amber-600 hover:bg-amber-700 focus:ring-amber-500",
  },
  success: {
    icon: CheckCircle2,
    iconClass: "bg-emerald-50 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-300",
    buttonClass: "bg-emerald-600 hover:bg-emerald-700 focus:ring-emerald-500",
  },
  info: {
    icon: Info,
    iconClass: "bg-cyan-50 text-[#0f8b8d] dark:bg-cyan-500/15 dark:text-cyan-300",
    buttonClass: "bg-[#0f787a] hover:bg-[#0c6264] focus:ring-[#0f8b8d]",
  },
  question: {
    icon: HelpCircle,
    iconClass: "bg-indigo-50 text-indigo-600 dark:bg-indigo-500/15 dark:text-indigo-300",
    buttonClass: "bg-indigo-600 hover:bg-indigo-700 focus:ring-indigo-500",
  },
};

export default function CorePetDialogHost() {
  const [dialogo, setDialogo] = useState(null);
  const [valor, setValor] = useState("");
  const [erro, setErro] = useState("");
  const campoRef = useRef(null);
  const confirmarRef = useRef(null);

  useEffect(() => assinarCorePetDialog(setDialogo), []);

  useEffect(() => {
    if (!dialogo) return;
    setValor(dialogo.valorInicial || "");
    setErro("");

    const timer = window.setTimeout(() => {
      if (dialogo.tipo === "entrada") campoRef.current?.focus();
      else confirmarRef.current?.focus();
    }, 30);

    return () => window.clearTimeout(timer);
  }, [dialogo]);

  useEffect(() => {
    if (!dialogo) return;

    const aoPressionarTecla = (event) => {
      if (event.key === "Escape") {
        resolverCorePetDialog(dialogo.tipo === "entrada" ? null : false);
      }
    };

    window.addEventListener("keydown", aoPressionarTecla);
    return () => window.removeEventListener("keydown", aoPressionarTecla);
  }, [dialogo]);

  if (!dialogo) return null;

  const variante = VARIANTES[dialogo.variante] || VARIANTES.info;
  const Icone = variante.icon;

  const confirmar = () => {
    if (dialogo.tipo !== "entrada") {
      resolverCorePetDialog(true);
      return;
    }

    const valorNormalizado = valor.trim();
    if (dialogo.obrigatorio && !valorNormalizado) {
      setErro(dialogo.mensagemObrigatoria || "Preencha este campo para continuar.");
      campoRef.current?.focus();
      return;
    }

    if (dialogo.minimoCaracteres && valorNormalizado.length < dialogo.minimoCaracteres) {
      setErro(`Digite pelo menos ${dialogo.minimoCaracteres} caracteres.`);
      campoRef.current?.focus();
      return;
    }

    resolverCorePetDialog(valorNormalizado);
  };

  return (
    <div
      className="fixed inset-0 z-[120] flex items-center justify-center bg-slate-950/45 p-4 backdrop-blur-[2px]"
      data-modal-backdrop-for="corepet-dialog"
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="corepet-dialog-title"
        aria-describedby="corepet-dialog-message"
        data-modal-panel="corepet-dialog"
        className="w-full max-w-lg overflow-hidden rounded-2xl border border-white/70 bg-white shadow-2xl dark:border-slate-700 dark:bg-slate-900"
      >
        <div className="flex items-start gap-4 px-6 pb-4 pt-6">
          <div
            className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl ${variante.iconClass}`}
          >
            <Icone className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0 flex-1">
            <h2
              id="corepet-dialog-title"
              className="text-lg font-semibold text-slate-900 dark:text-slate-100"
            >
              {dialogo.titulo}
            </h2>
            <p
              id="corepet-dialog-message"
              className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-600 dark:text-slate-300"
            >
              {dialogo.mensagem}
            </p>
          </div>
          <button
            type="button"
            onClick={() => resolverCorePetDialog(dialogo.tipo === "entrada" ? null : false)}
            className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            aria-label="Fechar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {dialogo.tipo === "entrada" && (
          <div className="px-6 pb-2">
            {dialogo.rotulo && (
              <label
                htmlFor="corepet-dialog-input"
                className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-200"
              >
                {dialogo.rotulo}
              </label>
            )}
            {dialogo.multilinha ? (
              <textarea
                ref={campoRef}
                id="corepet-dialog-input"
                value={valor}
                rows={4}
                placeholder={dialogo.placeholder}
                onChange={(event) => {
                  setValor(event.target.value);
                  setErro("");
                }}
                className="w-full resize-y rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-[#0f8b8d] focus:ring-2 focus:ring-[#0f8b8d]/20 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
              />
            ) : (
              <input
                ref={campoRef}
                id="corepet-dialog-input"
                value={valor}
                placeholder={dialogo.placeholder}
                onChange={(event) => {
                  setValor(event.target.value);
                  setErro("");
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter") confirmar();
                }}
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-[#0f8b8d] focus:ring-2 focus:ring-[#0f8b8d]/20 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
              />
            )}
            {erro && (
              <p className="mt-2 text-sm font-medium text-red-600 dark:text-red-300">{erro}</p>
            )}
          </div>
        )}

        <div className="mt-4 flex flex-col-reverse gap-2 border-t border-slate-100 bg-slate-50/80 px-6 py-4 sm:flex-row sm:justify-end dark:border-slate-800 dark:bg-slate-950/40">
          <button
            type="button"
            onClick={() => resolverCorePetDialog(dialogo.tipo === "entrada" ? null : false)}
            className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            {dialogo.cancelarTexto}
          </button>
          <button
            ref={confirmarRef}
            type="button"
            onClick={confirmar}
            className={`rounded-xl px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition focus:outline-none focus:ring-2 focus:ring-offset-2 ${variante.buttonClass}`}
          >
            {dialogo.confirmarTexto}
          </button>
        </div>
      </section>
    </div>
  );
}
