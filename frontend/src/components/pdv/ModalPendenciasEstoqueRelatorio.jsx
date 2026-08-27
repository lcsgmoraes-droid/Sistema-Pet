import { Download, PackageSearch, RefreshCw, ShoppingBasket, Tags, Users } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";

import api from "../../api";
import { baixarCsvListaEspera, formatarQuantidadeListaEspera } from "./pendenciasEstoqueRelatorio";

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

function TabelaProdutosMarca({ produtos }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
          <tr>
            <th className="px-3 py-2">SKU</th>
            <th className="px-3 py-2">Produto</th>
            <th className="px-3 py-2 text-right">Clientes</th>
            <th className="px-3 py-2 text-right">Qtd. desejada</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {produtos.map((produto) => (
            <tr key={produto.produto_id || `${produto.sku}-${produto.produto_nome}`}>
              <td className="whitespace-nowrap px-3 py-2 font-mono text-xs text-slate-600">
                {produto.sku}
              </td>
              <td className="px-3 py-2 font-medium text-slate-800">{produto.produto_nome}</td>
              <td className="px-3 py-2 text-right font-semibold text-blue-700">
                {produto.total_clientes}
              </td>
              <td className="px-3 py-2 text-right font-semibold text-emerald-700">
                {formatarQuantidadeListaEspera(produto.quantidade_total)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ModalPendenciasEstoqueRelatorio() {
  const [relatorio, setRelatorio] = useState(null);
  const [loading, setLoading] = useState(true);

  const carregarRelatorio = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get("/pendencias-estoque/relatorio");
      setRelatorio(response.data);
    } catch (error) {
      console.error("Erro ao carregar relatório da lista de espera:", error);
      toast.error(error.response?.data?.detail || "Erro ao carregar relatório da lista de espera");
      setRelatorio(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void carregarRelatorio();
  }, [carregarRelatorio]);

  if (loading) {
    return <p className="py-12 text-center text-slate-500">Montando relatório...</p>;
  }

  if (!relatorio) {
    return (
      <div className="py-12 text-center">
        <p className="text-slate-600">Não foi possível carregar o relatório.</p>
        <button
          type="button"
          onClick={carregarRelatorio}
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700"
        >
          <RefreshCw className="h-4 w-4" /> Tentar novamente
        </button>
      </div>
    );
  }

  const resumo = relatorio.resumo || {};
  const grupos = Array.isArray(relatorio.agrupado_por_fornecedor)
    ? relatorio.agrupado_por_fornecedor
    : [];
  const detalhes = Array.isArray(relatorio.detalhes) ? relatorio.detalhes : [];

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Necessidade de compra</h3>
          <p className="text-sm text-slate-600">
            Lista ativa, agrupada por fornecedor, marca e SKU.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={carregarRelatorio}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw className="h-4 w-4" /> Atualizar
          </button>
          <button
            type="button"
            onClick={() => baixarCsvListaEspera(relatorio)}
            disabled={!resumo.total_registros}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Download className="h-4 w-4" /> Baixar CSV
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <ResumoCard icon={Users} label="Clientes" valor={resumo.total_clientes || 0} />
        <ResumoCard icon={Tags} label="SKUs" valor={resumo.total_skus || 0} />
        <ResumoCard
          icon={ShoppingBasket}
          label="Qtd. desejada"
          valor={formatarQuantidadeListaEspera(resumo.quantidade_total)}
        />
        <ResumoCard
          icon={PackageSearch}
          label="Vínculos"
          valor={resumo.total_registros || 0}
          detalhe="cliente × produto"
        />
      </div>

      {grupos.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-300 py-12 text-center">
          <PackageSearch className="mx-auto h-12 w-12 text-slate-300" />
          <p className="mt-3 font-medium text-slate-600">A lista de espera ativa está vazia.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {grupos.map((grupo) => (
            <section
              key={grupo.fornecedor}
              className="overflow-hidden rounded-xl border border-slate-200 bg-white"
            >
              <div className="flex flex-col gap-1 bg-slate-800 px-4 py-3 text-white sm:flex-row sm:items-center sm:justify-between">
                <h4 className="font-bold">Fornecedor: {grupo.fornecedor}</h4>
                <p className="text-xs text-slate-200">
                  {grupo.total_skus} SKU(s) • {grupo.total_clientes} cliente(s) • Qtd.{" "}
                  {formatarQuantidadeListaEspera(grupo.quantidade_total)}
                </p>
              </div>
              <div className="divide-y divide-slate-200">
                {grupo.marcas.map((marca) => (
                  <div key={marca.marca}>
                    <div className="flex items-center justify-between bg-blue-50 px-4 py-2">
                      <h5 className="font-semibold text-blue-900">Marca: {marca.marca}</h5>
                      <span className="text-xs text-blue-700">
                        {marca.total_skus} SKU(s) • {marca.total_clientes} cliente(s)
                      </span>
                    </div>
                    <TabelaProdutosMarca produtos={marca.produtos} />
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}

      {detalhes.length > 0 && (
        <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <div className="border-b border-slate-200 bg-slate-50 px-4 py-3">
            <h4 className="font-bold text-slate-900">Cliente × produto</h4>
            <p className="text-xs text-slate-500">Quem aguarda cada item da lista.</p>
          </div>
          <div className="max-h-80 overflow-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="sticky top-0 bg-white text-left text-xs uppercase text-slate-500 shadow-sm">
                <tr>
                  <th className="px-3 py-2">Cliente</th>
                  <th className="px-3 py-2">Produto / SKU</th>
                  <th className="px-3 py-2">Marca</th>
                  <th className="px-3 py-2 text-right">Qtd.</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {detalhes.map((item) => (
                  <tr key={item.pendencia_id}>
                    <td className="px-3 py-2">
                      <p className="font-medium text-slate-800">{item.cliente_nome}</p>
                      <p className="text-xs text-slate-500">
                        {item.cliente_telefone || "Sem telefone"}
                      </p>
                    </td>
                    <td className="px-3 py-2">
                      <p className="text-slate-800">{item.produto_nome}</p>
                      <p className="font-mono text-xs text-slate-500">{item.sku}</p>
                    </td>
                    <td className="px-3 py-2 text-slate-600">{item.marca}</td>
                    <td className="px-3 py-2 text-right font-semibold text-slate-800">
                      {formatarQuantidadeListaEspera(item.quantidade_desejada)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
