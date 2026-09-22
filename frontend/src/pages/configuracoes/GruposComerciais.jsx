import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { MessageCircle } from "lucide-react";
import {
  FiAlertTriangle,
  FiCheckCircle,
  FiChevronLeft,
  FiGrid,
  FiLink,
  FiTrash2,
  FiUsers,
} from "react-icons/fi";
import ActionButton from "../../components/ui/ActionButton";
import EmptyState from "../../components/ui/EmptyState";
import LoadingState from "../../components/ui/LoadingState";
import PageHeader from "../../components/ui/PageHeader";
import Panel from "../../components/ui/Panel";
import StatusBadge from "../../components/ui/StatusBadge";
import LinkPadrao from "../../components/v2/LinkPadrao/LinkPadrao";
import {
  listarBillingGrupo,
  obterResumoGruposComerciais,
  removerEmpresaGrupo,
  sincronizarBillingLojaGrupo,
} from "../../services/gruposComerciais";
import { confirmarCorePet } from "../../services/corepetDialog";
import { buildSalesContactUrl } from "../../data/publicPlans";
import EstoqueCompartilhadoGrupo from "./EstoqueCompartilhadoGrupo";

const resumoVazio = {
  empresa_atual_id: null,
  grupos: [],
  tem_grupo_sem_acesso: false,
};

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

// Só faz sentido oferecer "verificar pendência" quando existe, de fato, algo em
// aberto pra checar — nos demais status (em dia, em teste, encerrada) não há
// boleto pendente algum pra rebuscar no Asaas.
const STATUS_COM_PENDENCIA = new Set(["pending", "past_due", "blocked"]);

function mensagemErro(error, padrao) {
  return error?.response?.data?.detail || padrao;
}

function formatarData(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("pt-BR").format(new Date(`${value}T00:00:00`));
}

