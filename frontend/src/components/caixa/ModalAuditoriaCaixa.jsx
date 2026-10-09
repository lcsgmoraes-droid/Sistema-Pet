import { useEffect, useState } from "react";
import { RefreshCw, X } from "lucide-react";
import { conferirItemCaixa, obterAuditoriaCaixa } from "../../api/caixa";
import { formatMoneyBRL } from "../../utils/formatters";
import SaleReference from "../ui/SaleReference";

const formatarData = (data) => (data ? new Date(data).toLocaleString("pt-BR") : "—");
const rotulosHistorico = {
  caixa_fechado: "Fechamento",
  caixa_reaberto: "Reabertura",
  caixa_conferencia: "Conferência",
};

export default function ModalAuditoriaCaixa({ caixaId, onClose }) {
  const [auditoria, setAuditoria] = useState(null);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState("");
  const [aba, setAba] = useState("vendas");
  const [forma, setForma] = useState("");
  const [salvando, setSalvando] = useState(null);

  const carregar = async () => {
    setLoading(true);
    setErro("");
    try {
      setAuditoria(await obterAuditoriaCaixa(caixaId));
    } catch (error) {
      setErro(error.response?.data?.detail || "Não foi possível carregar a auditoria.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    carregar();
  }, [caixaId]);

  const conferir = async (tipo, item) => {
    const chave = `${tipo}:${item.id}`;
    setSalvando(chave);
    setErro("");
    try {
      await conferirItemCaixa(caixaId, {
        tipo_item: tipo,
        item_id: item.id,
        conferido: !item.conferido,
        assinatura: item.assinatura,
      });
      await carregar();
    } catch (error) {
      setErro(error.response?.data?.detail || "Não foi possível salvar a conferência.");
    } finally {
      setSalvando(null);
    }
  };

  const checkbox = (tipo, item) => (
    <label className="inline-flex items-center gap-2 text-sm font-medium">
      <input
        type="checkbox"
        checked={item.conferido}
        disabled={salvando !== null}
        onChange={() => conferir(tipo, item)}
        aria-label={`Conferir ${tipo} ${item.id}`}
      />
      {salvando === `${tipo}:${item.id}`
        ? "Salvando..."
        : item.conferido
          ? "Conferido"
          : "Conferir"}
    </label>
  );
  const caixa = auditoria?.resumo.caixa;
  const formas = auditoria?.resumo.vendas_por_forma_pagamento || {};
  const vendas = (auditoria?.vendas || []).filter(
    (venda) => !forma || venda.recebimentos.some((item) => item.forma_pagamento === forma),
  );
  const lancamentos = [
    ...(auditoria?.movimentacoes || []).map((item) => ({ ...item, tipo_item: "movimentacao" })),
    ...(auditoria?.pagamentos || []).map((item) => ({ ...item, tipo_item: "pagamento" })),
  ]
    .filter((item) => !forma || item.forma_pagamento === forma)
    .sort((a, b) => (b.data_movimento || "").localeCompare(a.data_movimento || ""));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-auditoria-caixa"
        className="flex max-h-[92vh] w-full max-w-6xl flex-col rounded-xl bg-white shadow-xl"
      >
        <header className="flex items-center justify-between border-b p-5">
          <div>
            <h2 id="titulo-auditoria-caixa" className="text-xl font-semibold">
              Auditoria do caixa {caixa ? `#${caixa.numero_caixa}` : ""}
            </h2>
            <p className="text-sm text-gray-600">
              Confira cada venda e lançamento. Os recebimentos pertencem ao dia em que foram
              recebidos.
            </p>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={carregar}
              disabled={loading}
              aria-label="Atualizar auditoria"
              className="p-2"
            >
              <RefreshCw className={`h-5 w-5 ${loading ? "animate-spin" : ""}`} />
            </button>
            <button type="button" onClick={onClose} aria-label="Fechar auditoria" className="p-2">
              <X className="h-5 w-5" />
            </button>
          </div>
        </header>
        <div className="flex-1 overflow-y-auto p-5">
          {erro && (
            <p role="alert" className="mb-4 rounded bg-red-50 p-3 text-red-700">
              {erro}
            </p>
          )}
          {loading ? (
            <p className="py-8 text-center">Carregando auditoria...</p>
          ) : auditoria ? (
            <>
              <div className="grid gap-3 sm:grid-cols-3">
                {[
                  ["Vendas registradas neste caixa", auditoria.resumo.total_vendido],
                  ["Recebido neste caixa", auditoria.resumo.total_recebido],
                  ["Saldo físico em dinheiro", auditoria.resumo.totais.saldo_atual],
                ].map(([titulo, valor]) => (
                  <div key={titulo} className="rounded-lg border p-3">
                    <p className="text-sm text-gray-600">{titulo}</p>
                    <p className="text-lg font-semibold">{formatMoneyBRL(valor)}</p>
                  </div>
                ))}
              </div>
              <p className="mt-4 text-sm font-medium">Resumo por forma de pagamento</p>
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setForma("")}
                  className={`rounded border px-3 py-2 text-sm ${!forma ? "border-blue-600 bg-blue-50" : ""}`}
                >
                  Todas as formas
                </button>
                {Object.entries(formas).map(([nome, dados]) => (
                  <button
                    key={nome}
                    type="button"
                    onClick={() => setForma(nome)}
                    className={`rounded border px-3 py-2 text-sm ${forma === nome ? "border-blue-600 bg-blue-50" : ""}`}
                  >
                    {nome}: {formatMoneyBRL(dados.total)}
                    {["crediário", "crediario", "boleto"].includes(nome.toLowerCase()) &&
                      " (a prazo)"}
                  </button>
                ))}
              </div>
              <nav className="my-4 flex gap-3 border-b" aria-label="Seções da auditoria">
                {[
                  ["vendas", "Vendas"],
                  ["lancamentos", "Lançamentos"],
                  ["historico", "Histórico"],
                ].map(([id, nome]) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setAba(id)}
                    className={`border-b-2 px-3 py-2 ${aba === id ? "border-blue-600 text-blue-700" : "border-transparent"}`}
                  >
                    {nome}
                  </button>
                ))}
              </nav>
              {aba === "vendas" && (
                <div className="space-y-3">
                  {vendas.length === 0 && (
                    <p className="py-6 text-center text-gray-500">Nenhuma venda nesta seleção.</p>
                  )}
                  {vendas.map((venda) => (
                    <div key={venda.id} className="rounded-lg border p-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <SaleReference sale={venda} />
                          <p className="text-sm text-gray-600">
                            {venda.cliente_nome} · {venda.status} · Venda de{" "}
                            {venda.data_venda?.split("-").reverse().join("/")}
                          </p>
                          {venda.caixa_origem_id !== caixa.id && (
                            <p className="text-sm text-amber-700">
                              Venda de outro caixa, recebida neste caixa.
                            </p>
                          )}
                        </div>
                        <div className="text-right">
                          <p>Total da venda: {formatMoneyBRL(venda.total)}</p>
                          <p className="font-semibold">
                            Lançado neste caixa: {formatMoneyBRL(venda.valor_nesta_forma)}
                          </p>
                          {checkbox("venda", venda)}
                        </div>
                      </div>
                      <details className="mt-3">
                        <summary className="cursor-pointer text-sm font-medium text-blue-700">
                          Ver produtos e recebimentos
                        </summary>
                        <div className="mt-2 space-y-1 text-sm">
                          {venda.itens.map((item) => (
                            <p key={item.id}>
                              {item.produto_nome} ·{" "}
                              {Number(item.quantidade).toLocaleString("pt-BR", {
                                maximumFractionDigits: 3,
                              })}{" "}
                              un. · {formatMoneyBRL(item.subtotal)}
                            </p>
                          ))}
                          <p className="pt-2 font-medium">Recebimentos neste caixa</p>
                          {venda.recebimentos.length === 0 && (
                            <p className="text-gray-500">Sem recebimentos neste caixa.</p>
                          )}
                          {venda.recebimentos.map((item) => (
                            <p key={`${item.tipo}:${item.id}`}>
                              {item.forma_pagamento} · {formatMoneyBRL(item.valor)} ·{" "}
                              {formatarData(item.data_recebimento)}
                            </p>
                          ))}
                        </div>
                      </details>
                      {venda.conferencia && (
                        <p className="mt-2 text-xs text-gray-500">
                          Última conferência: {venda.conferencia.usuario_nome} ·{" "}
                          {formatarData(venda.conferencia.data)}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
              {aba === "lancamentos" && (
                <div className="space-y-3">
                  {lancamentos.length === 0 && (
                    <p className="py-6 text-center text-gray-500">
                      Nenhum lançamento nesta seleção.
                    </p>
                  )}
                  {lancamentos.map((item) => (
                    <div
                      key={`${item.tipo_item}:${item.id}`}
                      className="flex flex-wrap justify-between gap-3 rounded-lg border p-4"
                    >
                      <div>
                        <p className="font-medium">{item.descricao || item.tipo}</p>
                        <p className="text-sm text-gray-600">
                          {item.forma_pagamento || "Dinheiro"} · {formatarData(item.data_movimento)}
                          {item.usuario_nome ? ` · ${item.usuario_nome}` : ""}
                        </p>
                        {item.venda_id && <SaleReference sale={item} className="text-sm" />}
                        {item.conferencia && (
                          <p className="mt-2 text-xs text-gray-500">
                            Última conferência: {item.conferencia.usuario_nome} ·{" "}
                            {formatarData(item.conferencia.data)}
                          </p>
                        )}
                      </div>
                      <div className="text-right">
                        <p
                          className={`font-semibold ${item.natureza === "saida" ? "text-red-700" : "text-green-700"}`}
                        >
                          {item.natureza === "saida" ? "−" : "+"}
                          {formatMoneyBRL(item.valor)}
                        </p>
                        {checkbox(item.tipo_item, item)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
              {aba === "historico" && (
                <div className="space-y-3">
                  {auditoria.historico.length === 0 && (
                    <p className="text-gray-500">
                      Nenhuma conferência ou reabertura registrada ainda.
                    </p>
                  )}
                  {auditoria.historico.map((evento) => {
                    const snapshot = evento.anterior?.resumo || evento.dados.resumo;
                    return (
                      <div key={evento.id} className="rounded-lg border p-4">
                        <p className="font-medium">
                          {rotulosHistorico[evento.acao]} · {evento.usuario_nome} ·{" "}
                          {formatarData(evento.data)}
                        </p>
                        {evento.observacao && <p className="text-sm">{evento.observacao}</p>}
                        {evento.dados.tipo_item && (
                          <p className="text-sm">
                            {evento.dados.tipo_item} #{evento.dados.item_id}:{" "}
                            {evento.dados.conferido ? "conferido" : "conferência retirada"}
                          </p>
                        )}
                        {snapshot && (
                          <details className="mt-2 text-sm">
                            <summary className="cursor-pointer text-blue-700">
                              Ver fechamento preservado
                            </summary>
                            <p>
                              Fechado em {formatarData(snapshot.caixa.data_fechamento)} · Contado:{" "}
                              {formatMoneyBRL(snapshot.caixa.valor_informado)} · Esperado:{" "}
                              {formatMoneyBRL(snapshot.caixa.valor_esperado)}
                            </p>
                            {Object.entries(snapshot.vendas_por_forma_pagamento || {}).map(
                              ([nome, dados]) => (
                                <p key={nome}>
                                  {nome}: {formatMoneyBRL(dados.total)}
                                </p>
                              ),
                            )}
                          </details>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          ) : null}
        </div>
        <footer className="border-t p-4 text-sm text-gray-600">
          As conferências ficam registradas com nome e data. Se um lançamento mudar, será necessário
          conferir novamente.
        </footer>
      </section>
    </div>
  );
}
