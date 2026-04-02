import React from "react";

export default function UsuarioModal({
  novoUsuario,
  onClose,
  onSubmit,
  roles,
  setNovoUsuario,
  setShowPassword,
  showModal,
  showPassword,
}) {
  if (!showModal) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-bold text-gray-900">Novo Usuário</h2>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="novo-usuario-email"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Email *
              </label>
              <input
                id="novo-usuario-email"
                type="email"
                required
                value={novoUsuario.email}
                onChange={(event) =>
                  setNovoUsuario({ ...novoUsuario, email: event.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="usuario@exemplo.com"
                autoComplete="off"
              />
            </div>

            <div>
              <label
                htmlFor="novo-usuario-senha"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Senha *
              </label>
              <div className="relative">
                <input
                  id="novo-usuario-senha"
                  type={showPassword ? "text" : "password"}
                  required
                  value={novoUsuario.password}
                  onChange={(event) =>
                    setNovoUsuario({
                      ...novoUsuario,
                      password: event.target.value,
                    })
                  }
                  className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Mínimo 6 caracteres"
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                >
                  {showPassword ? (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                      />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                      />
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                      />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            <div>
              <label
                htmlFor="novo-usuario-role"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Role *
              </label>
              <select
                id="novo-usuario-role"
                value={novoUsuario.role_id || ""}
                onChange={(event) =>
                  setNovoUsuario({
                    ...novoUsuario,
                    role_id: Number.parseInt(event.target.value, 10),
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              >
                {roles.length === 0 ? (
                  <option value="">Carregando...</option>
                ) : (
                  <>
                    <option value="">Selecione uma role...</option>
                    {roles.map((role) => (
                      <option key={role.role_id} value={role.role_id}>
                        {role.nome}
                      </option>
                    ))}
                  </>
                )}
              </select>
            </div>

            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Criar Usuário
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
