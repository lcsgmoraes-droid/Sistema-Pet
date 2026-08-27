import {
  Download,
  PackageSearch,
  RefreshCw,
  SearchX,
  UserRoundCheck,
  WalletCards,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";

import api from "../../api";
import { formatMoneyBRL } from "../../utils/formatters";
import { MOTIVOS_NAO_VENDA } from "./naoVendaConstants";
import { baixarCsvNaoVendas, formatarQuantidadeNaoVenda } from "./naoVendaRelatorioCsv";

function dataLocalInput(data) {
  const ano = data.getFullYear();
  const mes = String(data.getMonth() + 1).padStart(2, "0");
  const dia = String(data.getDate()).padStart(2, "0");
  return `${ano}-${mes}-${dia}`;
}

function ResumoCard({ icon: Icon, label, valor, detalhe }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
      <div className="flex items-center gap-2 text-slate-500">
        <Icon className="h-4 w-4" />
        <span className="text-xs font-medium uppercase tracking-wide">{label}</span>
      </div>
      <p className="mt-2 text-2xl font-bold text-slate-900">{valor}</p>
      {detalhe && <p className="mt-1 text-xs text-slate-500">{detalhe}</p>}
    </div>
  );
}

export default function NaoVendaRelatorio() {
  const hoje = new Date();
  const [dataInicio, setDataInicio] = useState(
    dataLocalInput(new Date(hoje.getFullYear(), hoje.getMonth(), 1)),
  );
  const [dataFim, setDataFim] = useState(dataLocalInput(hoje));
  const [motivo, setMotivo] = useState("");
  const [relatorio, setRelatorio] = useState(null);
  const [loading, setLoading] = useState(true);

  const carregar = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get("/nao-vendas/relatorio", {
        params: {
          data_inicio: dataInicio,
          data_fim: dataFim,
          motivo: motivo || undefined,
        },
      });
      setRelatorio(response.data);
    } catch (error) {
      setRelatorio(null);
      toast.error(error.response?.data?.detail || "Erro ao carregar o relatório de não vendas");
    } finally {
      setLoading(false);
    }
  }, [dataFim, dataInicio, motivo]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const resumo = relatorio?.resumo || {};
  const motivos = Array.isArray(relatorio?.motivos) ? relatorio.motivos : [];
  const grupos = Array.isArray(relatorio?.agrupado_por_fornecedor)
    ? relatorio.agrupado_por_fornecedor
    : [];
  const detalhes = Array.isArray(relatorio?.detalhes) ? relatorio.detalhes : [];

  return (
    <div className="space-y-5">
      <div className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3 md:grid-cols-4">
        <label>
          <span className="mb-1 block text-xs font-medium text-slate-600">De</span>
          <input
            type="date"
            value={dataInicio}
            onChange={(event) => setDataInicio(event.target.value)}
            className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"
          />
        </label>
        <label>
          <span className="mb-1 block text-xs font-medium text-slate-600">Até</span>
          <input
            type="date"
            value={dataFim}
            onChange={(event) => setDataFim(event.target.value)}
            className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"
          />
        </label>
        <label>
          <span className="mb-1 block text-xs font-medium text-slate-600">Motivo</span>
          <select
            value={motivo}
            onChange={(event) => setMotivo(event.target.value)}
            className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"
          >
            <option value="">Todos os motivos</option>
            {MOTIVOS_NAO_VENDA.map((opcao) => (
              <option key={opcao.value} value={opcao.value}>
                {opcao.label}
              </option>
            ))}
          </select>
        </label>
        <div className="flex items-end gap-2">
          <button
            type="button"
            onClick={carregar}
            className="inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-100"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Atualizar
          </button>
          <button
            type="button"
            onClick={() => baixarCsvNaoVendas(relatorio)}
            disabled={!resumo.total_atendimentos}
            className="inline-flex h-10 items-center justify-center rounded-lg bg-emerald-600 px-3 text-white hover:bg-emerald-700 disabled:opacity-50"
            title="Baixar relatório completo em CSV"
          >
            <Download className="h-4 w-4" />
          </button>
        </div>
      </div>

      {loading && !relatorio ? (
        <p className="py-12 text-center text-slate-500">Montando relatório...</p>
      ) : !relatorio ? (
        <p className="py-12 text-center text-slate-500">Não foi possível carregar o relatório.</p>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <ResumoCard
              icon={SearchX}
              label="Não vendas"
              valor={resumo.total_atendimentos || 0}
              detalhe="visitas sem compra"
            />
            <ResumoCard
              icon={UserRoundCheck}
              label="Identificados"
              valor={resumo.atendimentos_identificados || 0}
              detalhe={`${resumo.atendimentos_anonimos || 0} anônimo(s)`}
            />
            <ResumoCard
              icon={PackageSearch}
              label="Produtos"
              valor={resumo.total_produtos_distintos || 0}
              detalhe={`Qtd. ${formatarQuantidadeNaoVenda(resumo.quantidade_total)}`}
            />
            <ResumoCard
              icon={WalletCards}
              label="Valor estimado"
              valor={formatMoneyBRL(resumo.valor_estimado_total || 0)}
            />
          </div>

          <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            <div className="border-b border-slate-200 bg-slate-50 px-4 py-3">
              <h3 className="font-bold text-slate-900">Por que as vendas foram perdidas</h3>
            </div>
            {motivos.length === 0 ? (
              <p className="px-4 py-8 text-center text-sm text-slate-500">
                Nenhum atendimento sem venda no período.
              </p>
            ) : (
              <div className="divide-y divide-slate-100">
                {motivos.map((item) => (
                  <div
                    key={item.codigo}
                    className="grid grid-cols-[1fr_auto_auto] items-center gap-4 px-4 py-3 text-sm"
                  >
                    <span className="font-medium text-slate-800">{item.motivo}</span>
                    <span className="text-right font-semibold text-slate-900">
                      {item.total_atendimentos} atendimento(s)
                    </span>
                    <span className="w-16 text-right text-slate-500">{item.percentual}%</span>
                  </div>
                ))}
              </div>
            )}
          </section>

          {grupos.length > 0 && (
            <section className="space-y-4">
              <div>
                <h3 className="font-bold text-slate-900">Produtos que os clientes procuraram</h3>
                <p className="text-xs text-slate-500">
                  Agrupados por fornecedor, marca e produto cadastrado ou livre.
                </p>
              </div>
              {grupos.map((grupo) => (
                <div
                  key={grupo.fornecedor}
                  className="overflow-hidden rounded-xl border border-slate-200 bg-white"
                >
                  <div className="flex flex-col justify-between gap-1 bg-slate-800 px-4 py-3 text-white sm:flex-row">
                    <h4 className="font-bold">Fornecedor: {grupo.fornecedor}</h4>
                    <span className="text-xs text-slate-200">
                      {grupo.total_produtos} produto(s) • Qtd.{" "}
                      {formatarQuantidadeNaoVenda(grupo.quantidade_total)}
                    </span>
                  </div>
                  {grupo.marcas.map((marca) => (
                    <div key={marca.marca} className="border-b border-slate-200 last:border-0">
                      <div className="bg-blue-50 px-4 py-2 text-sm font-semibold text-blue-900">
                        Marca: {marca.marca}
                      </div>
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-slate-200 text-sm">
                          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
                            <tr>
                              <th className="px-3 py-2">Produto / SKU</th>
                              <th className="px-3 py-2 text-right">Atendimentos</th>
                              <th className="px-3 py-2 text-right">Qtd.</th>
                              <th className="px-3 py-2 text-right">Valor estimado</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {marca.produtos.map((produto) => (
                              <tr
                                key={produto.produto_id || `${produto.sku}-${produto.produto_nome}`}
                              >
                                <td className="px-3 py-2">
                                  <p className="font-medium text-slate-800">
                                    {produto.produto_nome}
                                  </p>
                                  <p className="font-mono text-xs text-slate-500">{produto.sku}</p>
                                </td>
                                <td className="px-3 py-2 text-right font-semibold text-blue-700">
                                  {produto.total_atendimentos}
                                </td>
                                <td className="px-3 py-2 text-right font-semibold text-slate-800">
                                  {formatarQuantidadeNaoVenda(produto.quantidade_total)}
                                </td>
                                <td className="px-3 py-2 text-right text-slate-700">
                                  {formatMoneyBRL(produto.valor_estimado_total || 0)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </section>
          )}

          {detalhes.length > 0 && (
            <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
              <div className="border-b border-slate-200 bg-slate-50 px-4 py-3">
                <h3 className="font-bold text-slate-900">Atendimento × produto</h3>
                <p className="text-xs text-slate-500">
                  Lista completa de quem entrou, o motivo e o que procurou.
                </p>
              </div>
              <div className="max-h-96 divide-y divide-slate-100 overflow-y-auto">
                {detalhes.map((registro) => (
                  <div key={registro.registro_id} className="px-4 py-3">
                    <div className="flex flex-col justify-between gap-1 sm:flex-row">
                      <div>
                        <p className="font-semibold text-slate-900">{registro.cliente_nome}</p>
                        <p className="text-xs text-slate-500">
                          {registro.cliente_telefone || "Sem telefone"} • {registro.motivo}
                        </p>
                      </div>
                      <p className="text-xs text-slate-500">
                        {registro.data_registro
                          ? new Date(registro.data_registro).toLocaleString("pt-BR")
                          : ""}
                      </p>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {registro.itens.length > 0 ? (
                        registro.itens.map((item) => (
                          <span
                            key={item.item_id}
                            className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-700"
                          >
                            {item.produto_nome} • Qtd. {formatarQuantidadeNaoVenda(item.quantidade)}
                          </span>
                        ))
                      ) : (
                        <span className="text-xs italic text-slate-400">Sem produto informado</span>
                      )}
                    </div>
                    {registro.observacoes && (
                      <p className="mt-2 text-xs text-slate-600">{registro.observacoes}</p>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
