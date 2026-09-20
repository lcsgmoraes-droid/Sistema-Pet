import { Fragment, useState } from "react";
import { formatarMoeda } from "../../api/produtos";
import { formatarData, formatarDataHora, formatarQuantidade } from "./transferenciaParceiroUtils";
import { filtrarItensExtratoTransferencia } from "./extratoTransferenciaUtils";
import { StatusTransferenciaBadge } from "./transferenciaParceiroComponents";

const OPCOES_FOCO = [
  { id: "todos", label: "Todos os lancamentos" },
  { id: "dividas", label: "Dividas geradas" },
  { id: "creditos", label: "Pagamentos e creditos" },
  { id: "em_aberto", label: "Somente em aberto" },
];

function TotalExtrato({ titulo, valor, cor = "text-slate-900" }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{titulo}</p>
      <p className={`mt-1 text-lg font-bold ${cor}`}>{formatarMoeda(valor)}</p>
    </div>
  );
}

function DetalheLancamentoExtrato({ item }) {
  return (
    <div className="space-y-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <StatusTransferenciaBadge status={item.conta_status} label={item.conta_status_label} />
        {item.data_vencimento ? (
          <span className="text-xs text-slate-600">
            Vencimento do documento: {formatarData(item.data_vencimento)}
          </span>
        ) : null}
        {item.forma_pagamento_nome ? (
          <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
            Forma: {item.forma_pagamento_nome}
          </span>
        ) : null}
      </div>

      {item.observacoes ? (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Detalhes</p>
          <p className="mt-1 whitespace-pre-line text-sm text-slate-700">{item.observacoes}</p>
        </div>
      ) : null}

      {item.itens?.length ? (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-100 text-left text-xs uppercase tracking-wide text-slate-600">
              <tr>
                <th className="px-3 py-2">Produto</th>
                <th className="px-3 py-2 text-right">Qtd.</th>
                <th className="px-3 py-2 text-right">Custo</th>
                <th className="px-3 py-2 text-right">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {item.itens.map((produto, index) => (
                <tr key={`${item.id}-${produto.produto_id || produto.produto_nome}-${index}`}>
                  <td className="px-3 py-2">
                    <p className="font-medium text-slate-900">{produto.produto_nome}</p>
                    {produto.codigo ? (
                      <p className="text-xs text-slate-500">Codigo: {produto.codigo}</p>
                    ) : null}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-700">
                    {formatarQuantidade(produto.quantidade)}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-700">
                    {formatarMoeda(produto.custo_unitario)}
                  </td>
                  <td className="px-3 py-2 text-right font-semibold text-slate-900">
                    {formatarMoeda(produto.valor_total)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <p className="text-xs text-slate-500">
        {item.registrado_em
          ? `Registrado no sistema em ${formatarDataHora(item.registrado_em)}`
          : "Horario de registro nao disponivel"}
      </p>
    </div>
  );
}

export default function ExtratoTransferenciaParceiro({
  sectionRef,
  pessoaFiltroAplicada,
  pessoaNome,
  extrato,
  loading,
  erro,
  foco,
  onChangeFoco,
}) {
  const [expandidos, setExpandidos] = useState([]);
  const itens = filtrarItensExtratoTransferencia(extrato?.items, foco);
  const totais = extrato?.totais || {};

  const alternarDetalhe = (id) => {
    setExpandidos((anteriores) =>
      anteriores.includes(id) ? anteriores.filter((itemId) => itemId !== id) : [...anteriores, id],
    );
  };

  return (
    <section ref={sectionRef} className="scroll-mt-6 rounded-2xl border border-slate-200 bg-white">
      <div className="flex flex-col gap-3 border-b border-slate-200 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h3 className="text-base font-semibold text-slate-900">Extrato da pessoa</h3>
          <p className="mt-1 text-sm text-slate-600">
            Dividas e creditos em ordem de data, com saldo atualizado a cada lancamento.
          </p>
        </div>
        {pessoaFiltroAplicada ? (
          <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
            {pessoaNome || extrato?.parceiro_nome || "Pessoa selecionada"}
          </span>
        ) : null}
      </div>

      {!pessoaFiltroAplicada ? (
        <div className="px-5 py-8 text-center">
          <p className="font-semibold text-slate-900">Selecione uma pessoa para ver o extrato</p>
          <p className="mt-2 text-sm text-slate-500">
            O extrato junta tudo que ela retirou e tudo que pagou ou devolveu, data a data.
          </p>
        </div>
      ) : loading ? (
        <div className="px-5 py-8 text-center text-sm text-slate-500">Carregando extrato...</div>
      ) : erro ? (
        <div className="px-5 py-8 text-center text-sm font-medium text-rose-700">{erro}</div>
      ) : (
        <div className="space-y-4 p-5">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <TotalExtrato titulo="Saldo anterior" valor={totais.saldo_anterior} />
            <TotalExtrato
              titulo="Debitos no periodo"
              valor={totais.total_debitos}
              cor="text-rose-700"
            />
            <TotalExtrato
              titulo="Creditos no periodo"
              valor={totais.total_creditos}
              cor="text-emerald-700"
            />
            <TotalExtrato titulo="Saldo final" valor={totais.saldo_final} cor="text-amber-700" />
          </div>

          <div className="flex flex-wrap gap-2" aria-label="Filtrar lancamentos do extrato">
            {OPCOES_FOCO.map((opcao) => (
              <button
                key={opcao.id}
                type="button"
                onClick={() => onChangeFoco(opcao.id)}
                aria-pressed={foco === opcao.id}
                className={`rounded-full px-3 py-2 text-xs font-semibold transition ${
                  foco === opcao.id
                    ? "border border-blue-500 bg-blue-600 text-white shadow-sm"
                    : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                }`}
              >
                {opcao.label}
              </button>
            ))}
          </div>

          {itens.length ? (
            <div className="overflow-x-auto rounded-2xl border border-slate-200">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                  <tr>
                    <th className="px-4 py-3">Data</th>
                    <th className="px-4 py-3">Lancamento</th>
                    <th className="px-4 py-3">Documento</th>
                    <th className="px-4 py-3 text-right">Debito</th>
                    <th className="px-4 py-3 text-right">Credito</th>
                    <th className="px-4 py-3 text-right">Saldo apos lancamento</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {itens.map((item) => {
                    const expandido = expandidos.includes(item.id);
                    return (
                      <Fragment key={item.id}>
                        <tr className="align-top hover:bg-slate-50">
                          <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-slate-700">
                            {formatarData(item.data)}
                          </td>
                          <td className="px-4 py-3">
                            <button
                              type="button"
                              onClick={() => alternarDetalhe(item.id)}
                              aria-expanded={expandido}
                              className="text-left"
                            >
                              <span className="block text-sm font-semibold text-slate-900 hover:text-blue-700">
                                {item.tipo_label}
                              </span>
                              <span className="mt-1 block text-xs text-slate-500">
                                {item.descricao} · {expandido ? "Fechar detalhes" : "Ver detalhes"}
                              </span>
                            </button>
                          </td>
                          <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-600">
                            {item.documento || "-"}
                          </td>
                          <td className="whitespace-nowrap px-4 py-3 text-right text-sm font-semibold text-rose-700">
                            {Number(item.debito || 0) > 0 ? formatarMoeda(item.debito) : "-"}
                          </td>
                          <td className="whitespace-nowrap px-4 py-3 text-right text-sm font-semibold text-emerald-700">
                            {Number(item.credito || 0) > 0 ? formatarMoeda(item.credito) : "-"}
                          </td>
                          <td className="whitespace-nowrap px-4 py-3 text-right text-sm font-bold text-slate-900">
                            {formatarMoeda(item.saldo)}
                          </td>
                        </tr>
                        {expandido ? (
                          <tr>
                            <td colSpan="6" className="bg-slate-50 px-4 py-4">
                              <DetalheLancamentoExtrato item={item} />
                            </td>
                          </tr>
                        ) : null}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-300 px-5 py-8 text-center text-sm text-slate-500">
              Nenhum lancamento encontrado neste recorte do extrato.
            </div>
          )}
        </div>
      )}
    </section>
  );
}
