import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage } from "../banhoTosaUtils";
import BanhoTosaAtendimentoPanel from "./BanhoTosaAtendimentoPanel";
import BanhoTosaVetAlertas from "./BanhoTosaVetAlertas";

const DEFAULT_FLUXO = ["chegou", "banho", "secagem", "tosa", "pronto"];
const ETAPA_LABELS = {
  chegou: "Chegou",
  banho: "Banho",
  secagem: "Secagem",
  tosa: "Tosa",
  higiene: "Higiene",
  preparo: "Preparo",
  pronto: "Pronto",
  entregue: "Entregue",
};
const STATUS_POR_ETAPA = {
  chegou: "chegou",
  banho: "em_banho",
  secagem: "em_secagem",
  tosa: "em_tosa",
  higiene: "em_banho",
  preparo: "em_banho",
  pronto: "pronto",
  entregue: "entregue",
};
const ETAPA_POR_STATUS = {
  chegou: "chegou",
  em_banho: "banho",
  em_secagem: "secagem",
  em_tosa: "tosa",
  pronto: "pronto",
};

export default function BanhoTosaFilaView({ config, funcionarios, recursos, onChanged }) {
  const [atendimentos, setAtendimentos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [processingId, setProcessingId] = useState(null);
  const [savingFluxo, setSavingFluxo] = useState(false);
  const [tick, setTick] = useState(0);
  const [fluxoLocal, setFluxoLocal] = useState(() => normalizarFluxo(config?.fluxo_etapas));
  const [atendimentoSelecionadoId, setAtendimentoSelecionadoId] = useState(null);

  useEffect(() => {
    setFluxoLocal(normalizarFluxo(config?.fluxo_etapas));
  }, [config?.id, JSON.stringify(config?.fluxo_etapas || [])]);

  useEffect(() => {
    carregarFila();
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => setTick((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const fluxo = useMemo(() => normalizarFluxo(fluxoLocal), [fluxoLocal]);

  async function carregarFila() {
    setLoading(true);
    try {
      const response = await banhoTosaApi.listarAtendimentos({ limit: 200 });
      setAtendimentos(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel carregar a fila."));
      setAtendimentos([]);
    } finally {
      setLoading(false);
    }
  }

  async function salvarFluxo(novoFluxo) {
    setFluxoLocal(novoFluxo);
    setSavingFluxo(true);
    try {
      await banhoTosaApi.atualizarConfiguracao({ fluxo_etapas: novoFluxo });
      toast.success("Ordem do fluxo atualizada.");
      await onChanged(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel salvar a ordem."));
      setFluxoLocal(normalizarFluxo(config?.fluxo_etapas));
    } finally {
      setSavingFluxo(false);
    }
  }

  function moverFluxo(index, direction) {
    const target = index + direction;
    if (index <= 0 || index >= fluxo.length - 1 || target <= 0 || target >= fluxo.length - 1) {
      return;
    }
    const novoFluxo = [...fluxo];
    [novoFluxo[index], novoFluxo[target]] = [novoFluxo[target], novoFluxo[index]];
    salvarFluxo(novoFluxo);
  }

  async function moverEtapa(atendimento, etapa) {
    if (!etapa) return;

    setProcessingId(atendimento.id);
    try {
      await banhoTosaApi.moverEtapaAtendimento(atendimento.id, { tipo: etapa });
      await carregarFila();
      await onChanged(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel mover a etapa."));
    } finally {
      setProcessingId(null);
    }
  }

  const visiveis = atendimentos.filter(
    (item) => !["entregue", "cancelado", "no_show"].includes(item.status),
  );

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
              Fila operacional
            </p>
            <h2 className="mt-2 text-xl font-black text-slate-900">
              Check-ins em andamento
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Reordene o fluxo, mova o pet pela proxima etapa ou escolha uma etapa manualmente quando o atendimento sair do padrao.
            </p>
          </div>
          <button
            type="button"
            onClick={carregarFila}
            className="rounded-2xl border border-slate-200 px-4 py-2 text-sm font-bold text-slate-600 transition hover:border-orange-300 hover:text-orange-700"
          >
            Atualizar fila
          </button>
        </div>

        <div className="mt-5 rounded-2xl border border-orange-100 bg-orange-50/70 p-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.16em] text-orange-600">
                Ordem do fluxo
              </p>
              <p className="text-xs text-slate-500">
                Chegou e Pronto ficam nas pontas; as etapas operacionais podem trocar de posicao.
              </p>
            </div>
            {savingFluxo && <span className="text-xs font-bold text-orange-700">Salvando...</span>}
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {fluxo.map((etapa, index) => (
              <div
                key={etapa}
                className="flex items-center gap-2 rounded-2xl border border-orange-200 bg-white px-3 py-2 shadow-sm"
              >
                <span className="text-sm font-black text-slate-900">
                  {index + 1}. {labelEtapa(etapa)}
                </span>
                {index > 0 && index < fluxo.length - 1 && (
                  <div className="flex gap-1">
                    <button
                      type="button"
                      onClick={() => moverFluxo(index, -1)}
                      disabled={savingFluxo}
                      className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-bold text-slate-600 hover:bg-slate-200 disabled:opacity-50"
                    >
                      Subir
                    </button>
                    <button
                      type="button"
                      onClick={() => moverFluxo(index, 1)}
                      disabled={savingFluxo}
                      className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-bold text-slate-600 hover:bg-slate-200 disabled:opacity-50"
                    >
                      Descer
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {loading ? (
        <div className="rounded-3xl border border-white/80 bg-white p-10 text-center text-sm font-semibold text-slate-500 shadow-sm">
          Carregando fila...
        </div>
      ) : (
        <div className="overflow-x-auto pb-2">
          <div
            className="grid min-w-[980px] gap-4"
            style={{ gridTemplateColumns: `repeat(${fluxo.length}, minmax(180px, 1fr))` }}
          >
            {fluxo.map((etapa) => {
              const itens = visiveis.filter((item) => etapaAtual(item) === etapa);
              return (
                <div
                  key={etapa}
                  className="min-h-[220px] rounded-3xl border border-white/80 bg-white p-4 shadow-sm"
                >
                  <div className="flex items-center justify-between">
                    <h3 className="font-black text-slate-900">{labelEtapa(etapa)}</h3>
                    <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-500">
                      {itens.length}
                    </span>
                  </div>

                  <div className="mt-4 space-y-3">
                    {itens.map((atendimento) => (
                      <AtendimentoCard
                        key={atendimento.id}
                        atendimento={atendimento}
                        fluxo={fluxo}
                        processing={processingId === atendimento.id}
                        tick={tick}
                        onMover={moverEtapa}
                        onSelect={setAtendimentoSelecionadoId}
                      />
                    ))}
                    {itens.length === 0 && (
                      <div className="rounded-2xl border border-dashed border-slate-200 p-5 text-center text-sm text-slate-400">
                        Sem pets nesta etapa.
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <BanhoTosaAtendimentoPanel
        atendimentoId={atendimentoSelecionadoId}
        funcionarios={funcionarios}
        recursos={recursos}
        onChanged={async (silent) => {
          await carregarFila();
          await onChanged(silent);
        }}
      />
    </div>
  );
}

function AtendimentoCard({ atendimento, fluxo, processing, tick, onMover, onSelect }) {
  const [openSelector, setOpenSelector] = useState(false);
  const atual = etapaAtual(atendimento);
  const proxima = proximaEtapa(atendimento, fluxo);
  const timer = timerEtapa(atendimento, tick);

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-black text-slate-900">
            {atendimento.pet_nome || `Pet #${atendimento.pet_id}`}
          </p>
          <p className="text-sm text-slate-500">
            Tutor: {atendimento.cliente_nome || `#${atendimento.cliente_id}`}
          </p>
        </div>
        <span className="rounded-full bg-white px-2 py-1 text-[11px] font-black uppercase tracking-[0.12em] text-slate-500">
          {labelEtapa(atual)}
        </span>
      </div>

      {atendimento.porte_snapshot && (
        <p className="mt-1 text-xs font-bold uppercase tracking-[0.12em] text-orange-500">
          {atendimento.porte_snapshot}
          {atendimento.pelagem_snapshot ? ` | ${atendimento.pelagem_snapshot}` : ""}
        </p>
      )}

      {timer && (
        <div
          className={`mt-3 rounded-2xl px-3 py-2 text-sm font-black ${
            timer.remaining < 0
              ? "bg-red-50 text-red-700"
              : timer.remaining <= 300
                ? "bg-amber-50 text-amber-700"
                : "bg-emerald-50 text-emerald-700"
          }`}
        >
          {timer.remaining < 0 ? "Atraso " : "Tempo restante "}
          {formatTempo(timer.remaining)}
          <span className="ml-2 text-xs font-semibold opacity-75">
            previsto {timer.previstoMin} min
          </span>
        </div>
      )}

      <BanhoTosaVetAlertas
        compact
        perfil={atendimento.perfil_comportamental_snapshot}
        restricoes={atendimento.restricoes_veterinarias_snapshot}
      />

      {proxima && (
        <button
          type="button"
          disabled={processing}
          onClick={() => onMover(atendimento, proxima)}
          className="mt-4 w-full rounded-xl bg-slate-900 px-3 py-2 text-sm font-bold text-white transition hover:bg-slate-700 disabled:opacity-60"
        >
          {processing ? "Atualizando..." : acaoProximaLabel(proxima)}
        </button>
      )}

      <div className="relative">
        <button
          type="button"
          onClick={() => setOpenSelector((value) => !value)}
          className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-bold text-slate-600 transition hover:border-orange-300 hover:text-orange-700"
        >
          Selecionar etapa
        </button>
        {openSelector && (
          <div className="absolute left-0 right-0 z-10 mt-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-xl">
            {fluxo.map((etapa) => (
              <button
                key={etapa}
                type="button"
                disabled={processing || etapa === atual}
                onClick={() => {
                  setOpenSelector(false);
                  onMover(atendimento, etapa);
                }}
                className="block w-full rounded-xl px-3 py-2 text-left text-sm font-bold text-slate-700 hover:bg-orange-50 disabled:cursor-not-allowed disabled:text-slate-300"
              >
                {labelEtapa(etapa)}
              </button>
            ))}
          </div>
        )}
      </div>

      <button
        type="button"
        onClick={() => onSelect(atendimento.id)}
        className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-bold text-slate-600 transition hover:border-orange-300 hover:text-orange-700"
      >
        Etapas e recursos
      </button>
    </div>
  );
}

function normalizarFluxo(valor) {
  const etapas = [];
  (Array.isArray(valor) && valor.length ? valor : DEFAULT_FLUXO).forEach((etapa) => {
    const codigo = String(etapa || "").trim().toLowerCase();
    if (ETAPA_LABELS[codigo] && !etapas.includes(codigo)) {
      etapas.push(codigo);
    }
  });
  const semPontas = etapas.filter((item) => !["chegou", "pronto", "entregue"].includes(item));
  return ["chegou", ...semPontas, "pronto"];
}

function labelEtapa(etapa) {
  return ETAPA_LABELS[etapa] || String(etapa || "").replace("_", " ");
}

function acaoProximaLabel(etapa) {
  if (etapa === "entregue") return "Entregar";
  if (etapa === "pronto") return "Marcar pronto";
  return `Ir para ${labelEtapa(etapa).toLowerCase()}`;
}

function etapaAtual(atendimento) {
  const aberta = etapaAberta(atendimento);
  if (aberta?.tipo) return aberta.tipo;
  return atendimento.etapa_atual_codigo || ETAPA_POR_STATUS[atendimento.status] || atendimento.status;
}

function etapaAberta(atendimento) {
  const abertas = (atendimento.etapas || [])
    .filter((etapa) => etapa.inicio_em && !etapa.fim_em)
    .sort((a, b) => new Date(b.inicio_em).getTime() - new Date(a.inicio_em).getTime());
  return abertas[0] || null;
}

function proximaEtapa(atendimento, fluxo) {
  if (atendimento.proxima_etapa_codigo) {
    return atendimento.proxima_etapa_codigo;
  }
  if (atendimento.status === "pronto") {
    return "entregue";
  }
  const atual = etapaAtual(atendimento);
  const index = fluxo.indexOf(atual);
  if (index >= 0 && index + 1 < fluxo.length) {
    return fluxo[index + 1];
  }
  return STATUS_POR_ETAPA[atual] === "pronto" ? "entregue" : null;
}

function timerEtapa(atendimento, tick) {
  void tick;
  const aberta = etapaAberta(atendimento);
  const previstoMin = Number(aberta?.tempo_previsto_minutos || atendimento.tempo_previsto_minutos || 0);
  if (!aberta?.inicio_em || !previstoMin) return null;
  const inicioMs = new Date(aberta.inicio_em).getTime();
  if (!Number.isFinite(inicioMs)) return null;
  const decorrido = Math.max(0, Math.floor((Date.now() - inicioMs) / 1000));
  return {
    previstoMin,
    decorrido,
    remaining: previstoMin * 60 - decorrido,
  };
}

function formatTempo(seconds) {
  const abs = Math.abs(Number(seconds || 0));
  const minutes = Math.floor(abs / 60);
  const rest = abs % 60;
  const prefix = Number(seconds || 0) < 0 ? "-" : "";
  return `${prefix}${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
}
