import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiAlertTriangle, FiBox, FiDollarSign, FiRepeat, FiShoppingCart } from "react-icons/fi";
import { useNavigate } from "react-router-dom";
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
  const navigate = useNavigate();
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
  const acoes = dados?.acoes_empresa_atual || {};
  const transferencias = acoes.transferencias || [];
  const compras = acoes.compras || [];
  const comprasSemFornecedor = acoes.compras_sem_fornecedor || [];
  const pendenciasOutrasEmpresas = acoes.pendencias_outras_empresas || {};
  const totalPendenciasOutras =
    Number(pendenciasOutrasEmpresas.transferencias || 0) +
    Number(pendenciasOutrasEmpresas.compras || 0);

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

      {!carregando &&
      (transferencias.length ||
        compras.length ||
        comprasSemFornecedor.length ||
        totalPendenciasOutras) ? (
        <Panel
          title="Ações para esta empresa"
          subtitle="Os botões apenas preparam os dados. A movimentação ou o pedido só acontece depois da sua revisão na tela original."
        >
          <div className="grid gap-3 lg:grid-cols-2">
            {transferencias.map((plano) => (
              <div
                key={`transferencia-${plano.empresa_destino_id}`}
                className="rounded-xl border border-cyan-200 bg-cyan-50/70 p-4 dark:border-cyan-500/30 dark:bg-cyan-500/10"
              >
                <div className="flex items-start gap-3">
                  <FiRepeat className="mt-0.5 shrink-0 text-cyan-700 dark:text-cyan-300" />
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold text-slate-900 dark:text-white">
                      Transferir para {plano.empresa_destino_nome}
                    </div>
                    <div className="mt-1 text-xs text-slate-600 dark:text-slate-300">
                      {plano.itens.length} produto(s) · {formatarQuantidade(plano.quantidade_total)}{" "}
                      unidade(s) · {formatMoneyBRL(plano.valor_total)}
                    </div>
                    <ActionButton
                      className="mt-3"
                      icon={FiRepeat}
                      intent="info"
                      onClick={() =>
                        navigate("/estoque/transferencia-parceiro", {
                          state: { reposicaoGrupoTransferencia: plano },
                        })
                      }
                    >
                      Preparar transferência
                    </ActionButton>
                  </div>
                </div>
              </div>
            ))}

            {compras.map((plano) => (
              <div
                key={`compra-${plano.fornecedor_id}`}
                className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-4 dark:border-emerald-500/30 dark:bg-emerald-500/10"
              >
                <div className="flex items-start gap-3">
                  <FiShoppingCart className="mt-0.5 shrink-0 text-emerald-700 dark:text-emerald-300" />
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold text-slate-900 dark:text-white">
                      Comprar de {plano.fornecedor_nome}
                    </div>
                    <div className="mt-1 text-xs text-slate-600 dark:text-slate-300">
                      {plano.itens.length} produto(s) · {formatarQuantidade(plano.quantidade_total)}{" "}
                      unidade(s) · {formatMoneyBRL(plano.valor_total)}
                    </div>
                    <ActionButton
                      className="mt-3"
                      icon={FiShoppingCart}
                      intent="create"
                      onClick={() =>
                        navigate("/compras/pedidos", {
                          state: { reposicaoGrupoPedido: plano },
                        })
                      }
                    >
                      Montar pedido
                    </ActionButton>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {comprasSemFornecedor.length ? (
            <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100">
              {comprasSemFornecedor.length} produto(s) precisam de fornecedor no cadastro antes de
              montar o pedido.
            </div>
          ) : null}

          {totalPendenciasOutras ? (
            <div className="mt-3 text-xs text-slate-500 dark:text-slate-400">
              Existem {totalPendenciasOutras} ação(ões) sob responsabilidade de outras empresas do
              grupo. Elas poderão prepará-las ao acessar esta análise.
            </div>
          ) : null}
        </Panel>
      ) : null}

      {itens.length === 0 && !carregando ? (
        <EmptyState
          icon={FiBox}
          title="Nenhuma reposição necessária"
          description="O estoque consolidado atende à cobertura escolhida ou nenhum produto corresponde à busca."
        />
      ) : (
        <Panel
          title="Plano inteligente do grupo"
          subtitle="A análise não movimenta estoque nem cria pedidos automaticamente; use as ações acima para preparar e revisar cada operação."
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
                            {item.quantidade_compra_sugerida > 0
                              ? "Sem sobra interna suficiente"
                              : "Nenhuma transferência necessária"}
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
