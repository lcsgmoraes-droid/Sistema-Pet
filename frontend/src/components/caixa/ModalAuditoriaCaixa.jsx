import { useCallback, useEffect, useRef, useState } from "react";
import { Banknote, ChevronDown, ChevronUp, RefreshCw, WalletCards, X } from "lucide-react";
import { conferirItemCaixa, obterAuditoriaCaixa } from "../../api/caixa";
import { formatMoneyBRL } from "../../utils/formatters";
import {
  FILTRO_SEM_PAGAMENTOS,
  TAMANHO_PAGINA_AUDITORIA,
  filtrarLancamentosAuditoria,
  filtrarVendasAuditoria,
  formasAuditoria,
  paginarAuditoria,
  selecionarVendasAuditoria,
  naturezaQuitacaoAuditoria,
} from "../../utils/auditoriaCaixaUtils";
import SaleReference from "../ui/SaleReference";
import PaginationControls from "../ui/PaginationControls";
import AuditoriaCaixaPagamentosVenda from "./AuditoriaCaixaPagamentosVenda";
import AbasNavegacao from "../v2/AbasNavegacao/AbasNavegacao";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import CartaoIndicador from "../v2/CartaoIndicador/CartaoIndicador";
import InputCheckbox from "../v2/InputCheckbox/InputCheckbox";
import ResumoFaturamento, { DetalhesFaturamento } from "../v2/ResumoFaturamento/ResumoFaturamento";
import { periodoFaturamento } from "../v2/ResumoFaturamento/faturamentoPresentation";
import SeletorOpcoes from "../v2/SeletorOpcoes/SeletorOpcoes";
import RecebimentosCaixaPanel from "./RecebimentosCaixaPanel";

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
  const [recorte, setRecorte] = useState("periodo");
  const [detalhe, setDetalhe] = useState(null);
  const inicioLista = useRef(null);
  const requisicao = useRef(0);
  const ciclo = useRef(0);
  const caixaAtual = useRef(caixaId);
  caixaAtual.current = caixaId;

  const carregar = useCallback(
    async (ativo = () => true) => {
      const atual = ++requisicao.current;
      setLoading(true);
      setErro("");
      try {
        const dados = await obterAuditoriaCaixa(caixaId);
        if (ativo() && atual === requisicao.current) setAuditoria(dados);
      } catch (error) {
        if (ativo() && atual === requisicao.current) {
          setErro(error.response?.data?.detail || "Não foi possível carregar a auditoria.");
        }
      } finally {
        if (ativo() && atual === requisicao.current) setLoading(false);
      }
    },
    [caixaId],
  );

  useEffect(() => {
    let ativo = true;
    ciclo.current += 1;
    setPagina(1);
    setRecorte("periodo");
    setDetalhe(null);
    setForma("");
    setAba("vendas");
    setSalvando(null);
    carregar(() => ativo);
    return () => {
      ativo = false;
      ciclo.current += 1;
      requisicao.current += 1;
    };
  }, [carregar]);

  const conferir = async (tipo, item) => {
    const cicloConferencia = ciclo.current;
    const aindaAtivo = () => caixaAtual.current === caixaId && ciclo.current === cicloConferencia;
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
      if (aindaAtivo()) await carregar(aindaAtivo);
    } catch (error) {
      if (aindaAtivo())
        setErro(error.response?.data?.detail || "Não foi possível salvar a conferência.");
    } finally {
      if (aindaAtivo()) setSalvando(null);
    }
  };

  const checkbox = (tipo, item) => (
    <div className="inline-flex items-center text-sm font-medium">
      <InputCheckbox
        checked={item.conferido}
        disabled={salvando !== null}
        onChange={() => conferir(tipo, item)}
        rotulo={`Conferir ${tipo} ${item.id}`}
      />
      {salvando === `${tipo}:${item.id}`
        ? "Salvando..."
        : item.conferido
          ? "Conferido"
          : item.estado_conferencia === "divergencia"
            ? "Com divergência"
            : item.conferencia_alterada
              ? "Pendente — confira novamente"
              : "Conferir"}
    </div>
  );
  const caixa = auditoria?.resumo?.caixa;
  const formas = formasAuditoria(auditoria || {});
  const composicaoVendas = auditoria?.resumo?.vendas_periodo;
  const composicaoRecebimentos = auditoria?.resumo?.composicao_recebimentos;
  const vendasTodas = auditoria?.vendas || [];
  const vendasRecorte = selecionarVendasAuditoria(vendasTodas, composicaoVendas, recorte);
  const vendas = filtrarVendasAuditoria(vendasRecorte, forma);
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
        className="flex max-h-[92vh] w-full max-w-6xl flex-col rounded-xl bg-white text-slate-900 shadow-xl dark:bg-slate-900 dark:text-slate-100"
      >
        <header className="flex items-center justify-between border-b p-5">
          <div>
            <h2 id="titulo-auditoria-caixa" className="text-xl font-semibold">
              Auditoria do caixa {caixa ? `#${caixa.numero_caixa}` : ""}
            </h2>
            <p className="text-sm text-gray-600 dark:text-slate-300">
              Vendas pela data e caixa de origem. Recebimentos pelo caixa que os registrou,
              inclusive de vendas anteriores.
            </p>
          </div>
          <div className="flex gap-2">
            <BotaoInteracao
              tamanho="pequeno"
              onClick={() => carregar()}
              loading={loading}
              icon={RefreshCw}
              aria-label="Atualizar auditoria"
            />
            <BotaoInteracao
              tamanho="pequeno"
              onClick={onClose}
              icon={X}
              aria-label="Fechar auditoria"
            />
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
                <ResumoFaturamento
                  composicao={composicaoVendas}
                  titulo={`Vendas de ${periodoFaturamento(composicaoVendas)}`}
                  expandido={detalhe === "vendas"}
                  aoAlternarDetalhes={() =>
                    setDetalhe((atual) => (atual === "vendas" ? null : "vendas"))
                  }
                  detalhesFora
                  detalhesId="auditoria-detalhes-vendas"
                />
                <CartaoIndicador
                  icone={WalletCards}
                  tom="sucesso"
                  titulo="Recebimentos neste caixa"
                  detalhe={`${periodoFaturamento(composicaoRecebimentos)} · Somente este caixa`}
                >
                  <p className="text-2xl font-bold tabular-nums">
                    {composicaoRecebimentos
                      ? formatMoneyBRL(composicaoRecebimentos.total_recebido)
                      : "—"}
                  </p>
                  <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">
                    Pagamentos recebidos, menos devoluções e estornos. Créditos e cashback
                    separados.
                  </p>
                  {composicaoRecebimentos && (
                    <div className="mt-3">
                      <BotaoInteracao
                        tamanho="pequeno"
                        icon={detalhe === "recebimentos" ? ChevronUp : ChevronDown}
                        aria-expanded={detalhe === "recebimentos"}
                        aria-controls="auditoria-detalhes-recebimentos"
                        aria-label="Detalhes dos recebimentos neste caixa"
                        onClick={() =>
                          setDetalhe((atual) => (atual === "recebimentos" ? null : "recebimentos"))
                        }
                      >
                        {detalhe === "recebimentos" ? "Ocultar detalhes" : "Detalhes"}
                      </BotaoInteracao>
                    </div>
                  )}
                </CartaoIndicador>
                <CartaoIndicador
                  icone={Banknote}
                  titulo="Saldo físico em dinheiro"
                  detalhe="Apenas dinheiro, abertura e movimentações físicas do caixa."
                >
                  <p className="text-2xl font-bold tabular-nums">
                    {formatMoneyBRL(auditoria.resumo.totais.saldo_atual)}
                  </p>
                </CartaoIndicador>
              </div>
              {detalhe === "vendas" && (
                <div className="mt-4">
                  <DetalhesFaturamento
                    key={caixaId}
                    composicao={composicaoVendas}
                    id="auditoria-detalhes-vendas"
                  />
                </div>
              )}
              {detalhe === "recebimentos" && (
                <div className="mt-4" id="auditoria-detalhes-recebimentos">
                  <RecebimentosCaixaPanel composicao={composicaoRecebimentos} somenteDetalhes />
                </div>
              )}
              {pagamentosSemCaixa?.quantidade > 0 && (
                <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                  {pagamentosSemCaixa.quantidade} registros de pagamento destas vendas não têm caixa
                  de recebimento identificado ({formatMoneyBRL(pagamentosSemCaixa.total)}). Eles
                  aparecem no histórico das formas de quitação. Esse valor não representa diferença
                  ou saldo a receber: pagamentos em dinheiro podem já estar comprovados pelas
                  movimentações do caixa.
                </p>
              )}
              <h3 className="mb-3 mt-5 text-base font-semibold">Registros para conferência</h3>
              <SeletorOpcoes
                rotulo="Forma de quitação ou recebimento"
                valorSelecionado={forma}
                aoSelecionar={mudarForma}
                opcoes={[
                  { valor: "", rotulo: "Todas as formas" },
                  ...formas.map(({ chave, rotulo }) => ({ valor: chave, rotulo })),
                  { valor: FILTRO_SEM_PAGAMENTOS, rotulo: "Sem pagamentos registrados" },
                ]}
              />
              <AbasNavegacao
                className="my-4"
                ariaLabel="Seções da auditoria"
                ativa={aba}
                abas={[
                  { id: "vendas", label: "Vendas" },
                  { id: "lancamentos", label: "Lançamentos" },
                  { id: "historico", label: "Histórico" },
                ]}
                onChange={(id) => {
                  setAba(id);
                  setPagina(1);
                }}
              />
              {aba === "vendas" && (
                <SeletorOpcoes
                  rotulo="Exibir vendas"
                  valorSelecionado={recorte}
                  aoSelecionar={(valor) => {
                    setRecorte(valor);
                    setPagina(1);
                  }}
                  opcoes={[
                    { valor: "periodo", rotulo: "Vendas do período neste caixa" },
                    { valor: "outros", rotulo: "Outros vínculos" },
                    { valor: "todos", rotulo: "Todos os vínculos" },
                  ]}
                />
              )}
              <div ref={inicioLista}>{paginacao}</div>
              {aba === "vendas" && (
                <div className="space-y-3">
                  <p className="text-sm text-gray-600 dark:text-slate-300">
                    {vendas.length} de {vendasRecorte.length} vendas neste recorte.
                  </p>
                  {recorte !== "periodo" && (
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Outros vínculos podem incluir vendas anteriores, de outro caixa ou canceladas.
                      Esses registros são preservados para conferência e não entram nas vendas do
                      período acima.
                    </p>
                  )}
                  {vendas.length === 0 && (
                    <p className="py-6 text-center text-gray-500 dark:text-slate-400">
                      Nenhuma venda nesta seleção.
                    </p>
                  )}
                  {dadosPagina.itens.map((venda) => (
                    <div key={venda.id} className="rounded-lg border p-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <SaleReference sale={venda} />
                          <p className="text-sm text-gray-600 dark:text-slate-300">
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
                          <p>Total do pedido: {formatMoneyBRL(venda.total)}</p>
                          <p className="font-semibold">
                            Quitações e lançamentos neste caixa:{" "}
                            {formatMoneyBRL(venda.valor_nesta_forma)}
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
                        <p className="mt-2 text-xs text-gray-500 dark:text-slate-400">
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
                    <p className="py-6 text-center text-gray-500 dark:text-slate-400">
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
                        <p className="text-sm text-gray-600 dark:text-slate-300">
                          {item.forma_pagamento || "Dinheiro"} · {formatarData(item.data_movimento)}
                          {item.usuario_nome ? ` · ${item.usuario_nome}` : ""}
                        </p>
                        {naturezaQuitacaoAuditoria(item) && (
                          <p className="text-xs text-amber-700 dark:text-amber-300">
                            {naturezaQuitacaoAuditoria(item)}
                          </p>
                        )}
                        {item.venda_id && <SaleReference sale={item} className="text-sm" />}
                        {item.conferencia && (
                          <p className="mt-2 text-xs text-gray-500 dark:text-slate-400">
                            Última conferência: {item.conferencia.usuario_nome} ·{" "}
                            {formatarData(item.conferencia.data)}
                          </p>
                        )}
                      </div>
                      <div className="text-right">
                        <p
                          className={`font-semibold ${naturezaQuitacaoAuditoria(item) ? "text-slate-700 dark:text-slate-300" : item.natureza === "saida" ? "text-red-700" : "text-green-700"}`}
                        >
                          {naturezaQuitacaoAuditoria(item)
                            ? Number(item.valor) < 0
                              ? "−"
                              : ""
                            : item.natureza === "saida"
                              ? "−"
                              : "+"}
                          {formatMoneyBRL(Math.abs(Number(item.valor) || 0))}
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
                    <p className="text-gray-500 dark:text-slate-400">
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
                            {evento.dados.estado === "divergencia"
                              ? "divergência apontada"
                              : evento.dados.conferido
                                ? "conferido"
                                : "pendente de conferência"}
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
                            <p className="mt-2">
                              Quitações registradas no fechamento preservado (legado). Podem incluir
                              créditos, cashback e planos a prazo; não representam somente dinheiro
                              recebido.
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
        <footer className="border-t p-4 text-sm text-gray-600 dark:text-slate-300">
          As conferências ficam registradas com nome e data. Se um lançamento mudar, será necessário
          conferir novamente.
        </footer>
      </section>
    </div>
  );
}
