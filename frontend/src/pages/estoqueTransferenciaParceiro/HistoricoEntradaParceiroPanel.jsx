import { formatarMoeda } from "../../api/produtos";
import { formatarData } from "./transferenciaParceiroUtils";
import { StatusTransferenciaBadge } from "./transferenciaParceiroComponents";

function TotalEntradaParceiro({ titulo, valor, destaque = "text-slate-900" }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{titulo}</p>
      <p className={`mt-1 text-base font-bold ${destaque}`}>{formatarMoeda(valor)}</p>
    </div>
  );
}

function EntradaParceiroRow({ entrada }) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="text-sm font-semibold text-slate-900">
              {entrada.documento || `Entrada #${entrada.conta_pagar_id}`}
            </h4>
            <StatusTransferenciaBadge status={entrada.status} label={entrada.status_label} />
            <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600">
              {entrada.estoque_atualizado ? "Estoque lancado" : "Sem entrada no estoque"}
            </span>
          </div>
          <p className="text-sm text-slate-700">
            {entrada.parceiro_nome}
            {entrada.parceiro_codigo ? ` | Codigo ${entrada.parceiro_codigo}` : ""}
          </p>
          <p className="text-xs text-slate-500">
            Emissao: {formatarData(entrada.data_emissao)} | Vencimento:{" "}
            {formatarData(entrada.data_vencimento)} | Pagamento:{" "}
            {formatarData(entrada.data_pagamento)}
          </p>
          {entrada.observacoes ? (
            <p className="line-clamp-2 text-xs text-slate-500">{entrada.observacoes}</p>
          ) : null}
        </div>

        <div className="grid min-w-0 gap-2 sm:grid-cols-3 lg:w-[420px]">
          <TotalEntradaParceiro titulo="Divida" valor={entrada.valor_original} />
          <TotalEntradaParceiro
            titulo="Pago"
            valor={entrada.valor_pago}
            destaque="text-emerald-700"
          />
          <TotalEntradaParceiro
            titulo="Saldo"
            valor={entrada.saldo_aberto}
            destaque="text-amber-700"
          />
        </div>
      </div>
    </article>
  );
}

export default function HistoricoEntradaParceiroPanel({
  entradasParceiro,
  loading,
  pagina = 1,
  onSetPagina,
}) {
  const items = Array.isArray(entradasParceiro?.items) ? entradasParceiro.items : [];
  const totais = entradasParceiro?.totais || {};
  const totalRegistros = Number(totais.total_registros || entradasParceiro?.total || 0);
  const totalPaginas = Number(entradasParceiro?.pages || 0);

  return (
    <section className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h3 className="text-base font-semibold text-slate-900">Entradas do parceiro</h3>
          <p className="mt-1 text-sm text-slate-500">
            Produtos recebidos de parceiros que geraram divida para acerto.
          </p>
        </div>
        <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-600">
          Exibindo {items.length} de {totalRegistros}
        </span>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <TotalEntradaParceiro titulo="Total da divida" valor={totais.valor_total || 0} />
        <TotalEntradaParceiro
          titulo="Pago"
          valor={totais.valor_pago || 0}
          destaque="text-emerald-700"
        />
        <TotalEntradaParceiro
          titulo="Saldo aberto"
          valor={totais.saldo_aberto || 0}
          destaque="text-amber-700"
        />
      </div>

      <div className="mt-4 space-y-3">
        {loading ? (
          <p className="rounded-2xl border border-slate-200 bg-white px-4 py-5 text-center text-sm text-slate-500">
            Carregando entradas de parceiro...
          </p>
        ) : items.length > 0 ? (
          items.map((entrada) => (
            <EntradaParceiroRow key={entrada.conta_pagar_id} entrada={entrada} />
          ))
        ) : (
          <p className="rounded-2xl border border-slate-200 bg-white px-4 py-5 text-center text-sm text-slate-500">
            Nenhuma entrada de parceiro encontrada no filtro atual.
          </p>
        )}
      </div>

      {totalPaginas > 1 ? (
        <div className="mt-4 flex flex-wrap items-center justify-end gap-2">
          <button
            type="button"
            onClick={() => onSetPagina?.((prev) => Math.max(prev - 1, 1))}
            disabled={pagina <= 1 || loading}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 transition-colors hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Anterior
          </button>
          <span className="text-sm text-slate-600">
            Pagina {entradasParceiro?.page || pagina} de {totalPaginas}
          </span>
          <button
            type="button"
            onClick={() => onSetPagina?.((prev) => Math.min(prev + 1, totalPaginas))}
            disabled={pagina >= totalPaginas || loading}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 transition-colors hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Proxima
          </button>
        </div>
      ) : null}
    </section>
  );
}
