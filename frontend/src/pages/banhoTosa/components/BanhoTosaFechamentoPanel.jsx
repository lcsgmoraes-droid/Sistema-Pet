import { useState } from "react";
import toast from "react-hot-toast";
import { banhoTosaApi } from "../banhoTosaApi";
import { formatCurrency, getApiErrorMessage } from "../banhoTosaUtils";

export default function BanhoTosaFechamentoPanel({ atendimento, onChanged }) {
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [canceling, setCanceling] = useState(false);

  async function gerarVenda() {
    setSaving(true);
    try {
      const response = await banhoTosaApi.gerarVendaAtendimento(atendimento.id);
      const venda = response.data;
      toast.success(venda.mensagem || "Venda gerada para cobranca.");
      await onChanged?.();
      abrirPdv(venda.pdv_url);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel gerar venda."));
    } finally {
      setSaving(false);
    }
  }

  async function sincronizar() {
    setSyncing(true);
    try {
      const response = await banhoTosaApi.sincronizarFechamentoAtendimento(atendimento.id);
      toast.success(response.data?.sincronizado ? "Fechamento sincronizado." : "Fechamento conferido.");
      await onChanged?.();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel sincronizar fechamento."));
    } finally {
      setSyncing(false);
    }
  }

  async function cancelarProcesso() {
    const motivo = window.prompt(
      `Informe o motivo para cancelar o atendimento #${atendimento.id} e todo o processo financeiro vinculado:`,
      "Lancado por engano",
    );
    if (motivo === null) return;
    if (!motivo.trim()) {
      toast.error("Informe um motivo para cancelar.");
      return;
    }

    const confirmar = window.confirm(
      "Confirma o cancelamento do atendimento? Se existir venda/recebimento vinculado, o sistema tambem vai cancelar/estornar esse processo.",
    );
    if (!confirmar) return;

    setCanceling(true);
    try {
      const response = await banhoTosaApi.cancelarProcessoAtendimento(atendimento.id, {
        motivo: motivo.trim(),
      });
      toast.success(response.data?.mensagem || "Processo cancelado.");
      await onChanged?.();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel cancelar o processo."));
    } finally {
      setCanceling(false);
    }
  }

  const temVenda = Boolean(atendimento?.venda_id);
  const quitadoPorPacote = Boolean(atendimento?.pacote_credito_id);
  const alertas = atendimento?.fechamento_alertas || [];

  if (quitadoPorPacote) {
    return (
      <div className="mt-5 rounded-3xl border border-emerald-200 bg-emerald-50 p-4">
        <p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-700">
          Fechamento
        </p>
        <h3 className="mt-1 font-black text-slate-900">Quitado por pacote</h3>
        <p className="mt-1 text-sm font-semibold text-emerald-700">
          Este atendimento consumiu credito de {atendimento.pacote_nome || "pacote"} e nao deve gerar venda avulsa no PDV.
        </p>
        <button
          type="button"
          disabled={canceling}
          onClick={cancelarProcesso}
          className="mt-4 rounded-2xl border border-red-200 bg-white px-5 py-3 text-sm font-bold text-red-700 transition hover:border-red-300 hover:bg-red-50 disabled:opacity-60"
        >
          {canceling ? "Cancelando..." : "Cancelar processo"}
        </button>
      </div>
    );
  }

  return (
    <div className="mt-5 rounded-3xl border border-amber-100 bg-amber-50/80 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.16em] text-amber-600">
            Fechamento
          </p>
          <h3 className="mt-1 font-black text-slate-900">
            {temVenda ? `Venda ${atendimento.venda_numero || `#${atendimento.venda_id}`}` : "Enviar para cobranca no PDV"}
          </h3>
          <p className="mt-1 text-sm text-slate-600">
            {temVenda
              ? `${atendimento.venda_status || "aberta"} | ${atendimento.venda_status_pagamento || "pendente"} | ${formatCurrency(atendimento.venda_total || 0)}`
              : "Gera uma venda em aberto com os servicos do atendimento, mantendo o pagamento no fluxo normal do caixa."}
          </p>
          {temVenda && (
            <p className="mt-1 text-xs font-bold text-slate-500">
              Pago {formatCurrency(atendimento.venda_total_pago || 0)} | Restante {formatCurrency(atendimento.venda_valor_restante || 0)}
              {atendimento.conta_receber_id ? ` | Conta #${atendimento.conta_receber_id}` : ""}
            </p>
          )}
        </div>
        {temVenda ? (
          <div className="flex flex-col gap-2 sm:flex-row">
            <button
              type="button"
              disabled={syncing}
              onClick={sincronizar}
              className="rounded-2xl border border-amber-200 bg-white px-5 py-3 text-sm font-bold text-amber-700 transition hover:border-amber-300 disabled:opacity-60"
            >
              {syncing ? "Conferindo..." : "Sincronizar"}
            </button>
            <button
              type="button"
              onClick={() => abrirPdv(atendimento.pdv_url)}
              className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-bold text-white transition hover:bg-slate-700"
            >
              Abrir no PDV
            </button>
            <button
              type="button"
              disabled={canceling}
              onClick={cancelarProcesso}
              className="rounded-2xl border border-red-200 bg-white px-5 py-3 text-sm font-bold text-red-700 transition hover:border-red-300 hover:bg-red-50 disabled:opacity-60"
            >
              {canceling ? "Cancelando..." : "Cancelar processo"}
            </button>
          </div>
        ) : (
          <div className="flex flex-col gap-2 sm:flex-row">
            <button
              type="button"
              disabled={saving}
              onClick={gerarVenda}
              className="rounded-2xl bg-amber-500 px-5 py-3 text-sm font-bold text-white transition hover:bg-amber-600 disabled:opacity-60"
            >
              {saving ? "Gerando..." : "Gerar venda"}
            </button>
            <button
              type="button"
              disabled={canceling}
              onClick={cancelarProcesso}
              className="rounded-2xl border border-red-200 bg-white px-5 py-3 text-sm font-bold text-red-700 transition hover:border-red-300 hover:bg-red-50 disabled:opacity-60"
            >
              {canceling ? "Cancelando..." : "Cancelar processo"}
            </button>
          </div>
        )}
      </div>
      {alertas.length > 0 && (
        <div className="mt-3 space-y-2">
          {alertas.map((alerta) => (
            <div key={alerta} className="rounded-2xl border border-amber-200 bg-white px-4 py-2 text-sm font-bold text-amber-800">
              {alerta}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function abrirPdv(url) {
  if (!url) return;
  window.open(url, "_blank", "noopener,noreferrer");
}
