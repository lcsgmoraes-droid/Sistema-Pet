import { Copy, ExternalLink, Link2Off, MessageCircle, Smartphone, Store } from "lucide-react";

const STATUS_STYLE = {
  ativa: "bg-emerald-100 text-emerald-700",
  agendada: "bg-blue-100 text-blue-700",
  expirada: "bg-slate-100 text-slate-600",
  desativada: "bg-red-100 text-red-700",
};

export default function OfertaPublicacoes({ publicacoes, onDesativar, onCopiar, desativandoId }) {
  if (!publicacoes.length) return null;
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="font-black text-slate-950">Campanhas salvas</h2>
          <p className="mt-1 text-xs text-slate-500">
            Cada campanha é independente. Você pode manter várias ativas ao mesmo tempo.
          </p>
        </div>
        <span className="rounded-full bg-violet-100 px-3 py-1 text-xs font-black text-violet-700">
          {publicacoes.length} campanha(s)
        </span>
      </div>
      <div className="mt-4 space-y-3">
        {publicacoes.map((item) => {
          const link = `${window.location.origin}${item.link_path}`;
          const textoWhatsApp = encodeURIComponent(`${item.titulo}: ${link}`);
          return (
            <article
              key={item.id}
              className="flex flex-col gap-3 rounded-xl border border-slate-200 p-4 md:flex-row md:items-center md:justify-between"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="truncate font-bold text-slate-900">{item.titulo}</h3>
                  <span
                    className={`rounded-full px-2 py-1 text-[10px] font-black uppercase ${STATUS_STYLE[item.status] || STATUS_STYLE.expirada}`}
                  >
                    {item.status}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  Expira em {new Date(item.expira_em).toLocaleString("pt-BR")}
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {item.canais?.ecommerce ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-orange-50 px-2 py-1 text-[10px] font-black text-orange-700">
                      <Store size={12} /> E-commerce
                    </span>
                  ) : null}
                  {item.canais?.app ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-1 text-[10px] font-black text-blue-700">
                      <Smartphone size={12} /> Aplicativo
                    </span>
                  ) : null}
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => onCopiar(link)}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-2 text-xs font-bold"
                >
                  <Copy size={14} /> Copiar
                </button>
                <a
                  href={`https://wa.me/?text=${textoWhatsApp}`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2 text-xs font-bold text-emerald-700 no-underline"
                >
                  <MessageCircle size={14} /> WhatsApp
                </a>
                <a
                  href={item.link_path}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-2 text-xs font-bold text-slate-700 no-underline"
                >
                  <ExternalLink size={14} /> Abrir
                </a>
                {item.status !== "desativada" && item.status !== "expirada" ? (
                  <button
                    type="button"
                    disabled={desativandoId === item.id}
                    onClick={() => onDesativar(item.id)}
                    className="inline-flex items-center gap-1 rounded-lg border border-red-200 px-3 py-2 text-xs font-bold text-red-600 disabled:opacity-50"
                  >
                    <Link2Off size={14} /> Desativar
                  </button>
                ) : null}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
