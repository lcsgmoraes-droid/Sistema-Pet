import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiAlertTriangle, FiBox, FiDollarSign, FiRepeat, FiShoppingCart } from "react-icons/fi";
import ActionButton from "../../../components/ui/ActionButton";
import EmptyState from "../../../components/ui/EmptyState";
import MetricCard from "../../../components/ui/MetricCard";
import MetricGrid from "../../../components/ui/MetricGrid";
import Panel from "../../../components/ui/Panel";
import ProductIdentity from "../../../components/ui/ProductIdentity";
import StatusBadge from "../../../components/ui/StatusBadge";
import { obterReposicaoInteligenteGrupo } from "../../../services/gruposEmpresas";
import { formatMoneyBRL } from "../../../utils/formatters";
import GrupoAnaliseFiltros from "./GrupoAnaliseFiltros";

const COBERTURAS = [15, 30, 45, 60, 90];

const PRIORIDADES = {
  critico: ["Crítico", "danger"],
  alerta: ["Comprar", "warning"],
  atencao: ["Transferir", "info"],
  normal: ["Adequado", "success"],
};

function formatarQuantidade(valor) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  });
}

export default function GrupoReposicaoInteligenteTab({ grupoId, periodoDias }) {
  const [busca, setBusca] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");
  const [diasCobertura, setDiasCobertura] = useState(30);
  const [somenteAcao, setSomenteAcao] = useState(true);
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      setDados(
        await obterReposicaoInteligenteGrupo(grupoId, {
          periodo_dias: periodoDias,
          dias_cobertura: diasCobertura,
          busca: buscaAplicada || undefined,
          somente_acao: somenteAcao,
        }),
      );
    } catch (error) {
      toast.error(
        error?.response?.data?.detail || "Não foi possível calcular a reposição do grupo.",
      );
    } finally {
      setCarregando(false);
    }
  }, [buscaAplicada, diasCobertura, grupoId, periodoDias, somenteAcao]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const resumo = dados?.resumo || {};
  const itens = dados?.itens || [];

  return (
    <div className="space-y-4">
      <Panel
        title="Objetivo da reposição"
        subtitle="O CorePet procura primeiro estoque que pode ser transferido entre as empresas e sugere comprar apenas o déficit restante."
      >
        <div className="flex flex-wrap items-center gap-2">
          {COBERTURAS.map((dias) => (
            <ActionButton
              key={dias}
              intent={diasCobertura === dias ? "info" : "neutral"}
              tone={diasCobertura === dias ? "solid" : "soft"}
              disabled={carregando}
              onClick={() => setDiasCobertura(dias)}
            >
              {dias} dias de cobertura
            </ActionButton>
          ))}
          <ActionButton
            className="ml-auto"
            intent={somenteAcao ? "warning" : "neutral"}
            tone="soft"
            disabled={carregando}
            onClick={() => setSomenteAcao((valor) => !valor)}
          >
            {somenteAcao ? "Somente com ação" : "Mostrar todos"}
          </ActionButton>
        </div>
      </Panel>

      <GrupoAnaliseFiltros
        busca={busca}
        carregando={carregando}
        empresas={[]}
        onBuscaChange={setBusca}
        onSubmit={(event) => {
          event.preventDefault();
          setBuscaAplicada(busca.trim());
        }}
        placeholder="Buscar produto, SKU, EAN ou empresa"
      />

      <MetricGrid>
        <MetricCard
          icon={<FiAlertTriangle />}
          intent="blue"
          size="compact"
          label="Produtos com ação"
          value={resumo.produtos_com_acao || 0}
          subtitle={`${resumo.produtos_analisados || 0} produtos analisados`}
        />
        <MetricCard
          icon={<FiShoppingCart />}
          intent="red"
          size="compact"
          label="Produtos para comprar"
          value={resumo.produtos_para_comprar || 0}
          subtitle={`${formatarQuantidade(resumo.quantidade_compra_sugerida)} unidades`}
        />
        <MetricCard
          icon={<FiRepeat />}
          intent="cyan"
          size="compact"
          label="Transferências possíveis"
          value={resumo.produtos_para_transferir || 0}
          subtitle="Antes de comprar de fornecedor"
        />
        <MetricCard
          icon={<FiDollarSign />}
          intent="emerald"
          size="compact"
          label="Compra estimada"
          value={formatMoneyBRL(resumo.valor_compra_estimado || 0)}
          subtitle="Pelo custo médio cadastrado"
        />
      </MetricGrid>

      {itens.length === 0 && !carregando ? (
        <EmptyState
          icon={FiBox}
          title="Nenhuma reposição necessária"
          description="O estoque consolidado atende à cobertura escolhida ou nenhum produto corresponde à busca."
        />
      ) : (
        <Panel
          title="Plano inteligente do grupo"
          subtitle="A sugestão é uma simulação de leitura e não movimenta estoque nem cria pedidos automaticamente."
          padding="none"
        >
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-700">
              <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:bg-slate-800 dark:text-slate-300">
                <tr>
                  <th className="px-4 py-3">Produto</th>
                  <th className="px-4 py-3">Posição por empresa</th>
                  <th className="px-4 py-3">Transferir antes de comprar</th>
                  <th className="px-4 py-3 text-right">Comprar</th>
                  <th className="px-4 py-3 text-right">Estimativa</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {itens.map((item, index) => {
                  const [prioridade, intent] = PRIORIDADES[item.prioridade] || [
                    item.prioridade,
                    "neutral",
                  ];
                  return (
                    <tr key={`${item.sku || item.produto_nome}-${index}`}>
                      <td className="px-4 py-3 align-top">
                        <ProductIdentity name={item.produto_nome} code={item.sku}>
                          <StatusBadge intent={intent}>{prioridade}</StatusBadge>
                        </ProductIdentity>
                        <div className="mt-1 text-xs text-slate-500">
                          {formatarQuantidade(item.quantidade_vendida)} vendidos · estoque{" "}
                          {formatarQuantidade(item.estoque_grupo)} · cobertura{" "}
                          {item.cobertura_dias == null
                            ? "sem giro"
                            : `${formatarQuantidade(item.cobertura_dias)} dias`}
                        </div>
                      </td>
                      <td className="px-4 py-3 align-top">
                        <div className="space-y-1.5">
                          {item.empresas.map((empresa) => (
                            <div
                              key={`${empresa.empresa_id}-${empresa.produto_id}`}
                              className="rounded-md bg-slate-50 px-2 py-1 text-xs dark:bg-slate-800"
                            >
                              <span className="font-semibold">{empresa.empresa_nome}</span>
                              {" · estoque "}
                              {formatarQuantidade(empresa.estoque)} · alvo{" "}
                              {formatarQuantidade(empresa.estoque_alvo)}
                              {empresa.compra_sugerida > 0
                                ? ` · comprar ${formatarQuantidade(empresa.compra_sugerida)}`
                                : ""}
                            </div>
                          ))}
                        </div>
                      </td>
                      <td className="px-4 py-3 align-top">
                        {item.transferencias_sugeridas.length ? (
                          <div className="space-y-1.5">
                            {item.transferencias_sugeridas.map((transferencia, posicao) => (
                              <div
                                key={`${transferencia.empresa_origem_id}-${transferencia.empresa_destino_id}-${posicao}`}
                                className="rounded-md bg-cyan-50 px-2 py-1.5 text-xs text-cyan-900 dark:bg-cyan-500/10 dark:text-cyan-100"
                              >
                                <strong>{transferencia.empresa_origem_nome}</strong> →{" "}
                                <strong>{transferencia.empresa_destino_nome}</strong>:{" "}
                                {formatarQuantidade(transferencia.quantidade)}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <span className="text-xs text-slate-500">
                            Sem sobra interna suficiente
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right align-top font-semibold text-red-700 dark:text-red-300">
                        {formatarQuantidade(item.quantidade_compra_sugerida)}
                      </td>
                      <td className="px-4 py-3 text-right align-top">
                        <div className="font-semibold">
                          {formatMoneyBRL(item.valor_compra_estimado)}
                        </div>
                        <div className="text-xs text-slate-500">
                          custo médio {formatMoneyBRL(item.custo_medio)}
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
