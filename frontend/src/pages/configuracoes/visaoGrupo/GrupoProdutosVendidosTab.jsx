import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiBox, FiDollarSign, FiLayers, FiShoppingCart } from "react-icons/fi";
import EmptyState from "../../../components/ui/EmptyState";
import MetricCard from "../../../components/ui/MetricCard";
import MetricGrid from "../../../components/ui/MetricGrid";
import Panel from "../../../components/ui/Panel";
import ProductIdentity from "../../../components/ui/ProductIdentity";
import StatusBadge from "../../../components/ui/StatusBadge";
import { obterProdutosVendidosGrupo } from "../../../services/gruposEmpresas";
import { formatMoneyBRL } from "../../../utils/formatters";
import GrupoAnaliseFiltros from "./GrupoAnaliseFiltros";

function rotuloVinculo(tipo) {
  if (tipo === "manual") return ["Vínculo confirmado", "purple"];
  if (tipo === "ean") return ["Mesmo EAN", "success"];
  return ["Produto isolado", "neutral"];
}

export default function GrupoProdutosVendidosTab({ grupoId, periodoDias }) {
  const [busca, setBusca] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      setDados(
        await obterProdutosVendidosGrupo(grupoId, {
          periodo_dias: periodoDias,
          busca: buscaAplicada || undefined,
        }),
      );
    } catch (error) {
      toast.error(
        error?.response?.data?.detail || "Não foi possível carregar os produtos vendidos.",
      );
    } finally {
      setCarregando(false);
    }
  }, [buscaAplicada, grupoId, periodoDias]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const resumo = dados?.resumo || {};
  const itens = dados?.itens || [];

  return (
    <div className="space-y-4">
      <GrupoAnaliseFiltros
        busca={busca}
        carregando={carregando}
        empresas={[]}
        onBuscaChange={setBusca}
        onSubmit={(event) => {
          event.preventDefault();
          setBuscaAplicada(busca.trim());
        }}
        placeholder="Buscar por nome, SKU, código de barras ou empresa"
      />

      <MetricGrid>
        <MetricCard
          icon={<FiLayers />}
          intent="blue"
          size="compact"
          label="Produtos consolidados"
          value={resumo.produtos || 0}
        />
        <MetricCard
          icon={<FiShoppingCart />}
          intent="violet"
          size="compact"
          label="Quantidade vendida"
          value={Number(resumo.quantidade || 0).toLocaleString("pt-BR")}
        />
        <MetricCard
          icon={<FiDollarSign />}
          intent="emerald"
          size="compact"
          label="Receita dos produtos"
          value={formatMoneyBRL(resumo.valor_total || 0)}
        />
        <MetricCard
          icon={<FiBox />}
          intent="slate"
          size="compact"
          label="Estoque atual do grupo"
          value={Number(resumo.estoque_grupo || 0).toLocaleString("pt-BR")}
        />
      </MetricGrid>

      {itens.length === 0 && !carregando ? (
        <EmptyState
          icon={FiBox}
          title="Nenhum produto vendido encontrado"
          description="Pesquise por outro SKU ou aumente o período da análise."
        />
      ) : (
        <Panel
          title="Produtos vendidos no grupo"
          subtitle="Itens equivalentes são somados pelo EAN ou pelo vínculo confirmado entre as empresas."
          padding="none"
        >
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-700">
              <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:bg-slate-800 dark:text-slate-300">
                <tr>
                  <th className="px-4 py-3">Produto consolidado</th>
                  <th className="px-4 py-3">Empresas / cadastros</th>
                  <th className="px-4 py-3 text-right">Pedidos</th>
                  <th className="px-4 py-3 text-right">Quantidade</th>
                  <th className="px-4 py-3 text-right">Receita</th>
                  <th className="px-4 py-3 text-right">Estoque / cobertura</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {itens.map((item, index) => {
                  const [vinculoLabel, vinculoIntent] = rotuloVinculo(item.tipo_vinculo);
                  return (
                    <tr key={`${item.sku || item.produto_nome}-${index}`}>
                      <td className="px-4 py-3 align-top">
                        <ProductIdentity
                          name={item.produto_nome}
                          code={item.sku}
                          nameClassName="font-semibold text-slate-900 dark:text-slate-100"
                        >
                          <StatusBadge intent={vinculoIntent}>{vinculoLabel}</StatusBadge>
                        </ProductIdentity>
                        {item.ean ? (
                          <div className="mt-1 text-xs text-slate-500">EAN {item.ean}</div>
                        ) : null}
                      </td>
                      <td className="px-4 py-3 align-top">
                        <div className="space-y-1.5">
                          {item.empresas.map((produto) => (
                            <div
                              key={`${produto.empresa_id}-${produto.produto_id}`}
                              className="rounded-md bg-slate-50 px-2 py-1 text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-200"
                            >
                              <span className="font-semibold">{produto.empresa_nome}</span>
                              {" · "}
                              {produto.sku || "sem SKU"} · {produto.quantidade} vendidos
                            </div>
                          ))}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right font-medium">{item.pedidos}</td>
                      <td className="px-4 py-3 text-right">
                        <div className="font-semibold">{item.quantidade}</div>
                        <div className="text-xs text-slate-500">
                          média {formatMoneyBRL(item.preco_medio)}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-emerald-700 dark:text-emerald-300">
                        {formatMoneyBRL(item.valor_total)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="font-semibold">{item.estoque_grupo}</div>
                        <div className="text-xs text-slate-500">
                          {item.cobertura_dias == null
                            ? "sem consumo médio"
                            : `${item.cobertura_dias} dias de cobertura`}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Panel>
      )}
    </div>
  );
}
