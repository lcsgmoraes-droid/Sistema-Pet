import { AlertCircle, Eye, EyeOff, UserPlus, X } from "lucide-react";
import ActionButton from "../ui/ActionButton";
import IconActionButton from "../ui/IconActionButton";

export default function UsuarioModal({
  novoUsuario,
  onClose,
  onSubmit,
  roles,
  setNovoUsuario,
  setShowPassword,
  showModal,
  showPassword,
  usuarioFormError,
}) {
  if (!showModal) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4">
      <div
        className="w-full max-w-md rounded-lg border border-slate-200 bg-white shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="novo-usuario-title"
      >
        <div className="flex items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
          <div>
            <h2 id="novo-usuario-title" className="text-lg font-semibold text-slate-950">
              Novo usuario
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Crie o acesso vinculado ao tenant atual.
            </p>
          </div>
          <IconActionButton
            icon={X}
            intent="neutral"
            onClick={onClose}
            title="Fechar"
            tone="ghost"
          />
        </div>

        <form onSubmit={onSubmit} className="space-y-4 px-5 py-4">
          {usuarioFormError ? (
            <div
              className="flex gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
              role="alert"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <span>{usuarioFormError}</span>
            </div>
          ) : null}

          <div>
            <label
              htmlFor="novo-usuario-email"
              className="mb-1 block text-sm font-medium text-slate-700"
            >
              Email
            </label>
            <input
              id="novo-usuario-email"
              type="email"
              required
              value={novoUsuario.email}
              onChange={(event) =>
                setNovoUsuario({ ...novoUsuario, email: event.target.value })
              }
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              placeholder="usuario@empresa.com.br"
              autoComplete="email"
            />
          </div>

          <div>
            <label
              htmlFor="novo-usuario-senha"
              className="mb-1 block text-sm font-medium text-slate-700"
            >
              Senha
            </label>
            <div className="relative">
              <input
                id="novo-usuario-senha"
                type={showPassword ? "text" : "password"}
                required
                minLength={8}
                value={novoUsuario.password}
                onChange={(event) =>
                  setNovoUsuario({
                    ...novoUsuario,
                    password: event.target.value,
                  })
                }
                className="w-full rounded-lg border border-slate-300 px-3 py-2 pr-11 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                placeholder="Minimo 8 caracteres"
                autoComplete="new-password"
              />
              <IconActionButton
                className="absolute right-1.5 top-1/2 -translate-y-1/2"
                icon={showPassword ? EyeOff : Eye}
                intent="neutral"
                onClick={() => setShowPassword(!showPassword)}
                title={showPassword ? "Ocultar senha" : "Mostrar senha"}
                tone="ghost"
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="novo-usuario-role"
              className="mb-1 block text-sm font-medium text-slate-700"
            >
              Perfil de acesso
            </label>
            <select
              id="novo-usuario-role"
              value={novoUsuario.role_id || ""}
              onChange={(event) =>
                setNovoUsuario({
                  ...novoUsuario,
                  role_id: event.target.value ? Number.parseInt(event.target.value, 10) : null,
                })
              }
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              required
              disabled={roles.length === 0}
            >
              {roles.length === 0 ? (
                <option value="">Nenhum perfil disponivel</option>
              ) : (
                <>
                  <option value="">Selecione um perfil...</option>
                  {roles.map((role) => (
                    <option key={role.role_id} value={role.role_id}>
                      {role.nome}
                    </option>
                  ))}
                </>
              )}
            </select>
          </div>

          <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
            <ActionButton intent="neutral" onClick={onClose} tone="soft">
              Cancelar
            </ActionButton>
            <ActionButton
              disabled={roles.length === 0}
              icon={UserPlus}
              intent="create"
              type="submit"
            >
              Criar usuario
            </ActionButton>
          </div>
        </form>
      </div>
    </div>
  );
}
