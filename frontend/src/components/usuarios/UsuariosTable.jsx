import { Building2, KeyRound, LogOut, Mail, UserCheck, UserX } from "lucide-react";
import BotaoMenuAcoes from "../v2/BotaoMenuAcoes/BotaoMenuAcoes";
import DataTable from "../ui/DataTable";
import Panel from "../ui/Panel";
import StatusBadge from "../ui/StatusBadge";
import { formatBrazilianLoginPhone } from "../../utils/loginPhone";

function formatPessoaTipo(tipoCadastro) {
  const value = (tipoCadastro || "").trim();
  if (!value) return "";
  return value.charAt(0).toUpperCase() + value.slice(1).replaceAll("_", " ");
}

export default function UsuariosTable({
  loading,
  onForcarLogout,
  onManageCredentials,
  onRecriarSenha,
  onToggleStatus,
  onVincularLoja,
  paginacaoRodape,
  usuarios,
}) {
  const columns = [
    {
      key: "actions",
      header: "Acoes",
      align: "left",
      render: (usuario) => (
        <BotaoMenuAcoes
          rotulo={`Mais ações para ${usuario.nome || usuario.login_phone || usuario.email}`}
          acoes={[
            {
              icon: KeyRound,
              label: "Gerenciar usuário e senha",
              onClick: () => onManageCredentials(usuario),
            },
            {
              icon: Mail,
              label: "Recriar senha",
              disabled: !usuario.email,
              title: usuario.email
                ? undefined
                : "Usuário sem e-mail cadastrado — não é possível enviar recriação de senha",
              onClick: () => onRecriarSenha(usuario.user_id),
            },
            {
              icon: Building2,
              label: "Vincular a outra loja do grupo",
              onClick: () => onVincularLoja(usuario),
            },
            {
              icon: LogOut,
              label: "Forçar logout",
              onClick: () => onForcarLogout(usuario.user_id),
            },
            {
              icon: usuario.is_active ? UserX : UserCheck,
              label: usuario.is_active ? "Desativar acesso" : "Ativar acesso",
              tom: usuario.is_active ? "perigo" : "neutro",
              onClick: () => onToggleStatus(usuario.user_id, usuario.is_active),
            },
          ]}
        />
      ),
    },
    {
      key: "login_phone",
      header: "Usuario",
      render: (usuario) => (
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-slate-900">
            {usuario.login_phone
              ? formatBrazilianLoginPhone(usuario.login_phone)
              : usuario.username || usuario.email}
          </p>
          <p className="truncate text-xs text-slate-500">
            {usuario.nome || usuario.email || `ID ${usuario.user_id}`}
          </p>
        </div>
      ),
    },
    {
      key: "pessoa",
      header: "Pessoa vinculada",
      render: (usuario) =>
        usuario.pessoa_id ? (
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-900">
              {usuario.pessoa_nome || `Pessoa ${usuario.pessoa_id}`}
            </p>
            <p className="truncate text-xs text-slate-500">
              {[
                usuario.pessoa_codigo ? `Codigo ${usuario.pessoa_codigo}` : null,
                formatPessoaTipo(usuario.pessoa_tipo_cadastro),
              ]
                .filter(Boolean)
                .join(" - ")}
            </p>
          </div>
        ) : (
          <StatusBadge intent="warning" size="sm">
            Sem pessoa
          </StatusBadge>
        ),
    },
    {
      key: "role",
      header: "Perfil",
      render: (usuario) => (
        <StatusBadge intent="info" size="sm">
          {usuario.role || "Sem perfil"}
        </StatusBadge>
      ),
    },
    {
      key: "status",
      header: "Status",
      align: "center",
      render: (usuario) => (
        <StatusBadge
          status={usuario.is_active ? "ativo" : "inativo"}
          intent={usuario.is_active ? "success" : "neutral"}
        />
      ),
    },
  ];

  return (
    <Panel padding="none">
      <DataTable
        columns={columns}
        data={usuarios}
        emptyMessage="Nenhum usuario encontrado"
        getRowKey={(usuario) => usuario.user_id}
        loading={loading}
        loadingMessage="Carregando usuarios..."
        tableClassName="min-w-[860px]"
      />
      {paginacaoRodape}
    </Panel>
  );
}
