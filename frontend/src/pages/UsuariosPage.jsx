import { Plus, Users } from "lucide-react";
import UsuarioModal from "../components/usuarios/UsuarioModal";
import UsuarioCredenciaisModal from "../components/usuarios/UsuarioCredenciaisModal";
import UsuarioAcessoInicialModal from "../components/usuarios/UsuarioAcessoInicialModal";
import UsuarioLojaLoginCard from "../components/usuarios/UsuarioLojaLoginCard";
import UsuariosTable from "../components/usuarios/UsuariosTable";
import ActionButton from "../components/ui/ActionButton";
import PageHeader from "../components/ui/PageHeader";
import useUsuariosPage from "../hooks/useUsuariosPage";

export default function UsuariosPage() {
  const {
    criarUsuario,
    credenciais,
    credenciaisError,
    fecharCredenciais,
    forcarLogout,
    generatedPassword,
    gerarNovaSenha,
    initialAccessCredentials,
    loading,
    novoUsuario,
    onAbrirModalUsuario,
    onAbrirCredenciais,
    onCloseModalUsuario,
    roles,
    setNovoUsuario,
    setCredenciais,
    setShowPassword,
    showModal,
    showPassword,
    salvarCredenciais,
    savingCredentials,
    setInitialAccessCredentials,
    tenantLoginReference,
    toggleStatus,
    usuarioFormError,
    usuarioCredenciais,
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

      <UsuarioLojaLoginCard tenantReference={tenantLoginReference} />

      <UsuariosTable
        loading={loading}
        onForcarLogout={forcarLogout}
        onManageCredentials={onAbrirCredenciais}
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

      <UsuarioCredenciaisModal
        credenciais={credenciais}
        erro={credenciaisError}
        generatedPassword={generatedPassword}
        loading={savingCredentials}
        onChange={setCredenciais}
        onClose={fecharCredenciais}
        onGenerate={gerarNovaSenha}
        onSubmit={salvarCredenciais}
        tenantReference={tenantLoginReference}
        usuario={usuarioCredenciais}
      />

      <UsuarioAcessoInicialModal
        credentials={initialAccessCredentials}
        onClose={() => setInitialAccessCredentials(null)}
      />
    </div>
  );
}
