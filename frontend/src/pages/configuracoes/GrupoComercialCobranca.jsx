import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiExternalLink, FiRefreshCw } from "react-icons/fi";
import ActionButton from "../../components/ui/ActionButton";
import EmptyState from "../../components/ui/EmptyState";
import LoadingState from "../../components/ui/LoadingState";
import StatusBadge from "../../components/ui/StatusBadge";
import { listarBillingGrupo, sincronizarBillingLojaGrupo } from "../../services/gruposComerciais";

function mensagemErro(error, padrao) {
  return error?.response?.data?.detail || padrao;
}

const STATUS_COBRANCA = {
  active: { label: "Adimplente", intent: "success" },
  trial: { label: "Em teste", intent: "info" },
  pending: { label: "Pendente", intent: "warning" },
  past_due: { label: "Inadimplente", intent: "danger" },
  blocked: { label: "Bloqueada", intent: "danger" },
  refunded: { label: "Estornada", intent: "neutral" },
  canceled: { label: "Cancelada", intent: "neutral" },
};

const TIPO_COBRANCA = {
  BOLETO: "Boleto",
  PIX: "Pix",
  UNDEFINED: "Não definido",
};

function formatarData(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("pt-BR").format(new Date(`${value}T00:00:00`));
}

export default function GrupoComercialCobranca({ grupoId }) {
  const [lojas, setLojas] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [sincronizando, setSincronizando] = useState("");

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const data = await listarBillingGrupo(grupoId);
      setLojas(data.lojas);
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível carregar a cobrança das lojas."));
    } finally {
      setCarregando(false);
    }
  }, [grupoId]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  async function sincronizar(tenantId) {
    setSincronizando(tenantId);
    try {
      const atualizada = await sincronizarBillingLojaGrupo(grupoId, tenantId);
      setLojas((atual) =>
        atual.map((loja) => (loja.tenant_id === tenantId ? atualizada : loja)),
      );
      toast.success("Cobrança atualizada.");
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível atualizar a cobrança desta loja."));
    } finally {
      setSincronizando("");
    }
  }

  if (carregando) {
    return <LoadingState label="Carregando cobrança das lojas..." />;
  }

  if (lojas.length === 0) {
    return (
      <EmptyState
        title="Nenhuma loja para mostrar"
        description="As lojas do grupo aparecem aqui assim que tiverem cobrança configurada."
      />
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500">
        Cada loja continua sendo cobrada separadamente — esta lista só reúne a situação de
        cada uma num lugar só.
      </p>
      <div className="divide-y divide-slate-100 rounded-lg border border-slate-200">
        {lojas.map((loja) => {
          const status = STATUS_COBRANCA[loja.billing_status] || {
            label: loja.billing_status || "Sem informação",
            intent: "neutral",
          };
          return (
            <div
              key={loja.tenant_id}
              className="flex flex-col gap-3 px-3 py-3 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-slate-900">{loja.nome}</span>
                  <StatusBadge intent={status.intent}>{status.label}</StatusBadge>
                </div>
                <div className="mt-0.5 text-xs text-slate-500">
                  {TIPO_COBRANCA[loja.billing_type] || "Não definido"} · Próxima cobrança:{" "}
                  {formatarData(loja.next_due_date)}
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {loja.checkout_url ? (
                  <a
                    href={loja.checkout_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700"
                  >
                    <FiExternalLink aria-hidden="true" />
                    Ver boleto/fatura
                  </a>
                ) : null}
                <ActionButton
                  icon={FiRefreshCw}
                  intent="info"
                  tone="outline"
                  size="sm"
                  loading={sincronizando === loja.tenant_id}
                  onClick={() => sincronizar(loja.tenant_id)}
                >
                  Sincronizar
                </ActionButton>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
