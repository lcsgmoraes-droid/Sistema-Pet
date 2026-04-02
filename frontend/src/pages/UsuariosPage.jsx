import UsuarioModal from "../components/usuarios/UsuarioModal";
import UsuariosTable from "../components/usuarios/UsuariosTable";
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
    usuarios,
  } = useUsuariosPage();

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Usuários</h1>
          <p className="text-gray-600 mt-1">Gerencie os usuários do sistema</p>
        </div>
        <button
          onClick={onAbrirModalUsuario}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Novo Usuário
        </button>
      </div>

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
      />
    </div>
  );
}
