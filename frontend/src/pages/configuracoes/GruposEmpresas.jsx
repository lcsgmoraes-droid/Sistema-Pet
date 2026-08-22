import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import {
  FiCheck,
  FiChevronLeft,
  FiCopy,
  FiLink,
  FiPlus,
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
  convidarEmpresa,
  criarGrupoEmpresa,
  obterResumoGruposEmpresas,
  removerEmpresaGrupo,
  responderConviteGrupo,
} from "../../services/gruposEmpresas";
import { confirmarCorePet } from "../../services/corepetDialog";

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

export default function GruposEmpresas() {
  const [resumo, setResumo] = useState(resumoVazio);
  const [carregando, setCarregando] = useState(true);
  const [acao, setAcao] = useState("");
  const [nomeGrupo, setNomeGrupo] = useState("");
  const [codigosConvite, setCodigosConvite] = useState({});

  const carregar = useCallback(async () => {
    try {
      setResumo(await obterResumoGruposEmpresas());
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível carregar os grupos de empresas."));
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

  function handleCriarGrupo(event) {
    event.preventDefault();
    const nome = nomeGrupo.trim();
    if (nome.length < 2) {
      toast.error("Informe o nome do grupo.");
      return;
    }
    executar(
      "criar-grupo",
      async () => {
        await criarGrupoEmpresa(nome);
        setNomeGrupo("");
      },
      "Grupo criado. Agora você pode convidar outras empresas.",
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
    return <LoadingState label="Carregando grupos de empresas..." />;
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
        title="Grupos de empresas"
        subtitle="Conecte empresas por convite para preparar transferências e análises consolidadas."
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

      <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
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

        <Panel
          title="Criar um grupo"
          subtitle="A empresa criadora fica responsável pelos convites e membros."
        >
          <form className="flex flex-col gap-3 sm:flex-row" onSubmit={handleCriarGrupo}>
            <label className="flex-1">
              <span className="sr-only">Nome do grupo</span>
              <input
                value={nomeGrupo}
                onChange={(event) => setNomeGrupo(event.target.value)}
                maxLength={150}
                placeholder="Ex.: Grupo Lojas Centro"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
              />
            </label>
            <ActionButton
              type="submit"
              icon={FiPlus}
              intent="info"
              loading={acao === "criar-grupo"}
            >
              Criar grupo
            </ActionButton>
          </form>
        </Panel>
      </div>

      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Seus grupos</h2>
          <p className="text-sm text-slate-500">
            Os dados continuam separados por empresa; o grupo apenas autoriza os recursos
            consolidados escolhidos.
          </p>
        </div>

        {resumo.grupos.length === 0 ? (
          <EmptyState
            icon={FiLink}
            title="Nenhum grupo criado ou aceito"
            description="Crie um grupo ou compartilhe seu código mensal para receber um convite."
          />
        ) : (
          resumo.grupos.map((grupo) => (
            <Panel
              key={grupo.id}
              title={grupo.nome}
              actions={
                <StatusBadge intent={grupo.papel === "responsavel" ? "purple" : "info"}>
                  {grupo.papel === "responsavel" ? "Responsável" : "Membro"}
                </StatusBadge>
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
                  <div>
                    <h3 className="text-sm font-semibold text-slate-800">Convidar empresa</h3>
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
                ) : (
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                    A empresa responsável administra os convites e participantes deste grupo.
                  </div>
                )}
              </div>
            </Panel>
          ))
        )}
      </div>
    </div>
  );
}
