import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { banhoTosaApi } from "../banhoTosaApi";
import { formatNumber, getApiErrorMessage } from "../banhoTosaUtils";

export default function BanhoTosaPacoteUsoPanel({ atendimento, onChanged }) {
  const [creditos, setCreditos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [processingId, setProcessingId] = useState(null);

  async function carregarCreditos() {
    if (!atendimento?.cliente_id) return;
    setLoading(true);
    try {
      const response = await banhoTosaApi.listarCreditosPacote({
        cliente_id: atendimento.cliente_id,
        pet_id: atendimento.pet_id,
        disponiveis_only: true,
        limit: 50,
      });
      setCreditos(Array.isArray(response.data) ? response.data : []);
    } catch {
      setCreditos([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    carregarCreditos();
  }, [atendimento?.id, atendimento?.cliente_id, atendimento?.pet_id]);

  async function consumir(credito) {
    setProcessingId(credito.id);
    try {
      await banhoTosaApi.consumirCreditoPacote(credito.id, {
        atendimento_id: atendimento.id,
        quantidade: "1",
      });
      toast.success("Credito de pacote consumido.");
      await onChanged?.();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel consumir o pacote."));
    } finally {
      setProcessingId(null);
    }
  }

  async function estornar() {
    setProcessingId(atendimento.pacote_credito_id);
    try {
      await banhoTosaApi.estornarCreditoPacote(atendimento.pacote_credito_id, {
        atendimento_id: atendimento.id,
      });
      toast.success("Consumo do pacote estornado.");
      await onChanged?.();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel estornar o pacote."));
    } finally {
      setProcessingId(null);
    }
  }

  if (atendimento?.pacote_credito_id) {
    return (
      <div className="mt-5 rounded-3xl border border-emerald-200 bg-emerald-50 p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-700">
              Pacote consumido
            </p>
            <h3 className="mt-1 font-black text-slate-900">
              {atendimento.pacote_nome || `Credito #${atendimento.pacote_credito_id}`}
            </h3>
            <p className="mt-1 text-sm font-semibold text-emerald-700">
              Saldo atual: {formatNumber(atendimento.pacote_saldo_creditos, 0)} credito(s).
            </p>
          </div>
          <button
            type="button"
            disabled={Boolean(processingId)}
            onClick={estornar}
            className="rounded-2xl border border-emerald-200 bg-white px-5 py-3 text-sm font-bold text-emerald-700 transition hover:border-emerald-300 disabled:opacity-60"
          >
            {processingId ? "Estornando..." : "Estornar consumo"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-5 rounded-3xl border border-sky-100 bg-sky-50/80 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.16em] text-sky-700">
            Pacotes disponiveis
          </p>
          <p className="mt-1 text-sm text-slate-600">
            Use um credito ativo para quitar este atendimento sem enviar ao PDV.
          </p>
        </div>
        <button type="button" onClick={carregarCreditos} className="text-xs font-bold text-sky-700">
          {loading ? "..." : "Atualizar"}
        </button>
      </div>

      <div className="mt-3 space-y-2">
        {creditos.map((credito) => (
          <div key={credito.id} className="flex flex-col gap-2 rounded-2xl bg-white p-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-black text-slate-900">{credito.pacote_nome}</p>
              <p className="text-xs font-semibold text-slate-500">
                {credito.pet_nome || "todos os pets"} | saldo {formatNumber(credito.saldo_creditos, 0)}
              </p>
            </div>
            <button
              type="button"
              disabled={processingId === credito.id}
              onClick={() => consumir(credito)}
              className="rounded-xl bg-sky-600 px-4 py-2 text-sm font-bold text-white transition hover:bg-sky-700 disabled:opacity-60"
            >
              {processingId === credito.id ? "Usando..." : "Usar credito"}
            </button>
          </div>
        ))}
        {!creditos.length && (
          <p className="rounded-2xl border border-dashed border-sky-200 bg-white/70 p-3 text-sm text-slate-500">
            Nenhum credito ativo para este tutor/pet.
          </p>
        )}
      </div>
    </div>
  );
}
