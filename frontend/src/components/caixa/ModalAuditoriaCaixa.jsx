import { useEffect, useRef, useState } from "react";
import { RefreshCw, X } from "lucide-react";
import { conferirItemCaixa, obterAuditoriaCaixa } from "../../api/caixa";
import { formatMoneyBRL } from "../../utils/formatters";
import {
  FILTRO_SEM_PAGAMENTOS,
  TAMANHO_PAGINA_AUDITORIA,
  filtrarLancamentosAuditoria,
  filtrarVendasAuditoria,
  formasAuditoria,
  paginarAuditoria,
} from "../../utils/auditoriaCaixaUtils";
import SaleReference from "../ui/SaleReference";
import PaginationControls from "../ui/PaginationControls";
import AuditoriaCaixaPagamentosVenda from "./AuditoriaCaixaPagamentosVenda";
import AuditoriaCaixaResumoFormas from "./AuditoriaCaixaResumoFormas";

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
  const [pagina, setPagina] = useState(1);
  const inicioLista = useRef(null);

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
    setPagina(1);
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
  const caixa = auditoria?.resumo?.caixa;
  const formas = formasAuditoria(auditoria || {});
  const vendasTodas = auditoria?.vendas || [];
  const vendas = filtrarVendasAuditoria(vendasTodas, forma);
  const pagamentosSemCaixa = auditoria?.resumo?.pagamentos_vendas_sem_caixa;
  const lancamentos = filtrarLancamentosAuditoria(
    [
      ...(auditoria?.movimentacoes || []).map((item) => ({ ...item, tipo_item: "movimentacao" })),
      ...(auditoria?.pagamentos || []).map((item) => ({ ...item, tipo_item: "pagamento" })),
    ],
    forma,
  ).sort((a, b) => (b.data_movimento || "").localeCompare(a.data_movimento || ""));
  const itensAba =
    aba === "vendas" ? vendas : aba === "lancamentos" ? lancamentos : auditoria?.historico || [];
  const dadosPagina = paginarAuditoria(itensAba, pagina);
  const paginacao = (
    <PaginationControls
      currentPage={dadosPagina.pagina}
      totalItems={dadosPagina.total}
      itemsPerPage={TAMANHO_PAGINA_AUDITORIA}
      pageSizeOptions={[TAMANHO_PAGINA_AUDITORIA]}
      itemName={aba === "vendas" ? "vendas" : aba === "lancamentos" ? "lançamentos" : "eventos"}
      disabled={salvando !== null}
      className="my-4"
      onPageChange={(proximaPagina) => {
        setPagina(proximaPagina);
        inicioLista.current?.scrollIntoView({ block: "start" });
      }}
    />
  );
  const mudarForma = (novaForma) => {
    setForma(novaForma);
    setPagina(1);
  };

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
                  ["Recebimentos vinculados a este caixa", auditoria.resumo.total_recebido],
                  ["Saldo físico em dinheiro", auditoria.resumo.totais.saldo_atual],
                ].map(([titulo, valor]) => (
                  <div key={titulo} className="rounded-lg border p-3">
                    <p className="text-sm text-gray-600">{titulo}</p>
                    <p className="text-lg font-semibold">{formatMoneyBRL(valor)}</p>
                  </div>
                ))}
              </div>
              {pagamentosSemCaixa?.quantidade > 0 && (
                <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                  {pagamentosSemCaixa.quantidade} registros de pagamento destas vendas não têm caixa
                  de recebimento identificado ({formatMoneyBRL(pagamentosSemCaixa.total)}). Eles
                  aparecem nas vendas e no resumo dos pagamentos. Esse valor não representa
                  diferença ou saldo a receber: pagamentos em dinheiro podem já estar comprovados
                  pelas movimentações do caixa.
                </p>
              )}
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <AuditoriaCaixaResumoFormas
                  titulo="Pagamentos registrados nas vendas deste caixa"
                  descricao="Registros ativos de vendas finalizadas, com baixa parcial ou NF paga. Inclui pagamentos a prazo e pagamentos feitos em outros caixas."
                  formas={auditoria.resumo.pagamentos_vendas_por_forma_pagamento}
                />
                <AuditoriaCaixaResumoFormas
                  titulo="Recebimentos vinculados a este caixa"
                  descricao="Considera os recebimentos vinculados e as movimentações comprovadas de dinheiro."
                  formas={auditoria.resumo.recebimentos_por_forma_pagamento}
                />
              </div>
              <p className="mt-4 text-sm font-medium">Filtrar por forma de pagamento</p>
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => mudarForma("")}
                  className={`rounded border px-3 py-2 text-sm ${!forma ? "border-blue-600 bg-blue-50" : ""}`}
                >
                  Todas as formas
                </button>
                {formas.map(({ chave, rotulo }) => (
                  <button
                    key={chave}
                    type="button"
                    onClick={() => mudarForma(chave)}
                    className={`rounded border px-3 py-2 text-sm ${forma === chave ? "border-blue-600 bg-blue-50" : ""}`}
                  >
                    {rotulo}
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => mudarForma(FILTRO_SEM_PAGAMENTOS)}
                  className={`rounded border px-3 py-2 text-sm ${forma === FILTRO_SEM_PAGAMENTOS ? "border-blue-600 bg-blue-50" : ""}`}
                >
                  Sem pagamentos registrados
                </button>
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
                    onClick={() => {
                      setAba(id);
                      setPagina(1);
                    }}
                    className={`border-b-2 px-3 py-2 ${aba === id ? "border-blue-600 text-blue-700" : "border-transparent"}`}
                  >
                    {nome}
                  </button>
                ))}
              </nav>
              <div ref={inicioLista}>{paginacao}</div>
              {aba === "vendas" && (
                <div className="space-y-3">
                  <p className="text-sm text-gray-600">
                    {vendas.length} de {vendasTodas.length} vendas nesta seleção.
                  </p>
                  {vendas.length === 0 && (
                    <p className="py-6 text-center text-gray-500">Nenhuma venda nesta seleção.</p>
                  )}
                  {dadosPagina.itens.map((venda) => (
                    <div key={venda.id} className="rounded-lg border p-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <SaleReference sale={venda} />
                          <p className="text-sm text-gray-600">
                            {venda.cliente_nome} · {venda.status} · Venda de{" "}
                            {venda.data_venda?.split("-").reverse().join("/")}
                          </p>
                          {venda.caixa_origem_id == null ? (
                            <p className="text-sm text-amber-700">
                              Caixa de origem da venda não informado.
                            </p>
                          ) : (
                            Number(venda.caixa_origem_id) !== Number(caixa.id) && (
                              <p className="text-sm text-amber-700">
                                Venda de outro caixa, com lançamento neste caixa.
                              </p>
                            )
                          )}
                        </div>
                        <div className="text-right">
                          <p>Total da venda: {formatMoneyBRL(venda.total)}</p>
                          <p className="font-semibold">
                            Lançamentos neste caixa: {formatMoneyBRL(venda.valor_nesta_forma)}
                          </p>
                          {checkbox("venda", venda)}
                        </div>
                      </div>
                      <AuditoriaCaixaPagamentosVenda venda={venda} caixaId={caixa.id} />
                      <details className="mt-3">
                        <summary className="cursor-pointer text-sm font-medium text-blue-700">
                          Ver produtos da venda
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
                  {dadosPagina.itens.map((item) => (
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
                  {dadosPagina.itens.map((evento) => {
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
              {dadosPagina.totalPaginas > 1 && paginacao}
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
