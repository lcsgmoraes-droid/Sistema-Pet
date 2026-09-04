import { Clipboard, KeyRound, RefreshCw, X } from "lucide-react";
import { formatInitialAccessCredentials } from "../../utils/usuarioAcessoInicial";
import ActionButton from "../ui/ActionButton";
import IconActionButton from "../ui/IconActionButton";

export default function UsuarioCredenciaisModal({
  credenciais,
  erro,
  generatedPassword,
  loading,
  onChange,
  onClose,
  onGenerate,
  onSubmit,
  roles,
  tenantReference,
  usuario,
}) {
  if (!usuario) return null;

  const copiarSenha = async () => {
    if (!generatedPassword) return;
    await navigator.clipboard.writeText(generatedPassword);
  };

  const copiarDadosDeAcesso = async () => {
    if (!generatedPassword || !tenantReference) return;
    await navigator.clipboard.writeText(
      formatInitialAccessCredentials({
        tenant: tenantReference,
        username: credenciais.username,
        password: generatedPassword,
      }),
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4">
      <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white shadow-xl">
        <div className="flex items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-950">Gerenciar acesso</h2>
            <p className="mt-1 text-sm text-slate-500">
              {usuario.nome || usuario.username || usuario.email}
            </p>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="cred-role">
              Perfil de acesso
            </label>
            <select
              id="cred-role"
              value={credenciais.role_id}
              onChange={(event) => onChange({ ...credenciais, role_id: event.target.value })}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
              required
            >
              <option value="">Selecione um perfil</option>
              {roles.map((role) => (
                <option key={role.role_id} value={role.role_id}>
                  {role.nome}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-slate-500">
              Ao trocar o perfil, as sessoes abertas deste usuario serao encerradas.
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
          {erro && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{erro}</p>}

          <div>
            <label
              className="mb-1 block text-sm font-medium text-slate-700"
              htmlFor="cred-username"
            >
              Nome de usuario
            </label>
            <input
              id="cred-username"
              value={credenciais.username}
              onChange={(event) => onChange({ ...credenciais, username: event.target.value })}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              minLength={3}
              maxLength={40}
              required
              autoComplete="username"
            />
          </div>

          <div>
            <label
              className="mb-1 block text-sm font-medium text-slate-700"
              htmlFor="cred-password"
            >
              Definir nova senha (opcional)
            </label>
            <input
              id="cred-password"
              type="password"
              value={credenciais.new_password}
              onChange={(event) => onChange({ ...credenciais, new_password: event.target.value })}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              placeholder="Minimo 8 caracteres"
              minLength={8}
              maxLength={72}
              autoComplete="new-password"
            />
          </div>

          {generatedPassword && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
              <p className="text-xs font-medium text-emerald-800">
                Copie e entregue esta senha ao usuario. Ela nao sera mostrada novamente.
              </p>
              <div className="mt-2 flex items-center gap-2">
                <code className="min-w-0 flex-1 break-all rounded bg-white px-2 py-1.5 text-sm">
                  {generatedPassword}
                </code>
                <IconActionButton
                  icon={Clipboard}
                  intent="success"
                  onClick={copiarSenha}
                  title="Copiar senha"
                />
              </div>
              {tenantReference ? (
                <button
                  type="button"
                  onClick={copiarDadosDeAcesso}
                  className="mt-3 inline-flex items-center gap-2 text-xs font-semibold text-emerald-800 underline-offset-2 hover:underline"
                >
                  <Clipboard className="h-3.5 w-3.5" aria-hidden="true" />
                  Copiar loja, usuario e nova senha
                </button>
              ) : null}
            </div>
          )}

          <p className="text-xs text-slate-500">
            Ao trocar a senha, as sessoes abertas desta conta serao encerradas.
          </p>

          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <ActionButton intent="neutral" onClick={onClose} tone="soft">
              Fechar
            </ActionButton>
            <ActionButton
              icon={RefreshCw}
              intent="warning"
              onClick={onGenerate}
              disabled={loading}
              type="button"
            >
              Gerar nova senha
            </ActionButton>
            <ActionButton icon={KeyRound} intent="create" disabled={loading} type="submit">
              Salvar
            </ActionButton>
          </div>
        </form>
      </div>
    </div>
  );
}
