import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { CheckCircle2, ExternalLink, Receipt, RefreshCw, RotateCw } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
import EmptyState from "../../../components/ui/EmptyState";
import MetricCard from "../../../components/ui/MetricCard";
import MetricGrid from "../../../components/ui/MetricGrid";
import Panel from "../../../components/ui/Panel";
import { formatMoneyBRL } from "../../../utils/formatters";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage } from "../banhoTosaUtils";

export default function BanhoTosaFechamentosView({ onChanged }) {
  const [pendencias, setPendencias] = useState([]);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState("");

  useEffect(() => {
    carregar();
  }, []);

  async function carregar() {
    setLoading(true);
    try {
      const response = await banhoTosaApi.listarPendenciasFechamento({ limit: 300 });
      setPendencias(Array.isArray(response.data?.itens) ? response.data.itens : []);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Não foi possível carregar os fechamentos."));
      setPendencias([]);
    } finally {
      setLoading(false);
    }
  }

  async function executar(chave, operacao, mensagem) {
    setProcessing(chave);
    try {
      const response = await operacao();
      toast.success(mensagem);
      await carregar();
      await onChanged?.(true);
      return response;
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Não foi possível concluir a operação."));
      return null;
    } finally {
      setProcessing("");
    }
  }

  async function gerarVenda(item) {
    const response = await executar(
      `venda-${item.atendimento_id}`,
      () => banhoTosaApi.gerarVendaAtendimento(item.atendimento_id),
      "Cobrança gerada no PDV.",
    );
    if (response?.data?.pdv_url) {
      window.open(response.data.pdv_url, "_blank", "noopener,noreferrer");
    }
  }

  async function entregar(item) {
    const confirmou = window.confirm(
      `Confirmar a entrega de ${item.pet_nome || "este pet"} e encerrar o atendimento?`,
    );
    if (!confirmou) return;
    await executar(
      `entrega-${item.atendimento_id}`,
      () =>
        banhoTosaApi.moverEtapaAtendimento(item.atendimento_id, {
          tipo: "entregue",
          iniciar_timer: false,
        }),
      "Entrega confirmada.",
    );
  }

  const semVenda = pendencias.filter((item) => !item.venda_id).length;
  const cobrancaAberta = pendencias.filter((item) =>
    ["pendente", "parcial"].includes(item.status_pagamento),
  ).length;

  return (
    <div className="space-y-4">
      <Panel
        actions={
          <>
            <ActionButton
              icon={RotateCw}
              intent="info"
              loading={processing === "sincronizar-todos"}
              tone="soft"
              onClick={() =>
                executar(
                  "sincronizar-todos",
                  () => banhoTosaApi.sincronizarPendenciasFechamento({ limit: 300 }),
                  "Pendências sincronizadas.",
                )
              }
            >
              Sincronizar todos
            </ActionButton>
            <ActionButton
              icon={RefreshCw}
              intent="neutral"
              loading={loading}
              tone="soft"
              onClick={carregar}
            >
              Atualizar
            </ActionButton>
          </>
        }
        subtitle="Centralize cobrança, conferência financeira e entrega sem perder atendimentos prontos."
        title="Fechamentos"
      >
        <MetricGrid>
          <MetricCard intent="amber" label="Pendências" value={pendencias.length} />
          <MetricCard intent="red" label="Sem venda" value={semVenda} />
          <MetricCard intent="blue" label="Cobrança aberta" value={cobrancaAberta} />
        </MetricGrid>
      </Panel>

      {loading && !pendencias.length ? (
        <Panel className="p-8 text-center text-sm text-slate-500">Carregando...</Panel>
      ) : pendencias.length ? (
        <div className="grid gap-3 xl:grid-cols-2">
          {pendencias.map((item) => (
            <Panel key={item.atendimento_id} padding="sm">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">
                    Atendimento #{item.atendimento_id}
                  </p>
                  <h3 className="mt-1 text-lg font-semibold text-slate-950">
                    {item.pet_nome || `Pet #${item.pet_id}`}
                  </h3>
                  <p className="text-sm text-slate-500">
                    Tutor: {item.cliente_nome || `#${item.cliente_id}`}
                  </p>
                </div>
                <span className="w-fit rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
                  {item.status_atendimento === "pronto" ? "Pronto" : "Entregue"}
                </span>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-2 rounded-lg bg-slate-50 p-3 text-sm">
                <div>
                  <p className="text-xs text-slate-500">Total</p>
                  <p className="font-semibold text-slate-900">{formatMoneyBRL(item.total)}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-slate-500">Restante</p>
                  <p className="font-semibold text-slate-900">
                    {formatMoneyBRL(item.valor_restante)}
                  </p>
                </div>
              </div>

              {item.alertas?.length ? (
                <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs font-medium text-amber-800">
                  {item.alertas.map((alerta) => (
                    <p key={alerta}>{alerta}</p>
                  ))}
                </div>
              ) : null}

              <div className="mt-4 flex flex-wrap gap-2">
                {!item.venda_id ? (
                  <ActionButton
                    icon={Receipt}
                    intent="create"
                    loading={processing === `venda-${item.atendimento_id}`}
                    onClick={() => gerarVenda(item)}
                  >
                    Gerar cobrança
                  </ActionButton>
                ) : (
                  <>
                    <ActionButton
                      icon={ExternalLink}
                      intent="info"
                      onClick={() => window.open(item.pdv_url, "_blank", "noopener,noreferrer")}
                    >
                      Abrir PDV
                    </ActionButton>
                    <ActionButton
                      icon={RotateCw}
                      intent="neutral"
                      loading={processing === `sync-${item.atendimento_id}`}
                      tone="soft"
                      onClick={() =>
                        executar(
                          `sync-${item.atendimento_id}`,
                          () => banhoTosaApi.sincronizarFechamentoAtendimento(item.atendimento_id),
                          "Fechamento sincronizado.",
                        )
                      }
                    >
                      Sincronizar
                    </ActionButton>
                  </>
                )}
                {item.status_atendimento === "pronto" && (
                  <ActionButton
                    disabled={!item.venda_id}
                    icon={CheckCircle2}
                    intent="create"
                    loading={processing === `entrega-${item.atendimento_id}`}
                    tone="soft"
                    onClick={() => entregar(item)}
                  >
                    Confirmar entrega
                  </ActionButton>
                )}
              </div>
            </Panel>
          ))}
        </div>
      ) : (
        <EmptyState
          description="Os atendimentos prontos estão com cobrança e financeiro em dia."
          title="Nenhum fechamento pendente"
        />
      )}
    </div>
  );
}
