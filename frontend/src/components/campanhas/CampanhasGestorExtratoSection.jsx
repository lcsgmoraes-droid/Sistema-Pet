import { useMemo, useState } from "react";
import { Download } from "lucide-react";
import { actionButtonClasses } from "../ui/actionStyles";
import CopyableValue from "../ui/CopyableValue";

const TIPO_LABELS = {
  todos: "Todos",
  carimbo: "Carimbos",
  cashback: "Cashback",
  cupom: "Cupons",
  ranking: "Ranking",
};

const DIRECAO_CLASS = {
  credito: "border-emerald-200 bg-emerald-50 text-emerald-700",
  debito: "border-red-200 bg-red-50 text-red-700",
  neutro: "border-slate-200 bg-slate-50 text-slate-700",
};

function formatarDataHora(iso) {
  if (!iso) return "-";
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return "-";
  return data.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatarValor(evento, formatBRL) {
  if (evento.categoria === "carimbo") {
    const quantidade = Number(evento.quantidade || 0);
    if (!quantidade) return "-";
    return `${quantidade > 0 ? "+" : ""}${quantidade} carimbo(s)`;
  }

  if (evento.valor === null || evento.valor === undefined) return "-";

  const valor = Number(evento.valor || 0);
  if (evento.metadata?.valor_tipo === "percentual") {
    return `${valor.toLocaleString("pt-BR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}%`;
  }
  return `${valor < 0 ? "-" : ""}R$ ${formatBRL(Math.abs(valor))}`;
}

function baixarCsv(eventos, clienteNome, formatBRL) {
  const header = [
    "Data",
    "Tipo",
    "Direcao",
    "Titulo",
    "Campanha",
    "Venda",
    "Cupom",
    "Valor",
    "Saldo carimbos",
    "Saldo cashback",
    "Descricao",
  ];
  const linhas = eventos.map((evento) => [
    formatarDataHora(evento.data),
    evento.categoria || "",
    evento.direcao || "",
    evento.titulo || "",
    evento.campanha_nome || "",
    evento.numero_venda || evento.venda_id || "",
    evento.cupom_codigo || "",
    formatarValor(evento, formatBRL),
    evento.saldo_carimbos ?? "",
    evento.saldo_cashback !== null && evento.saldo_cashback !== undefined
      ? `R$ ${formatBRL(evento.saldo_cashback)}`
      : "",
    evento.descricao || "",
  ]);
  const csv = [header, ...linhas]
    .map((linha) =>
      linha
        .map((campo) => `"${String(campo).replace(/"/g, '""')}"`)
        .join(";"),
    )
    .join("\n");

  const blob = new Blob([`\uFEFF${csv}`], {
    type: "text/csv;charset=utf-8;",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const nome = (clienteNome || "cliente").replace(/\s+/g, "-").toLowerCase();
  link.href = url;
  link.download = `extrato-campanhas-${nome}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

export default function CampanhasGestorExtratoSection({
  gestorExtrato,
  gestorSecao,
  setGestorSecao,
  formatBRL,
}) {
  const [filtroTipo, setFiltroTipo] = useState("todos");
  const aberto = gestorSecao === "extrato";
  const eventos = gestorExtrato?.eventos || [];
  const eventosFiltrados = useMemo(() => {
    if (filtroTipo === "todos") return eventos;
    return eventos.filter((evento) => evento.categoria === filtroTipo);
  }, [eventos, filtroTipo]);

  const resumo = gestorExtrato?.saldo_atual || {};

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
      <button
        type="button"
        onClick={() => setGestorSecao(aberto ? null : "extrato")}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <div>
          <h3 className="font-semibold text-gray-900">Extrato de campanhas</h3>
          <p className="text-xs text-gray-500">
            Rastreie o que gerou credito, debito, cupom, estorno e saldo.
          </p>
        </div>
        <span className="text-sm text-blue-700">{aberto ? "Ocultar" : "Ver extrato"}</span>
      </button>

      {aberto && (
        <div className="border-t border-gray-100 p-4 space-y-4">
          {!gestorExtrato ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              Extrato nao disponivel no momento. Os demais dados do gestor
              continuam carregados.
            </div>
          ) : (
            <>
              <div className="grid gap-3 md:grid-cols-4">
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs font-medium uppercase text-slate-500">Carimbos disp.</p>
                  <p className="text-lg font-bold text-slate-900">
                    {resumo.carimbos_disponiveis ?? 0}
                  </p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs font-medium uppercase text-slate-500">Comprometidos</p>
                  <p className="text-lg font-bold text-slate-900">
                    {resumo.carimbos_comprometidos ?? 0}
                  </p>
                </div>
                <div className="rounded-lg border border-red-200 bg-red-50 p-3">
                  <p className="text-xs font-medium uppercase text-red-600">Em debito</p>
                  <p className="text-lg font-bold text-red-700">
                    {resumo.carimbos_em_debito ?? 0}
                  </p>
                </div>
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
                  <p className="text-xs font-medium uppercase text-emerald-700">Cashback</p>
                  <p className="text-lg font-bold text-emerald-800">
                    R$ {formatBRL(resumo.cashback || 0)}
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3">
                <select
                  value={filtroTipo}
                  onChange={(event) => setFiltroTipo(event.target.value)}
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
                >
                  {Object.entries(TIPO_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>

                <button
                  type="button"
                  onClick={() =>
                    baixarCsv(
                      eventosFiltrados,
                      gestorExtrato?.cliente_nome,
                      formatBRL,
                    )
                  }
                  disabled={eventosFiltrados.length === 0}
                  className={actionButtonClasses({
                    intent: "neutral",
                    tone: "soft",
                    size: "sm",
                  })}
                >
                  <Download className="h-4 w-4" />
                  Exportar CSV
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                    <tr>
                      <th className="px-3 py-2 text-left">Data</th>
                      <th className="px-3 py-2 text-left">Evento</th>
                      <th className="px-3 py-2 text-left">Origem</th>
                      <th className="px-3 py-2 text-right">Impacto</th>
                      <th className="px-3 py-2 text-right">Saldo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {eventosFiltrados.length === 0 ? (
                      <tr>
                        <td colSpan="5" className="px-3 py-6 text-center text-gray-500">
                          Nenhum evento encontrado para este filtro.
                        </td>
                      </tr>
                    ) : (
                      eventosFiltrados.map((evento) => (
                        <tr key={evento.id} className="border-t border-gray-100">
                          <td className="whitespace-nowrap px-3 py-3 text-gray-600">
                            {formatarDataHora(evento.data)}
                          </td>
                          <td className="px-3 py-3">
                            <div className="flex flex-col gap-1">
                              <span className="font-medium text-gray-900">
                                {evento.titulo}
                              </span>
                              <span className="text-xs text-gray-500">
                                {evento.descricao || "-"}
                              </span>
                            </div>
                          </td>
                          <td className="px-3 py-3 text-xs text-gray-600">
                            <div className="flex flex-col gap-1">
                              <span>{evento.campanha_nome || TIPO_LABELS[evento.categoria] || "-"}</span>
                              {evento.numero_venda || evento.venda_id ? (
                                <CopyableValue
                                  title="Copiar venda"
                                  value={evento.numero_venda || evento.venda_id}
                                >
                                  Venda {evento.numero_venda || `#${evento.venda_id}`}
                                </CopyableValue>
                              ) : null}
                              {evento.cupom_codigo ? <span>Cupom {evento.cupom_codigo}</span> : null}
                            </div>
                          </td>
                          <td className="px-3 py-3 text-right">
                            <span
                              className={`inline-flex rounded-full border px-2 py-1 text-xs font-semibold ${
                                DIRECAO_CLASS[evento.direcao] || DIRECAO_CLASS.neutro
                              }`}
                            >
                              {formatarValor(evento, formatBRL)}
                            </span>
                          </td>
                          <td className="whitespace-nowrap px-3 py-3 text-right text-xs text-gray-600">
                            {evento.categoria === "carimbo" && evento.saldo_carimbos !== null
                              ? `${evento.saldo_carimbos} carimbo(s)`
                              : evento.categoria === "cashback" && evento.saldo_cashback !== null
                                ? `R$ ${formatBRL(evento.saldo_cashback)}`
                                : "-"}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
