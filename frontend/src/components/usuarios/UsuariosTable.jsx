import { KeyRound, LogOut, UserCheck, UserX } from "lucide-react";
import DataTable from "../ui/DataTable";
import IconActionButton from "../ui/IconActionButton";
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
  onToggleStatus,
  usuarios,
}) {
  const columns = [
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
    {
      key: "actions",
      header: "Acoes",
      align: "center",
      render: (usuario) => (
        <div className="flex items-center justify-center gap-2">
          <IconActionButton
            icon={KeyRound}
            intent="edit"
            onClick={() => onManageCredentials(usuario)}
            title="Gerenciar usuario e senha"
          />
          <IconActionButton
            icon={LogOut}
            intent="warning"
            onClick={() => onForcarLogout(usuario.user_id)}
            title="Forcar logout"
          />
          <IconActionButton
            icon={usuario.is_active ? UserX : UserCheck}
            intent={usuario.is_active ? "danger" : "success"}
            onClick={() => onToggleStatus(usuario.user_id, usuario.is_active)}
            title={usuario.is_active ? "Desativar acesso" : "Ativar acesso"}
          />
        </div>
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
    </Panel>
  );
}
