import { Headphones, Sparkles } from "lucide-react";

export default function LaunchOfferBanner({ dark = false }) {
  return (
    <aside
      className={`rounded-2xl border p-4 sm:flex sm:items-center sm:justify-between sm:gap-6 ${
        dark
          ? "border-amber-300/30 bg-amber-300/10 text-white"
          : "border-amber-200 bg-amber-50 text-slate-950"
      }`}
    >
      <div className="flex items-start gap-3">
        <span
          className={`flex h-10 w-10 flex-none items-center justify-center rounded-xl ${
            dark ? "bg-amber-300 text-slate-950" : "bg-amber-200 text-amber-900"
          }`}
        >
          <Sparkles className="h-5 w-5" />
        </span>
        <div>
          <p
            className={`text-xs font-black uppercase tracking-[0.14em] ${
              dark ? "text-amber-200" : "text-amber-800"
            }`}
          >
            Condição de lançamento · 20 primeiras empresas
          </p>
          <p className="mt-1 font-extrabold">
            30 dias com acesso completo ao CorePet, independentemente do plano escolhido.
          </p>
        </div>
      </div>
      <p
        className={`mt-3 flex items-center gap-2 text-sm font-semibold sm:mt-0 sm:max-w-xs ${
          dark ? "text-slate-300" : "text-slate-600"
        }`}
      >
        <Headphones className="h-4 w-4 flex-none" />
        Implantação e acompanhamento humano incluídos durante o lançamento.
      </p>
    </aside>
  );
}
