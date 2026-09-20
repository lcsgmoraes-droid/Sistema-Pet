import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import {
  FiBarChart2,
  FiChevronLeft,
  FiGrid,
  FiLink,
  FiPlusCircle,
  FiTrash2,
  FiUsers,
} from "react-icons/fi";
import ActionButton from "../../components/ui/ActionButton";
import EmptyState from "../../components/ui/EmptyState";
import { TextField } from "../../components/ui/FormField";
import LoadingState from "../../components/ui/LoadingState";
import ModuleTabs from "../../components/ui/ModuleTabs";
import PageHeader from "../../components/ui/PageHeader";
import Panel from "../../components/ui/Panel";
import StatusBadge from "../../components/ui/StatusBadge";
import { adicionarLojaGrupo, obterResumoGruposComerciais, removerEmpresaGrupo } from "../../services/gruposComerciais";
import { confirmarCorePet } from "../../services/corepetDialog";
import { useAuth } from "../../contexts/AuthContext";
import EstoqueCompartilhadoGrupo from "./EstoqueCompartilhadoGrupo";
import GrupoComercialAcessos from "./GrupoComercialAcessos";
import GrupoComercialCobranca from "./GrupoComercialCobranca";

const resumoVazio = {
  empresa_atual_id: null,
  grupos: [],
  tem_grupo_sem_acesso: false,
};

function mensagemErro(error, padrao) {
  return error?.response?.data?.detail || padrao;
}

function GrupoComercialPainel({
  acao,
  empresaAtualId,
  executar,
  grupo,
  navigate,
  onRemover,
  podeAnalisarGrupo,
}) {
  const [aba, setAba] = useState("membros");
  const [nomeNovaLoja, setNomeNovaLoja] = useState("");

  const abas = [
    { id: "membros", label: "Lojas do grupo" },
    { id: "cobranca", label: "Cobrança" },
    ...(grupo.sou_master ? [{ id: "acessos", label: "Acessos do grupo" }] : []),
  ];

  function handleAdicionarLoja(event) {
    event.preventDefault();
    const nome = nomeNovaLoja.trim();
    if (nome.length < 2) {
      toast.error("Informe o nome da nova loja.");
      return;
    }
    executar(
      `adicionar-loja-${grupo.id}`,
      async () => {
        await adicionarLojaGrupo(grupo.id, { nomeLoja: nome });
        setNomeNovaLoja("");
      },
      "Loja criada e adicionada ao grupo.",
    );
  }

  return (
    <Panel
      title={grupo.nome}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge intent={grupo.sou_master ? "purple" : "info"}>
            {grupo.sou_master ? "Master" : "Gestor"}
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
              onClick={() => navigate(`/configuracoes/grupos-comerciais/${grupo.id}/visao-consolidada`)}
            >
              Ver visão consolidada
            </ActionButton>
          ) : null}
        </div>
      }
    >
      <ModuleTabs active={aba} onChange={setAba} tabs={abas} className="mb-4" />

      {aba === "membros" ? (
        <div className="grid gap-5 lg:grid-cols-[1fr_0.9fr]">
          <div>
            <h3 className="text-sm font-semibold text-slate-800">Lojas participantes</h3>
            <div className="mt-2 divide-y divide-slate-100 rounded-lg border border-slate-200">
              {grupo.membros.map((membro) => (
                <div
                  key={membro.empresa_id}
                  className="flex items-center justify-between gap-3 px-3 py-2.5"
                >
                  <div>
                    <div className="text-sm font-medium text-slate-900">{membro.empresa_nome}</div>
                    <div className="text-xs text-slate-500">
                      {membro.papel === "responsavel" ? "Loja responsável" : "Loja do grupo"}
                    </div>
                  </div>
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
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-slate-800">Adicionar nova loja ao grupo</h3>
            <p className="mt-1 text-xs text-slate-500">
              Cria uma loja nova, com seu próprio login, já dentro deste grupo.
            </p>
            <form className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-end" onSubmit={handleAdicionarLoja}>
              <TextField
                className="min-w-0 flex-1"
                value={nomeNovaLoja}
                onChange={setNomeNovaLoja}
                placeholder="Nome da nova loja"
                maxLength={150}
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
        </div>
      ) : null}

      {aba === "cobranca" ? <GrupoComercialCobranca grupoId={grupo.id} /> : null}

      {aba === "acessos" && grupo.sou_master ? <GrupoComercialAcessos grupoId={grupo.id} /> : null}

      <EstoqueCompartilhadoGrupo empresaAtualId={empresaAtualId} grupo={grupo} />
    </Panel>
  );
}

export default function GruposComerciais() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [resumo, setResumo] = useState(resumoVazio);
  const [carregando, setCarregando] = useState(true);
  const [acao, setAcao] = useState("");
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
        subtitle="Toda loja já nasce dentro de um grupo comercial. Adicione novas lojas suas direto aqui."
      />

      <div className="space-y-4">
        {resumo.grupos.length === 0 ? (
          <EmptyState
            icon={FiLink}
            title={
              resumo.tem_grupo_sem_acesso
                ? "Você não tem acesso à gestão deste grupo"
                : "Nenhum grupo encontrado"
            }
            description={
              resumo.tem_grupo_sem_acesso
                ? "Peça para o responsável do seu grupo comercial liberar seu acesso nesta tela."
                : "Fale com o suporte se você acredita que sua loja deveria ter um grupo comercial."
            }
          />
        ) : (
          resumo.grupos.map((grupo) => (
            <GrupoComercialPainel
              key={grupo.id}
              acao={acao}
              empresaAtualId={resumo.empresa_atual_id}
              executar={executar}
              grupo={grupo}
              navigate={navigate}
              onRemover={handleRemover}
              podeAnalisarGrupo={podeAnalisarGrupo}
            />
          ))
        )}
      </div>
    </div>
  );
}
