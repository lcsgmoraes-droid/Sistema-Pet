import { Edit3, ShieldCheck, Trash2 } from "lucide-react";
import IconActionButton from "../ui/IconActionButton";
import Panel from "../ui/Panel";
import StatusBadge from "../ui/StatusBadge";

const MAX_VISIBLE_PERMISSIONS = 8;

export default function RoleCard({ onDelete, onEdit, role }) {
  const permissions = role.permissions || [];
  const visiblePermissions = permissions.slice(0, MAX_VISIBLE_PERMISSIONS);
  const hiddenCount = Math.max(permissions.length - visiblePermissions.length, 0);

  return (
    <Panel className="flex h-full flex-col" padding="md">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-700">
              <ShieldCheck className="h-5 w-5" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h2 className="truncate text-base font-semibold text-slate-950">
                {role.nome}
              </h2>
              <p className="text-xs text-slate-500">ID {role.role_id}</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <IconActionButton
            icon={Edit3}
            intent="info"
            onClick={() => onEdit(role)}
            title="Editar perfil"
          />
          <IconActionButton
            icon={Trash2}
            intent="delete"
            onClick={() => onDelete(role.role_id)}
            title="Excluir perfil"
          />
        </div>
      </div>

      <div className="mt-4 flex flex-1 flex-col">
        <div className="mb-2 flex items-center justify-between gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Permissoes
          </span>
          <StatusBadge intent={permissions.length ? "info" : "neutral"} size="xs">
            {permissions.length}
          </StatusBadge>
        </div>

        {permissions.length === 0 ? (
          <p className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-500">
            Sem permissoes vinculadas.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {visiblePermissions.map((permission) => (
              <StatusBadge key={permission.permission_id} intent="neutral" size="xs">
                {permission.nome}
              </StatusBadge>
            ))}
            {hiddenCount ? (
              <StatusBadge intent="purple" size="xs">
                +{hiddenCount}
              </StatusBadge>
            ) : null}
          </div>
        )}
      </div>
    </Panel>
  );
}
