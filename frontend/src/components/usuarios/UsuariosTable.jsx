import React from "react";

export default function UsuariosTable({
  loading,
  onForcarLogout,
  onToggleStatus,
  usuarios,
}) {
  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="mt-2 text-gray-600">Carregando...</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Email
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Role
            </th>
            <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
            <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
              Ações
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {usuarios.length === 0 ? (
            <tr>
              <td colSpan="4" className="px-6 py-12 text-center text-gray-500">
                Nenhum usuário encontrado
              </td>
            </tr>
          ) : (
            usuarios.map((usuario) => (
              <tr key={usuario.user_id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">
                    {usuario.email}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                    {usuario.role}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <span
                    className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      usuario.is_active
                        ? "bg-green-100 text-green-800"
                        : "bg-red-100 text-red-800"
                    }`}
                  >
                    {usuario.is_active ? "Ativo" : "Inativo"}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                  <div className="flex items-center justify-center gap-2">
                    <button
                      onClick={() => onForcarLogout(usuario.user_id)}
                      className="px-3 py-1 rounded text-white transition-colors bg-amber-500 hover:bg-amber-600"
                      title="Encerra sessões sem desativar o usuário"
                    >
                      Forçar Logout
                    </button>
                    <button
                      onClick={() =>
                        onToggleStatus(usuario.user_id, usuario.is_active)
                      }
                      className={`px-3 py-1 rounded text-white transition-colors ${
                        usuario.is_active
                          ? "bg-red-500 hover:bg-red-600"
                          : "bg-green-500 hover:bg-green-600"
                      }`}
                      title={
                        usuario.is_active
                          ? "Desativa o acesso do usuário"
                          : "Reativa o acesso do usuário"
                      }
                    >
                      {usuario.is_active ? "Desativar Acesso" : "Ativar Acesso"}
                    </button>
                  </div>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
