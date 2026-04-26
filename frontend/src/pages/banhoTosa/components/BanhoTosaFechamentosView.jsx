import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { banhoTosaApi } from "../banhoTosaApi";
import { formatCurrency, getApiErrorMessage } from "../banhoTosaUtils";

export default function BanhoTosaFechamentosView() {
  const [itens, setItens] = useState([]);
  const [loading, setLoading] = useState(false);
  const [processingId, setProcessingId] = useState(null);
  const [cancelingId, setCancelingId] = useState(null);
  const [syncingAll, setSyncingAll] = useState(false);

  async function carregar() {
    setLoading(true);
    try {
      const response = await banhoTosaApi.listarPendenciasFechamento({ limit: 300 });
      setItens(Array.isArray(response.data?.itens) ? response.data.itens : []);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel carregar fechamentos."));
      setItens([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    carregar();
  }, []);

  async function gerarVenda(item) {
    setProcessingId(item.atendimento_id);
    try {
      const response = await banhoTosaApi.gerarVendaAtendimento(item.atendimento_id);
      toast.success(response.data?.mensagem || "Venda gerada.");
      abrirPdv(response.data?.pdv_url);
      await carregar();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel gerar venda."));
    } finally {
      setProcessingId(null);
    }
  }

  async function sincronizar(item) {
    setProcessingId(item.atendimento_id);
    try {
      const response = await banhoTosaApi.sincronizarFechamentoAtendimento(item.atendimento_id);
      toast.success(response.data?.sincronizado ? "Fechamento sincronizado." : "Fechamento conferido.");
      await carregar();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel sincronizar."));
    } finally {
      setProcessingId(null);
    }
  }

  async function sincronizarTodos() {
    setSyncingAll(true);
    try {
      const response = await banhoTosaApi.sincronizarPendenciasFechamento({ limit: 300 });
      toast.success(`${response.data?.sincronizados || 0} fechamento(s) sincronizado(s).`);
      await carregar();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel sincronizar pendencias."));
    } finally {
      setSyncingAll(false);
    }
  }

  async function cancelarProcesso(item) {
    const motivo = window.prompt(
      `Informe o motivo para cancelar o atendimento #${item.atendimento_id} e todo o processo financeiro vinculado:`,
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

    setCancelingId(item.atendimento_id);
    try {
      const response = await banhoTosaApi.cancelarProcessoAtendimento(item.atendimento_id, {
        motivo: motivo.trim(),
      });
      toast.success(response.data?.mensagem || "Processo cancelado.");
      await carregar();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel cancelar o processo."));
    } finally {
      setCancelingId(null);
    }
  }

  const semVenda = itens.filter((item) => !item.venda_id).length;
  const abertas = itens.filter((item) => ["aberta", "baixa_parcial"].includes(item.venda_status)).length;
  const semConta = itens.filter(
    (item) => item.venda_id && item.venda_status === "finalizada" && !item.conta_receber_id,
  ).length;

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
              Fechamentos
            </p>
            <h2 className="mt-2 text-2xl font-black text-slate-900">
              Pendencias de cobranca
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Atendimentos prontos/entregues que ainda precisam de venda, pagamento ou conta sincronizada.
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <button type="button" onClick={carregar} disabled={loading} className="rounded-2xl border border-slate-200 px-5 py-3 text-sm font-bold text-slate-600 transition hover:border-orange-300 hover:text-orange-700 disabled:opacity-60">
              {loading ? "Atualizando..." : "Atualizar"}
            </button>
            <button type="button" onClick={sincronizarTodos} disabled={syncingAll || loading} className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-bold text-white transition hover:bg-slate-700 disabled:opacity-60">
              {syncingAll ? "Sincronizando..." : "Sincronizar todos"}
            </button>
          </div>
        </div>
      </section>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Pendencias" value={itens.length} detail="Atendimentos na fila de cobranca" />
        <Metric label="Sem venda" value={semVenda} detail="Precisa gerar PDV" />
        <Metric label="Venda aberta" value={abertas} detail="Aguardando recebimento no caixa" />
        <Metric label="Sem conta" value={semConta} detail="Finalizada sem financeiro sincronizado" />
      </div>

      {loading ? (
        <div className="rounded-3xl border border-white/80 bg-white p-10 text-center text-sm font-semibold text-slate-500 shadow-sm">
          Carregando fechamentos...
        </div>
      ) : itens.length === 0 ? (
        <div className="rounded-3xl border border-emerald-200 bg-emerald-50 p-8 text-center shadow-sm">
          <p className="text-lg font-black text-emerald-900">Fila de cobranca limpa.</p>
          <p className="mt-1 text-sm font-semibold text-emerald-700">Nenhum atendimento pronto/entregue com pendencia encontrada.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {itens.map((item) => (
            <FechamentoCard
              key={item.atendimento_id}
              item={item}
              processing={processingId === item.atendimento_id}
              canceling={cancelingId === item.atendimento_id}
              onGerarVenda={gerarVenda}
              onSincronizar={sincronizar}
              onCancelarProcesso={cancelarProcesso}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function FechamentoCard({
  item,
  processing,
  canceling,
  onGerarVenda,
  onSincronizar,
  onCancelarProcesso,
}) {
  return (
    <article className="rounded-3xl border border-white/80 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-orange-100 px-3 py-1 text-xs font-black uppercase tracking-[0.14em] text-orange-700">
              {item.status_atendimento}
            </span>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">
              Atendimento #{item.atendimento_id}
            </span>
          </div>
          <h3 className="mt-3 text-lg font-black text-slate-900">
            {item.pet_nome || `Pet #${item.pet_id}`}
          </h3>
          <p className="text-sm text-slate-500">
            Tutor: {item.cliente_nome || `#${item.cliente_id}`} | Finalizado: {formatDate(item.fim_em || item.entregue_em)}
          </p>
          <p className="mt-2 text-sm font-bold text-slate-700">
            {item.venda_id ? `Venda ${item.venda_numero || `#${item.venda_id}`} | ${item.venda_status || "-"} | ${item.status_pagamento}` : "Sem venda vinculada"}
          </p>
          {item.venda_id && (
            <p className="mt-1 text-xs font-semibold text-slate-500">
              Total {formatCurrency(item.total)} | Pago {formatCurrency(item.total_pago)} | Restante {formatCurrency(item.valor_restante)}
              {item.conta_receber_id ? ` | Conta #${item.conta_receber_id}` : " | Sem conta sincronizada"}
            </p>
          )}
          <Alertas alertas={item.alertas} />
        </div>
        <div className="flex flex-col gap-2 sm:flex-row lg:flex-col">
          {!item.venda_id ? (
            <button type="button" disabled={processing} onClick={() => onGerarVenda(item)} className="rounded-2xl bg-amber-500 px-5 py-3 text-sm font-bold text-white transition hover:bg-amber-600 disabled:opacity-60">
              {processing ? "Gerando..." : "Gerar venda"}
            </button>
          ) : (
            <>
              <button type="button" disabled={processing} onClick={() => onSincronizar(item)} className="rounded-2xl border border-amber-200 px-5 py-3 text-sm font-bold text-amber-700 transition hover:border-amber-300 disabled:opacity-60">
                {processing ? "Conferindo..." : "Sincronizar"}
              </button>
              <button type="button" onClick={() => abrirPdv(item.pdv_url)} className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-bold text-white transition hover:bg-slate-700">
                Abrir PDV
              </button>
            </>
          )}
          <button
            type="button"
            disabled={processing || canceling}
            onClick={() => onCancelarProcesso(item)}
            className="rounded-2xl border border-red-200 bg-red-50 px-5 py-3 text-sm font-bold text-red-700 transition hover:border-red-300 hover:bg-red-100 disabled:opacity-60"
          >
            {canceling ? "Cancelando..." : "Cancelar processo"}
          </button>
        </div>
      </div>
    </article>
  );
}

function Alertas({ alertas = [] }) {
  if (!alertas.length) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {alertas.map((alerta) => (
        <span key={alerta} className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-bold text-amber-800">
          {alerta}
        </span>
      ))}
    </div>
  );
}

function Metric({ label, value, detail }) {
  return (
    <div className="rounded-3xl border border-white/80 bg-white p-5 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-400">{label}</p>
      <p className="mt-2 text-3xl font-black text-slate-900">{value}</p>
      {detail && <p className="mt-1 text-xs font-semibold text-slate-400">{detail}</p>}
    </div>
  );
}

function abrirPdv(url) {
  if (!url) return;
  window.open(url, "_blank", "noopener,noreferrer");
}

function formatDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}
