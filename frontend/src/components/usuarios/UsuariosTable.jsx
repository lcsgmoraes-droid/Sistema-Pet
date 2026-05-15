import { LogOut, UserCheck, UserX } from "lucide-react";
import DataTable from "../ui/DataTable";
import IconActionButton from "../ui/IconActionButton";
import Panel from "../ui/Panel";
import StatusBadge from "../ui/StatusBadge";

export default function UsuariosTable({
  loading,
  onForcarLogout,
  onToggleStatus,
  usuarios,
}) {
  const columns = [
    {
      key: "email",
      header: "Email",
      render: (usuario) => (
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-slate-900">
            {usuario.email}
          </p>
          <p className="text-xs text-slate-500">ID {usuario.user_id}</p>
        </div>
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
        tableClassName="min-w-[720px]"
      />
    </Panel>
  );
}
