import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { ArrowRight, GripVertical, RefreshCw, Route } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
import Panel from "../../../components/ui/Panel";
import PetAvatar from "../../../components/ui/PetAvatar";
import StatusBadge from "../../../components/ui/StatusBadge";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage } from "../banhoTosaUtils";
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

export default function BanhoTosaFilaView({ config, onChanged }) {
  const [atendimentos, setAtendimentos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [processingId, setProcessingId] = useState(null);
  const [savingFluxo, setSavingFluxo] = useState(false);
  const [draggedFluxoIndex, setDraggedFluxoIndex] = useState(null);
  const [draggedAtendimentoId, setDraggedAtendimentoId] = useState(null);
  const [fluxoLocal, setFluxoLocal] = useState(() => normalizarFluxo(config?.fluxo_etapas));

  useEffect(() => {
    setFluxoLocal(normalizarFluxo(config?.fluxo_etapas));
  }, [config?.id, JSON.stringify(config?.fluxo_etapas || [])]);

  useEffect(() => {
    carregarFila();
  }, []);

  const fluxo = useMemo(() => normalizarFluxo(fluxoLocal), [fluxoLocal]);
  const visiveis = useMemo(
    () => atendimentos.filter((item) => !["entregue", "cancelado", "no_show"].includes(item.status)),
    [atendimentos],
  );

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

  function reordenarFluxo(origem, destino) {
    if (!podeArrastarEtapa(origem, fluxoLocal.length) || !podeArrastarEtapa(destino, fluxoLocal.length) || origem === destino) return;
    const novoFluxo = [...fluxo];
    const [etapa] = novoFluxo.splice(origem, 1);
    novoFluxo.splice(destino, 0, etapa);
    salvarFluxo(novoFluxo);
  }

  async function moverEtapa(atendimento, etapa, options = {}) {
    if (!etapa || processingId) return;

    setProcessingId(atendimento.id);
    try {
      await banhoTosaApi.moverEtapaAtendimento(atendimento.id, {
        tipo: etapa,
        iniciar_timer: false,
        resetar_fluxo: Boolean(options.resetarFluxo),
      });

      await carregarFila();
      await onChanged(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel mover a etapa."));
    } finally {
      setProcessingId(null);
      setDraggedAtendimentoId(null);
    }
  }

  function onDropAtendimento(event, etapaDestino) {
    event.preventDefault();
    const atendimentoId = event.dataTransfer.getData("text/plain") || draggedAtendimentoId;
    const atendimento = visiveis.find((item) => String(item.id) === String(atendimentoId));
    if (!atendimento || etapaAtual(atendimento) === etapaDestino) return;
    moverEtapa(atendimento, etapaDestino);
  }

  return (
    <div className="space-y-4">
      <Panel
        actions={
          <ActionButton icon={RefreshCw} intent="neutral" onClick={carregarFila} tone="soft">
            Atualizar fila
          </ActionButton>
        }
        subtitle="Arraste os pets entre etapas ou use os comandos do card."
        title="Fila do dia"
      >
        <FluxoDraggable
          draggedIndex={draggedFluxoIndex}
          fluxo={fluxo}
          saving={savingFluxo}
          onDragEnd={() => setDraggedFluxoIndex(null)}
          onDragStart={setDraggedFluxoIndex}
          onDrop={reordenarFluxo}
        />
      </Panel>

      {loading ? (
        <Panel className="p-8 text-center text-sm font-medium text-slate-500">
          Carregando fila...
        </Panel>
      ) : (
        <div className="overflow-x-auto pb-2">
          <div
            className="grid min-w-[980px] gap-3"
            style={{ gridTemplateColumns: `repeat(${fluxo.length}, minmax(190px, 1fr))` }}
          >
            {fluxo.map((etapa) => {
              const itens = visiveis.filter((item) => etapaAtual(item) === etapa);
              const isDropTarget = Boolean(draggedAtendimentoId);
              return (
                <section
                  key={etapa}
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={(event) => onDropAtendimento(event, etapa)}
                  className={[
                    "min-h-[280px] rounded-lg border border-slate-200 bg-white p-3 shadow-sm transition",
                    isDropTarget ? "ring-1 ring-blue-100" : "",
                  ].join(" ")}
                >
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-slate-900">{labelEtapa(etapa)}</h3>
                    <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-500">
                      {itens.length}
                    </span>
                  </div>

                  <div className="mt-3 space-y-2">
                    {itens.map((atendimento) => (
                      <AtendimentoCard
                        key={atendimento.id}
                        atendimento={atendimento}
                        fluxo={fluxo}
                        processing={processingId === atendimento.id}
                        onDragEnd={() => setDraggedAtendimentoId(null)}
                        onDragStart={(event) => {
                          setDraggedAtendimentoId(atendimento.id);
                          event.dataTransfer.effectAllowed = "move";
                          event.dataTransfer.setData("text/plain", String(atendimento.id));
                        }}
                        onMover={moverEtapa}
                      />
                    ))}
                    {itens.length === 0 && (
                      <div className="rounded-lg border border-dashed border-slate-200 p-4 text-center text-sm text-slate-400">
                        Sem pets nesta etapa.
                      </div>
                    )}
                  </div>
                </section>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function FluxoDraggable({
  draggedIndex,
  fluxo,
  saving,
  onDragEnd,
  onDragStart,
  onDrop,
}) {
  return (
    <div className="rounded-lg border border-blue-100 bg-blue-50/60 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">
            Ordem operacional
          </p>
          <p className="text-xs text-slate-500">
            Arraste as etapas do meio para ajustar a sequencia. Chegou e Pronto ficam fixos.
          </p>
        </div>
        {saving && <span className="text-xs font-semibold text-blue-700">Salvando...</span>}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {fluxo.map((etapa, index) => {
          const draggable = podeArrastarEtapa(index, fluxo.length);
          return (
            <button
              key={etapa}
              type="button"
              draggable={draggable}
              onDragStart={() => draggable && onDragStart(index)}
              onDragOver={(event) => draggable && event.preventDefault()}
              onDrop={() => onDrop(draggedIndex, index)}
              onDragEnd={onDragEnd}
              className={[
                "inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-semibold transition",
                draggable
                  ? "cursor-grab border-blue-200 bg-white text-slate-800 hover:border-blue-300"
                  : "cursor-default border-slate-200 bg-slate-50 text-slate-500",
                draggedIndex === index ? "opacity-60" : "",
              ].join(" ")}
            >
              {draggable && <GripVertical size={14} aria-hidden="true" />}
              <span>{index + 1}. {labelEtapa(etapa)}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function AtendimentoCard({
  atendimento,
  fluxo,
  processing,
  onDragEnd,
  onDragStart,
  onMover,
}) {
  const [openSelector, setOpenSelector] = useState(false);
  const atual = etapaAtual(atendimento);
  const proxima = proximaEtapa(atendimento, fluxo);
  const etapasDestino = [...fluxo, "entregue"].filter((etapa, index, lista) => lista.indexOf(etapa) === index);

  return (
    <article
      draggable={!processing}
      onDragEnd={onDragEnd}
      onDragStart={onDragStart}
      className="rounded-lg border border-slate-200 bg-slate-50 p-3 shadow-sm transition hover:border-blue-200 hover:bg-white"
    >
      <div className="flex gap-3">
        <PetAvatar
          alt={atendimento.pet_nome || "Pet"}
          name={atendimento.pet_nome}
          size="lg"
          url={atendimento.pet_foto_url}
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-slate-900">
                {atendimento.pet_nome || `Pet #${atendimento.pet_id}`}
              </p>
              <p className="truncate text-xs text-slate-500">
                Tutor: {atendimento.cliente_nome || `#${atendimento.cliente_id}`}
              </p>
            </div>
            <GripVertical size={16} className="shrink-0 text-slate-300" aria-hidden="true" />
          </div>

          <div className="mt-2 flex flex-wrap gap-1.5">
            <StatusBadge status={atendimento.status} />
            {atendimento.porte_snapshot && (
              <span className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-medium text-slate-600">
                {atendimento.porte_snapshot}
                {atendimento.pelagem_snapshot ? ` / ${atendimento.pelagem_snapshot}` : ""}
              </span>
            )}
          </div>
        </div>
      </div>

      <BanhoTosaVetAlertas
        compact
        perfil={atendimento.perfil_comportamental_snapshot}
        restricoes={atendimento.restricoes_veterinarias_snapshot}
      />

      <div className="mt-3 grid gap-2">
        <ActionButton
          className="w-full"
          disabled={!proxima || processing}
          icon={ArrowRight}
          intent={proxima === "entregue" ? "create" : "edit"}
          loading={processing}
          onClick={() => proxima && onMover(atendimento, proxima)}
          size="sm"
        >
          Avancar
        </ActionButton>

        <div className="relative">
          <ActionButton
            className="w-full"
            icon={Route}
            intent="neutral"
            onClick={() => setOpenSelector((value) => !value)}
            size="sm"
            tone="soft"
          >
            Ir para etapa
          </ActionButton>

          {openSelector && (
            <div className="absolute left-0 right-0 z-20 mt-2 rounded-lg border border-slate-200 bg-white p-1.5 shadow-xl">
              {etapasDestino.map((etapa) => (
                <button
                  key={etapa}
                  type="button"
                  disabled={processing || etapa === atual}
                  onClick={() => {
                    setOpenSelector(false);
                    onMover(atendimento, etapa);
                  }}
                  className="block w-full rounded-md px-3 py-2 text-left text-sm font-medium text-slate-700 transition hover:bg-blue-50 disabled:cursor-not-allowed disabled:text-slate-300"
                >
                  {labelEtapa(etapa)}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </article>
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

function podeArrastarEtapa(index, total) {
  return index > 0 && index < total - 1;
}

function labelEtapa(etapa) {
  return ETAPA_LABELS[etapa] || String(etapa || "").replace("_", " ");
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
