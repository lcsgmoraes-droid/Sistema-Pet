import { Plus, ShieldCheck } from "lucide-react";
import RoleCard from "../components/roles/RoleCard";
import RoleModal from "../components/roles/RoleModal";
import ActionButton from "../components/ui/ActionButton";
import EmptyState from "../components/ui/EmptyState";
import LoadingState from "../components/ui/LoadingState";
import PageHeader from "../components/ui/PageHeader";
import useRolesPage from "../hooks/useRolesPage";

export default function RolesPage() {
  const {
    abrirCriacao,
    abrirEdicao,
    deletarRole,
    editingRole,
    expandedCategories,
    fecharModal,
    loading,
    permissionGroups,
    roleForm,
    roleFormError,
    roles,
    salvarRole,
    saving,
    setNome,
    showModal,
    toggleCategory,
    toggleExpandedCategory,
    togglePermission,
  } = useRolesPage();

  return (
    <div className="space-y-4 p-4 sm:p-6">
      <PageHeader
        icon={ShieldCheck}
        title="Roles e permissoes"
        subtitle="Gerencie perfis de acesso e permissoes do tenant atual."
        actions={
          <ActionButton icon={Plus} intent="create" onClick={abrirCriacao}>
            Novo perfil
          </ActionButton>
        }
      />

      {loading ? (
        <LoadingState label="Carregando perfis..." />
      ) : roles.length === 0 ? (
        <EmptyState
          action={
            <ActionButton icon={Plus} intent="create" onClick={abrirCriacao}>
              Criar primeiro perfil
            </ActionButton>
          }
          icon={ShieldCheck}
          title="Nenhum perfil encontrado"
          description="Crie perfis para controlar o que cada usuario pode acessar."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {roles.map((role) => (
            <RoleCard
              key={role.role_id}
              onDelete={deletarRole}
              onEdit={abrirEdicao}
              role={role}
            />
          ))}
        </div>
      )}

      <RoleModal
        editingRole={editingRole}
        expandedCategories={expandedCategories}
        onClose={fecharModal}
        onSetNome={setNome}
        onSubmit={salvarRole}
        onToggleCategory={toggleCategory}
        onToggleExpandedCategory={toggleExpandedCategory}
        onTogglePermission={togglePermission}
        permissionGroups={permissionGroups}
        roleForm={roleForm}
        roleFormError={roleFormError}
        saving={saving}
        showModal={showModal}
      />
    </div>
  );
}
