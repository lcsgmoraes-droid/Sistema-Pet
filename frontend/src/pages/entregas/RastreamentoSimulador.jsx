import { LocateFixed, Play, Square } from "lucide-react";
import { useEffect, useState } from "react";

export default function RastreamentoSimulador({ rotas, simulacao, onIniciar, onParar }) {
  const [rotaId, setRotaId] = useState("");

  useEffect(() => {
    if (!rotas.some((rota) => String(rota.id) === String(rotaId))) {
      setRotaId(rotas[0]?.id ? String(rotas[0].id) : "");
    }
  }, [rotaId, rotas]);

  return (
    <section className="rounded-xl border border-violet-200 bg-violet-50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <LocateFixed size={18} className="text-violet-700" />
            <h2 className="font-bold text-violet-950">Simulador de deslocamento</h2>
            <span className="rounded-full bg-violet-700 px-2 py-0.5 text-[10px] font-black uppercase tracking-wide text-white">
              Somente DEV
            </span>
          </div>
          <p className="mt-1 max-w-3xl text-xs text-violet-800">
            Envia 12 pontos de teste pela API real. Use apenas uma rota de demonstração: a distância
            percorrida será registrada no ambiente local.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            value={rotaId}
            onChange={(event) => setRotaId(event.target.value)}
            disabled={simulacao.ativa}
            className="h-10 min-w-52 rounded-lg border border-violet-300 bg-white px-3 text-sm"
          >
            {rotas.length === 0 ? <option value="">Nenhuma rota em andamento</option> : null}
            {rotas.map((rota) => (
              <option key={rota.id} value={rota.id}>
                {rota.numero || `Rota #${rota.id}`} · {rota.entregador?.nome || "Entregador"}
              </option>
            ))}
          </select>
          {simulacao.ativa ? (
            <button
              type="button"
              onClick={onParar}
              className="inline-flex h-10 items-center gap-2 rounded-lg bg-red-600 px-4 text-sm font-bold text-white"
            >
              <Square size={15} /> Parar ({simulacao.progresso}/12)
            </button>
          ) : (
            <button
              type="button"
              onClick={() => onIniciar(rotaId)}
              disabled={!rotaId}
              className="inline-flex h-10 items-center gap-2 rounded-lg bg-violet-700 px-4 text-sm font-bold text-white disabled:opacity-45"
            >
              <Play size={16} /> Simular trajeto
            </button>
          )}
        </div>
      </div>
      {simulacao.erro ? (
        <p className="mt-3 text-xs font-semibold text-red-700">{simulacao.erro}</p>
      ) : null}
    </section>
  );
}
