import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage } from "../banhoTosaUtils";
import BanhoTosaAtendimentoPanel from "./BanhoTosaAtendimentoPanel";
import BanhoTosaVetAlertas from "./BanhoTosaVetAlertas";

const statusColumns = [
  { value: "chegou", label: "Chegou" },
  { value: "em_banho", label: "Banho" },
  { value: "em_secagem", label: "Secagem" },
  { value: "em_tosa", label: "Tosa" },
  { value: "pronto", label: "Pronto" },
];

const nextStatus = {
  chegou: "em_banho",
  em_banho: "em_secagem",
  em_secagem: "em_tosa",
  em_tosa: "pronto",
  pronto: "entregue",
};

const nextLabel = {
  em_banho: "Iniciar banho",
  em_secagem: "Ir para secagem",
  em_tosa: "Ir para tosa",
  pronto: "Marcar pronto",
  entregue: "Entregar",
};

export default function BanhoTosaFilaView({ funcionarios, recursos, onChanged }) {
  const [atendimentos, setAtendimentos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [processingId, setProcessingId] = useState(null);
  const [atendimentoSelecionadoId, setAtendimentoSelecionadoId] = useState(null);

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

  useEffect(() => {
    carregarFila();
  }, []);

  async function avancar(atendimento) {
    const novoStatus = nextStatus[atendimento.status];
    if (!novoStatus) return;

    setProcessingId(atendimento.id);
    try {
      await banhoTosaApi.atualizarStatusAtendimento(atendimento.id, {
        status: novoStatus,
      });
      await carregarFila();
      await onChanged(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel atualizar status."));
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
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
              Fila operacional
            </p>
            <h2 className="mt-2 text-xl font-black text-slate-900">
              Check-ins em andamento
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Mova o pet pelas etapas para alimentar tempo real e custo depois.
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
      </div>

      {loading ? (
        <div className="rounded-3xl border border-white/80 bg-white p-10 text-center text-sm font-semibold text-slate-500 shadow-sm">
          Carregando fila...
        </div>
      ) : (
        <div className="grid gap-4 xl:grid-cols-5">
          {statusColumns.map((column) => {
            const itens = visiveis.filter((item) => item.status === column.value);
            return (
              <div
                key={column.value}
                className="min-h-[220px] rounded-3xl border border-white/80 bg-white p-4 shadow-sm"
              >
                <div className="flex items-center justify-between">
                  <h3 className="font-black text-slate-900">{column.label}</h3>
                  <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-500">
                    {itens.length}
                  </span>
                </div>

                <div className="mt-4 space-y-3">
                  {itens.map((atendimento) => (
                    <AtendimentoCard
                      key={atendimento.id}
                      atendimento={atendimento}
                      processing={processingId === atendimento.id}
                      onAvancar={avancar}
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

function AtendimentoCard({ atendimento, processing, onAvancar, onSelect }) {
  const proximo = nextStatus[atendimento.status];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="font-black text-slate-900">
        {atendimento.pet_nome || `Pet #${atendimento.pet_id}`}
      </p>
      <p className="text-sm text-slate-500">
        Tutor: {atendimento.cliente_nome || `#${atendimento.cliente_id}`}
      </p>
      {atendimento.porte_snapshot && (
        <p className="mt-1 text-xs font-bold uppercase tracking-[0.12em] text-orange-500">
          {atendimento.porte_snapshot}
        </p>
      )}
      <BanhoTosaVetAlertas
        compact
        perfil={atendimento.perfil_comportamental_snapshot}
        restricoes={atendimento.restricoes_veterinarias_snapshot}
      />

      {proximo && (
        <button
          type="button"
          disabled={processing}
          onClick={() => onAvancar(atendimento)}
          className="mt-4 w-full rounded-xl bg-slate-900 px-3 py-2 text-sm font-bold text-white transition hover:bg-slate-700 disabled:opacity-60"
        >
          {processing ? "Atualizando..." : nextLabel[proximo]}
        </button>
      )}
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
