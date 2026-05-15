import { Plus, Users } from "lucide-react";
import UsuarioModal from "../components/usuarios/UsuarioModal";
import UsuariosTable from "../components/usuarios/UsuariosTable";
import ActionButton from "../components/ui/ActionButton";
import PageHeader from "../components/ui/PageHeader";
import useUsuariosPage from "../hooks/useUsuariosPage";

export default function UsuariosPage() {
  const {
    criarUsuario,
    forcarLogout,
    loading,
    novoUsuario,
    onAbrirModalUsuario,
    onCloseModalUsuario,
    roles,
    setNovoUsuario,
    setShowPassword,
    showModal,
    showPassword,
    toggleStatus,
    usuarioFormError,
    usuarios,
  } = useUsuariosPage();

  return (
    <div className="space-y-4 p-4 sm:p-6">
      <PageHeader
        icon={Users}
        title="Usuarios"
        subtitle="Gerencie usuarios, perfis e acessos do tenant atual."
        actions={
          <ActionButton icon={Plus} intent="create" onClick={onAbrirModalUsuario}>
            Novo usuario
          </ActionButton>
        }
      />

      <UsuariosTable
        loading={loading}
        onForcarLogout={forcarLogout}
        onToggleStatus={toggleStatus}
        usuarios={usuarios}
      />

      <UsuarioModal
        novoUsuario={novoUsuario}
        onClose={onCloseModalUsuario}
        onSubmit={criarUsuario}
        roles={roles}
        setNovoUsuario={setNovoUsuario}
        setShowPassword={setShowPassword}
        showModal={showModal}
        showPassword={showPassword}
        usuarioFormError={usuarioFormError}
      />
    </div>
  );
}
