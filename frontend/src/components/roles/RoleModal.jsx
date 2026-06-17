import { useEffect, useRef } from "react";
import { AlertCircle, ChevronDown, ChevronRight, Save, ShieldPlus, X } from "lucide-react";
import ActionButton from "../ui/ActionButton";
import { TextField } from "../ui/FormField";
import IconActionButton from "../ui/IconActionButton";

function PermissionCategory({
  expanded,
  group,
  onToggleCategory,
  onToggleExpanded,
  onTogglePermission,
  selectedIds,
}) {
  const checkboxRef = useRef(null);
  const permissionIds = group.permissions.map((permission) => permission.permission_id);
  const selectedCount = permissionIds.filter((id) => selectedIds.includes(id)).length;
  const allSelected = permissionIds.length > 0 && selectedCount === permissionIds.length;
  const partiallySelected = selectedCount > 0 && selectedCount < permissionIds.length;
  const categoryCheckboxId = `role-category-${group.key}`;

  useEffect(() => {
    if (checkboxRef.current) {
      checkboxRef.current.indeterminate = partiallySelected;
    }
  }, [partiallySelected]);

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <div className="flex items-center gap-2 bg-slate-50 px-3 py-2">
        <IconActionButton
          icon={expanded ? ChevronDown : ChevronRight}
          intent="neutral"
          onClick={() => onToggleExpanded(group.key)}
          title={expanded ? "Recolher categoria" : "Expandir categoria"}
          tone="ghost"
        />
        <div className="flex min-w-0 flex-1 items-center gap-3 rounded-md px-2 py-1">
          <input
            id={categoryCheckboxId}
            ref={checkboxRef}
            type="checkbox"
            name={categoryCheckboxId}
            checked={allSelected}
            onChange={() => onToggleCategory(permissionIds)}
            aria-label={`Selecionar permissoes de ${group.label}`}
            className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
          />
          <button
            type="button"
            onClick={() => onToggleCategory(permissionIds)}
            className="min-w-0 flex-1 text-left text-sm font-semibold text-slate-900"
          >
            {group.label}
          </button>
          <span className="text-xs text-slate-500">
            {selectedCount}/{permissionIds.length}
          </span>
        </div>
      </div>

      {expanded ? (
        <div className="space-y-1 border-t border-slate-100 p-3">
          {group.permissions.map((permission) => {
            const checked = selectedIds.includes(permission.permission_id);
            const permissionLabel = permission.nome?.includes(".")
              ? permission.nome.split(".").slice(1).join(".")
              : permission.nome;

            return (
              <label
                key={permission.permission_id}
                htmlFor={`role-permission-${permission.permission_id}`}
                className="flex cursor-pointer items-start gap-3 rounded-lg px-3 py-2 transition hover:bg-slate-50"
              >
                <input
                  id={`role-permission-${permission.permission_id}`}
                  type="checkbox"
                  name="permissions"
                  checked={checked}
                  onChange={() => onTogglePermission(permission.permission_id)}
                  className="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="min-w-0">
                  <span className="block text-sm font-medium text-slate-800">
                    {permissionLabel}
                  </span>
                  {permission.descricao ? (
                    <span className="mt-0.5 block text-xs text-slate-500">
                      {permission.descricao}
                    </span>
                  ) : (
                    <span className="mt-0.5 block text-xs text-slate-400">{permission.nome}</span>
                  )}
                </span>
              </label>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

export default function RoleModal({
  editingRole,
  expandedCategories,
  onClose,
  onSetNome,
  onSubmit,
  onToggleCategory,
  onToggleExpandedCategory,
  onTogglePermission,
  permissionGroups,
  roleForm,
  roleFormError,
  saving,
  showModal,
}) {
  if (!showModal) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4">
      <div
        className="flex max-h-[90vh] w-full max-w-3xl flex-col rounded-lg border border-slate-200 bg-white shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="role-modal-title"
      >
        <div className="flex items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
          <div>
            <h2 id="role-modal-title" className="text-lg font-semibold text-slate-950">
              {editingRole ? "Editar perfil" : "Novo perfil"}
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Defina quais acoes este perfil pode executar no tenant atual.
            </p>
          </div>
          <IconActionButton
            disabled={saving}
            icon={X}
            intent="neutral"
            onClick={onClose}
            title="Fechar"
            tone="ghost"
          />
        </div>

        <form onSubmit={onSubmit} className="flex min-h-0 flex-1 flex-col">
          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-4">
            {roleFormError ? (
              <div
                className="flex gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
                role="alert"
              >
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                <span>{roleFormError}</span>
              </div>
            ) : null}

            <TextField
              autoComplete="off"
              id="role-name"
              label="Nome do perfil"
              name="role_name"
              onChange={onSetNome}
              placeholder="Ex: Vendedor, Gerente, Caixa"
              required
              value={roleForm.nome}
            />

            <div>
              <div className="mb-2 flex items-center justify-between gap-3">
                <span className="text-xs font-medium text-slate-600">Permissoes</span>
                <span className="text-xs text-slate-500">
                  {roleForm.permissions.length} selecionadas
                </span>
              </div>

              {permissionGroups.length === 0 ? (
                <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
                  Nenhuma permissao disponivel.
                </div>
              ) : (
                <div className="space-y-2">
                  {permissionGroups.map((group) => (
                    <PermissionCategory
                      key={group.key}
                      expanded={Boolean(expandedCategories[group.key])}
                      group={group}
                      onToggleCategory={onToggleCategory}
                      onToggleExpanded={onToggleExpandedCategory}
                      onTogglePermission={onTogglePermission}
                      selectedIds={roleForm.permissions}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-col-reverse gap-2 border-t border-slate-100 px-5 py-4 sm:flex-row sm:justify-end">
            <ActionButton disabled={saving} intent="neutral" onClick={onClose} tone="soft">
              Cancelar
            </ActionButton>
            <ActionButton
              icon={editingRole ? Save : ShieldPlus}
              intent={editingRole ? "edit" : "create"}
              loading={saving}
              type="submit"
            >
              {editingRole ? "Atualizar perfil" : "Criar perfil"}
            </ActionButton>
          </div>
        </form>
      </div>
    </div>
  );
}
