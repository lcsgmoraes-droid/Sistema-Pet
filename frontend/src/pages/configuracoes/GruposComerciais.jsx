import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import {
  FiCheck,
  FiBarChart2,
  FiChevronLeft,
  FiCopy,
  FiGrid,
  FiLink,
  FiPlusCircle,
  FiTrash2,
  FiUsers,
  FiX,
} from "react-icons/fi";
import ActionButton from "../../components/ui/ActionButton";
import EmptyState from "../../components/ui/EmptyState";
import LoadingState from "../../components/ui/LoadingState";
import PageHeader from "../../components/ui/PageHeader";
import Panel from "../../components/ui/Panel";
import StatusBadge from "../../components/ui/StatusBadge";
import {
  adicionarLojaGrupo,
  convidarEmpresa,
  obterResumoGruposComerciais,
  removerEmpresaGrupo,
  responderConviteGrupo,
} from "../../services/gruposComerciais";
import { confirmarCorePet } from "../../services/corepetDialog";
import { useAuth } from "../../contexts/AuthContext";
import EstoqueCompartilhadoGrupo from "./EstoqueCompartilhadoGrupo";

const resumoVazio = {
  codigo_empresa: null,
  convites_pendentes: [],
  grupos: [],
};

function mensagemErro(error, padrao) {
  return error?.response?.data?.detail || padrao;
}

