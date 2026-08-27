import { ExternalLink, MapPin } from "lucide-react";

import { getUltimaParadaPendente } from "./rotasEntregaUtils";
import { formatarIdadeSinal, obterEstadoSinal } from "./rastreamentoAoVivoUtils";

export default function RastreamentoLista({ rotas, rotaSelecionadaId, onSelecionar }) {
  if (rotas.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center">
        <p className="font-bold text-slate-800">Nenhuma entrega em andamento</p>
        <p className="mt-1 text-sm text-slate-500">
          As motos aparecerão quando uma rota for iniciada.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {rotas.map((rota) => {
        const estado = obterEstadoSinal(rota);
        const selecionada = String(rota.id) === String(rotaSelecionadaId);
        const proximaParada = getUltimaParadaPendente(rota);
        const urlPublica = rota.token_rastreio
          ? `/rastreio/${encodeURIComponent(rota.token_rastreio)}`
          : "";

        return (
          <article
            key={rota.id}
            className={`w-full rounded-xl border bg-white text-left shadow-sm transition ${
              selecionada
                ? "border-teal-500 ring-2 ring-teal-100"
                : "border-slate-200 hover:border-slate-300"
            }`}
          >
            <button
              type="button"
              onClick={() => onSelecionar(rota.id)}
              className="w-full p-4 text-left"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate font-bold text-slate-900">
                    🛵 {rota.entregador?.nome || "Entregador não informado"}
                  </p>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {rota.numero || `Rota #${rota.id}`} · {rota.paradas?.length || 0} parada(s)
                  </p>
                </div>
                <span
                  className="shrink-0 rounded-full px-2.5 py-1 text-xs font-bold text-white"
                  style={{ backgroundColor: estado.cor }}
                >
                  {estado.label}
                </span>
              </div>

              <div className="mt-3 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
                <div className="flex items-center gap-2">
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: estado.cor }}
                  />
                  Último sinal {formatarIdadeSinal(estado)}
                </div>
                <div className="mt-2 flex items-start gap-2">
                  <MapPin size={14} className="mt-0.5 shrink-0 text-slate-400" />
                  <span>Próxima entrega: {proximaParada?.endereco || "Não informada"}</span>
                </div>
              </div>
            </button>

            {urlPublica ? (
              <a
                href={urlPublica}
                target="_blank"
                rel="noreferrer"
                className="mx-4 mb-4 inline-flex items-center gap-1.5 text-xs font-bold text-teal-700 underline"
              >
                <ExternalLink size={14} /> Abrir visão do cliente
              </a>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}
