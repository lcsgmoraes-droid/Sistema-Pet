import { Loader2 } from "lucide-react";
import { forwardRef } from "react";

// Todas as variantes são "chapadas" (cor sólida + texto branco) — nunca bg suave/translúcido (bg-*-50, bg-*/10 etc.).
const VARIANTES = {
  neutro:
    "border-slate-900 bg-slate-900 text-white hover:bg-slate-700 dark:border-slate-600 dark:bg-slate-700 dark:hover:bg-slate-600",
  sucesso:
    "border-emerald-700 bg-emerald-700 text-white hover:bg-emerald-800 dark:border-emerald-700 dark:bg-emerald-700 dark:hover:bg-emerald-800",
  perigo:
    "border-red-600 bg-red-600 text-white hover:bg-red-700 dark:border-red-700 dark:bg-red-700 dark:hover:bg-red-800",
  informativo:
    "border-blue-700 bg-blue-700 text-white hover:bg-blue-800 dark:border-blue-700 dark:bg-blue-700 dark:hover:bg-blue-800",
  atencao:
    "border-amber-700 bg-amber-700 text-white hover:bg-amber-800 dark:border-amber-700 dark:bg-amber-700 dark:hover:bg-amber-800",
};

// 3 tamanhos fixos (pequeno/normal/grande) — não é uma escala livre, é um enum fechado.
const TAMANHOS = {
  pequeno: { botao: "h-8 gap-1 px-3 text-xs", icone: "h-3.5 w-3.5" },
  normal: { botao: "h-9 gap-1.5 px-3.5 text-sm", icone: "h-4 w-4" },
  grande: { botao: "h-11 gap-2 px-5 text-base", icone: "h-5 w-5" },
};

// Casca interna dos botões v2 — telas usam BotaoSalva/BotaoCancelar/BotaoExcluir/BotaoAjuda/BotaoInteracao, não este diretamente.
const BotaoBase = forwardRef(function BotaoBase(
  {
    children,
    disabled = false,
    icon: Icone,
    larguraTotal = false,
    loading = false,
    onClick,
    tamanho = "normal",
    type = "button",
    variante = "neutro",
    ...rest
  },
  ref,
) {
  const desabilitado = disabled || loading;
  const medida = TAMANHOS[tamanho] || TAMANHOS.normal;

  return (
    <button
      {...rest}
      ref={ref}
      type={type}
      disabled={desabilitado}
      onClick={onClick}
      className={[
        "items-center justify-center whitespace-nowrap rounded-lg border font-medium transition-colors",
        larguraTotal ? "flex w-full" : "inline-flex",
        "disabled:cursor-not-allowed disabled:border-gray-200 disabled:bg-gray-100 disabled:text-gray-500",
        "dark:disabled:border-slate-700 dark:disabled:bg-slate-800 dark:disabled:text-slate-500",
        medida.botao,
        VARIANTES[variante] || VARIANTES.neutro,
      ].join(" ")}
    >
      {loading ? (
        <Loader2 className={`${medida.icone} motion-safe:animate-spin`} aria-hidden="true" />
      ) : Icone ? (
        <Icone className={medida.icone} aria-hidden="true" />
      ) : null}
      {children}
    </button>
  );
});

export default BotaoBase;