function GrupoComercialPainel({ acao, empresaAtualId, grupo, navigate, onRemover }) {
  const [billingPorEmpresa, setBillingPorEmpresa] = useState({});
  const [carregandoBilling, setCarregandoBilling] = useState(true);
  const [sincronizando, setSincronizando] = useState("");

  useEffect(() => {
    let ativo = true;
    setCarregandoBilling(true);
    listarBillingGrupo(grupo.id)
      .then((data) => {
        if (!ativo) return;
        const mapa = {};
        (data.lojas || []).forEach((loja) => {
          mapa[loja.tenant_id] = loja;
        });
        setBillingPorEmpresa(mapa);
      })
      .catch((error) => {
        toast.error(mensagemErro(error, "Não foi possível carregar a cobrança das lojas."));
      })
      .finally(() => {
        if (ativo) setCarregandoBilling(false);
      });
    return () => {
      ativo = false;
    };
  }, [grupo.id]);

  async function sincronizar(tenantId) {
    setSincronizando(tenantId);
    try {
      const atualizada = await sincronizarBillingLojaGrupo(grupo.id, tenantId);
      setBillingPorEmpresa((atual) => ({ ...atual, [tenantId]: atualizada }));
      toast.success("Cobrança atualizada.");
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível atualizar a cobrança desta loja."));
    } finally {
      setSincronizando("");
    }
  }

  return (
    <Panel
      title={grupo.nome}
      actions={
        <ActionButton
          icon={FiGrid}
          intent="success"
          tone="outline"
          onClick={() => navigate(`/configuracoes/grupos-comerciais/${grupo.id}/mestres`)}
        >
          Dados compartilhados
        </ActionButton>
      }
    >
      <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-5">
        <div className="flex items-center gap-3">
          <div className="flex-none rounded-md bg-emerald-100 p-2 text-emerald-700">
            <MessageCircle className="h-5 w-5" aria-hidden="true" />
          </div>
          <h3 className="text-sm font-bold text-emerald-900">Adicionar nova loja ao grupo</h3>
        </div>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-emerald-900">
          Nossa equipe cuida da configuração da loja nova com você — funcionalidades, ajustes da
          operação e integração com as demais lojas do grupo, tudo já pronto pra usar desde o
          primeiro dia.
        </p>
        <div className="mt-4">
          <LinkPadrao
            href={buildSalesContactUrl(
              `Olá! Quero adicionar uma nova loja ao grupo "${grupo.nome}" no CorePet.`,
            )}
            novaJanela
            tamanho="text-sm font-bold"
          >
            Falar com a equipe sobre uma nova loja
          </LinkPadrao>
        </div>
      </div>

      <div className="mt-5">
        <h3 className="text-sm font-semibold text-slate-800">Lojas participantes</h3>
        <div className="mt-2 divide-y divide-slate-100 rounded-lg border border-slate-200">
          {grupo.membros.map((membro) => {
            const billing = billingPorEmpresa[membro.empresa_id];
            const status = billing
              ? STATUS_COBRANCA[billing.billing_status] || {
                  label: billing.billing_status || "Sem informação",
                  intent: "neutral",
                }
              : null;

            return (
              <div
                key={membro.empresa_id}
                className="flex flex-col gap-3 px-3 py-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-slate-900">
                      {membro.empresa_nome}
                    </span>
                    <span className="text-xs text-slate-500">
                      {membro.papel === "responsavel" ? "Loja responsável" : "Loja do grupo"}
                    </span>
                    {status ? <StatusBadge intent={status.intent}>{status.label}</StatusBadge> : null}
                  </div>
                  <div className="mt-0.5 text-xs text-slate-500">
                    {carregandoBilling
                      ? "Carregando cobrança..."
                      : billing
                        ? `${TIPO_COBRANCA[billing.billing_type] || "Não definido"} · Próxima cobrança: ${formatarData(billing.next_due_date)}`
                        : "Cobrança não disponível"}
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {billing?.checkout_url ? (
                    <LinkPadrao href={billing.checkout_url} novaJanela tamanho="text-sm">
                      Ver boleto/fatura
                    </LinkPadrao>
                  ) : null}
                  {billing && STATUS_COM_PENDENCIA.has(billing.billing_status) ? (
                    <ActionButton
                      icon={FiAlertTriangle}
                      intent="warning"
                      tone="outline"
                      size="sm"
                      title="Busca o boleto/fatura mais recente desta loja direto no Asaas"
                      loading={sincronizando === membro.empresa_id}
                      onClick={() => sincronizar(membro.empresa_id)}
                    >
                      Verificar pendência financeira
                    </ActionButton>
                  ) : billing?.billing_status === "active" ? (
                    <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-700">
                      <FiCheckCircle aria-hidden="true" />
                      Pagamento em dia
                    </span>
                  ) : null}
                  {membro.papel !== "responsavel" ? (
                    <ActionButton
                      icon={FiTrash2}
                      intent="danger"
                      tone="ghost"
                      size="xs"
                      loading={acao === `remover-${grupo.id}-${membro.empresa_id}`}
                      onClick={() => onRemover(grupo, membro)}
                    >
                      Remover
                    </ActionButton>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <EstoqueCompartilhadoGrupo empresaAtualId={empresaAtualId} grupo={grupo} />
    </Panel>
  );
}

export default function GruposComerciais() {
  const navigate = useNavigate();
  const [resumo, setResumo] = useState(resumoVazio);
  const [carregando, setCarregando] = useState(true);
  const [acao, setAcao] = useState("");

  const carregar = useCallback(async () => {
    try {
      setResumo(await obterResumoGruposComerciais());
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível carregar seu grupo comercial."));
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  async function executar(chave, operacao, sucesso) {
    setAcao(chave);
    try {
      await operacao();
      toast.success(sucesso);
      await carregar();
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível concluir esta ação."));
    } finally {
      setAcao("");
    }
  }

  async function handleRemover(grupo, membro) {
    if (!(await confirmarCorePet(`Remover ${membro.empresa_nome} do grupo ${grupo.nome}?`))) {
      return;
    }
    executar(
      `remover-${grupo.id}-${membro.empresa_id}`,
      () => removerEmpresaGrupo(grupo.id, membro.empresa_id),
      "Loja removida do grupo.",
    );
  }

  if (carregando) {
    return <LoadingState label="Carregando seu grupo comercial..." />;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <Link
        to="/configuracoes"
        className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700"
      >
        <FiChevronLeft aria-hidden="true" />
        Voltar para Configurações
      </Link>

      <PageHeader
        icon={FiUsers}
        title="Grupos Comerciais"
        subtitle="Veja as lojas do seu grupo, os dados compartilhados entre elas e a situação de cobrança de cada uma."
      />

      <div className="space-y-4">
        {resumo.grupos.length === 0 ? (
          <EmptyState
            icon={FiLink}
            title={
              resumo.tem_grupo_sem_acesso
                ? "Só o usuário master deste grupo vê esta tela"
                : "Nenhum grupo encontrado"
            }
            description={
              resumo.tem_grupo_sem_acesso
                ? "Fale com o usuário master do seu grupo comercial, ou com a equipe CorePet, se precisar de algo aqui."
                : "Fale com o suporte se você acredita que sua loja deveria ter um grupo comercial."
            }
          />
        ) : (
          resumo.grupos.map((grupo) => (
            <GrupoComercialPainel
              key={grupo.id}
              acao={acao}
              empresaAtualId={resumo.empresa_atual_id}
              grupo={grupo}
              navigate={navigate}
              onRemover={handleRemover}
            />
          ))
        )}
      </div>
    </div>
  );
}