function formatarData(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function GruposComerciais() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [resumo, setResumo] = useState(resumoVazio);
  const [carregando, setCarregando] = useState(true);
  const [acao, setAcao] = useState("");
  const [codigosConvite, setCodigosConvite] = useState({});
  const [novasLojas, setNovasLojas] = useState({});
  const permissoes = user?.permissions || [];
  const podeAnalisarGrupo =
    user?.role?.name?.toLowerCase() === "admin" ||
    ["relatorios.gerencial", "relatorios.financeiro"].some((permissao) =>
      permissoes.includes(permissao),
    );

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

  async function copiarCodigo() {
    const codigo = resumo.codigo_empresa?.codigo;
    if (!codigo) return;
    try {
      await navigator.clipboard.writeText(codigo);
      toast.success("Código da empresa copiado.");
    } catch {
      toast.error("Não foi possível copiar o código automaticamente.");
    }
  }

  function handleAdicionarLoja(event, grupoId) {
    event.preventDefault();
    const nomeLoja = (novasLojas[grupoId] || "").trim();
    if (nomeLoja.length < 2) {
      toast.error("Informe o nome da nova loja.");
      return;
    }
    executar(
      `adicionar-loja-${grupoId}`,
      async () => {
        await adicionarLojaGrupo(grupoId, { nomeLoja });
        setNovasLojas((atual) => ({ ...atual, [grupoId]: "" }));
      },
      "Loja criada e adicionada ao grupo.",
    );
  }

  function handleConvidar(event, grupoId) {
    event.preventDefault();
    const codigo = (codigosConvite[grupoId] || "").trim();
    if (!codigo) {
      toast.error("Informe o código mensal da empresa.");
      return;
    }
    executar(
      `convidar-${grupoId}`,
      async () => {
        await convidarEmpresa(grupoId, codigo);
        setCodigosConvite((atual) => ({ ...atual, [grupoId]: "" }));
      },
      "Convite enviado. A outra empresa precisa aceitar.",
    );
  }

  async function handleRemover(grupo, membro) {
    if (!(await confirmarCorePet(`Remover ${membro.empresa_nome} do grupo ${grupo.nome}?`))) {
      return;
    }
    executar(
      `remover-${grupo.id}-${membro.empresa_id}`,
      () => removerEmpresaGrupo(grupo.id, membro.empresa_id),
      "Empresa removida do grupo.",
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
        subtitle="Toda loja já nasce dentro de um grupo comercial. Adicione novas lojas suas direto aqui, ou convide outra empresa já existente para se juntar."
      />

      {resumo.convites_pendentes.length > 0 ? (
        <Panel
          title="Convites recebidos"
          subtitle="A entrada no grupo só acontece depois do seu aceite."
          className="border-amber-200 bg-amber-50/40"
        >
          <div className="space-y-3">
            {resumo.convites_pendentes.map((convite) => (
              <div
                key={convite.id}
                className="flex flex-col gap-3 rounded-lg border border-amber-200 bg-white p-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <div className="font-semibold text-slate-900">{convite.grupo_nome}</div>
                  <div className="mt-1 text-sm text-slate-600">
                    Convite enviado por {convite.empresa_origem_nome}. Expira em{" "}
                    {formatarData(convite.expira_em)}.
                  </div>
                </div>
                <div className="flex gap-2">
                  <ActionButton
                    icon={FiCheck}
                    intent="success"
                    loading={acao === `aceitar-${convite.id}`}
                    onClick={() =>
                      executar(
                        `aceitar-${convite.id}`,
                        () => responderConviteGrupo(convite.id, true),
                        "Convite aceito. Sua empresa entrou no grupo.",
                      )
                    }
                  >
                    Aceitar
                  </ActionButton>
                  <ActionButton
                    icon={FiX}
                    intent="danger"
                    tone="outline"
                    loading={acao === `recusar-${convite.id}`}
                    onClick={() =>
                      executar(
                        `recusar-${convite.id}`,
                        () => responderConviteGrupo(convite.id, false),
                        "Convite recusado.",
                      )
                    }
                  >
                    Recusar
                  </ActionButton>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      ) : null}

      <Panel
        title="Código mensal da sua empresa"
        subtitle="Compartilhe este código apenas com quem deve convidar sua empresa. Ele muda todo mês."
      >
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <code className="text-xl font-bold tracking-widest text-blue-900">
              {resumo.codigo_empresa?.codigo || "-"}
            </code>
            <ActionButton icon={FiCopy} intent="info" tone="outline" onClick={copiarCodigo}>
              Copiar
            </ActionButton>
          </div>
          <p className="mt-3 text-xs text-blue-800">
            Válido até {formatarData(resumo.codigo_empresa?.expira_em)}. O código identifica a
            empresa, mas não adiciona ninguém sem convite e aceite.
          </p>
        </div>
      </Panel>

      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Seu grupo comercial</h2>
          <p className="text-sm text-slate-500">
            Os dados continuam separados por loja; o grupo apenas autoriza os recursos
            consolidados escolhidos.
          </p>
        </div>

        {resumo.grupos.length === 0 ? (
          <EmptyState
            icon={FiLink}
            title="Nenhum grupo encontrado"
            description="Fale com o suporte se você acredita que sua loja deveria ter um grupo comercial."
          />
        ) : (
          resumo.grupos.map((grupo) => (
            <Panel
              key={grupo.id}
              title={grupo.nome}
              actions={
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge intent={grupo.papel === "responsavel" ? "purple" : "info"}>
                    {grupo.papel === "responsavel" ? "Responsável" : "Membro"}
                  </StatusBadge>
                  <ActionButton
                    icon={FiGrid}
                    intent="success"
                    tone="outline"
                    onClick={() => navigate(`/configuracoes/grupos-comerciais/${grupo.id}/mestres`)}
                  >
                    Dados compartilhados
                  </ActionButton>
                  {podeAnalisarGrupo ? (
                    <ActionButton
                      icon={FiBarChart2}
                      intent="info"
                      tone="outline"
                      onClick={() =>
                        navigate(`/configuracoes/grupos-comerciais/${grupo.id}/visao-consolidada`)
                      }
                    >
                      Ver visão consolidada
                    </ActionButton>
                  ) : null}
                </div>
              }
            >
              <div className="grid gap-5 lg:grid-cols-[1fr_0.9fr]">
                <div>
                  <h3 className="text-sm font-semibold text-slate-800">Empresas participantes</h3>
                  <div className="mt-2 divide-y divide-slate-100 rounded-lg border border-slate-200">
                    {grupo.membros.map((membro) => (
                      <div
                        key={membro.empresa_id}
                        className="flex items-center justify-between gap-3 px-3 py-2.5"
                      >
                        <div>
                          <div className="text-sm font-medium text-slate-900">
                            {membro.empresa_nome}
                          </div>
                          <div className="text-xs text-slate-500">
                            {membro.papel === "responsavel" ? "Empresa responsável" : "Membro"}
                          </div>
                        </div>
                        {grupo.papel === "responsavel" && membro.papel !== "responsavel" ? (
                          <ActionButton
                            icon={FiTrash2}
                            intent="danger"
                            tone="ghost"
                            size="xs"
                            loading={acao === `remover-${grupo.id}-${membro.empresa_id}`}
                            onClick={() => handleRemover(grupo, membro)}
                          >
                            Remover
                          </ActionButton>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>

                {grupo.papel === "responsavel" ? (
                  <div className="space-y-5">
                    <div>
                      <h3 className="text-sm font-semibold text-slate-800">
                        Adicionar nova loja ao grupo
                      </h3>
                      <p className="mt-1 text-xs text-slate-500">
                        Cria uma loja nova, com seu próprio login, já dentro deste grupo — sem
                        precisar de convite.
                      </p>
                      <form
                        className="mt-2 flex flex-col gap-2 sm:flex-row"
                        onSubmit={(event) => handleAdicionarLoja(event, grupo.id)}
                      >
                        <input
                          value={novasLojas[grupo.id] || ""}
                          onChange={(event) =>
                            setNovasLojas((atual) => ({
                              ...atual,
                              [grupo.id]: event.target.value,
                            }))
                          }
                          placeholder="Nome da nova loja"
                          maxLength={150}
                          className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                        />
                        <ActionButton
                          type="submit"
                          icon={FiPlusCircle}
                          intent="success"
                          loading={acao === `adicionar-loja-${grupo.id}`}
                        >
                          Adicionar loja
                        </ActionButton>
                      </form>
                    </div>

                    <div>
                      <h3 className="text-sm font-semibold text-slate-800">
                        Convidar empresa já existente
                      </h3>
                      <form
                        className="mt-2 flex flex-col gap-2 sm:flex-row"
                        onSubmit={(event) => handleConvidar(event, grupo.id)}
                      >
                        <input
                          value={codigosConvite[grupo.id] || ""}
                          onChange={(event) =>
                            setCodigosConvite((atual) => ({
                              ...atual,
                              [grupo.id]: event.target.value.toUpperCase(),
                            }))
                          }
                          placeholder="XXXX-XXXX-XXXX"
                          maxLength={20}
                          className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm uppercase tracking-wide focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                        />
                        <ActionButton
                          type="submit"
                          icon={FiLink}
                          intent="info"
                          tone="outline"
                          loading={acao === `convidar-${grupo.id}`}
                        >
                          Convidar
                        </ActionButton>
                      </form>
                      {grupo.convites_enviados.length > 0 ? (
                        <div className="mt-4 space-y-2">
                          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                            Aguardando aceite
                          </div>
                          {grupo.convites_enviados.map((convite) => (
                            <div
                              key={convite.id}
                              className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900"
                            >
                              {convite.empresa_nome} · expira em {formatarData(convite.expira_em)}
                            </div>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                    A empresa responsável administra os convites e participantes deste grupo.
                  </div>
                )}
              </div>
              <EstoqueCompartilhadoGrupo empresaAtualId={resumo.empresa_atual_id} grupo={grupo} />
            </Panel>
          ))
        )}
      </div>
    </div>
  );
}
