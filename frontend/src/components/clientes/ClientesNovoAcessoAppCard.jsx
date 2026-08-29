import { FiSmartphone, FiUserCheck } from "react-icons/fi";
import { useAuth } from "../../contexts/AuthContext";
import { canManageAppAccessProfiles } from "../../utils/appAccessProfiles";

const PERFIS_APP = [
  { value: "cliente", label: "Cliente", description: "Compras, pedidos e dados do cliente" },
  {
    value: "gestor",
    label: "Gestor",
    description: "Indicadores financeiros e gerenciais, somente para consulta",
  },
  {
    value: "funcionario",
    label: "Funcionario",
    description: "Rotinas internas liberadas para funcionarios",
  },
  {
    value: "banho_tosa",
    label: "Banho & Tosa",
    description: "Agenda, check-in e andamento dos pets",
  },
  { value: "entregador", label: "Entregador", description: "Entregas e rotas do app" },
  {
    value: "taxi_dog",
    label: "Taxi Dog",
    description: "Coleta, rota e devolucao dos pets",
  },
  {
    value: "veterinario",
    label: "Veterinario",
    description: "Agenda e recursos veterinarios",
  },
];

export default function ClientesNovoAcessoAppCard({
  formData,
  setFormData,
  usuarios = [],
  roles = [],
  loadingUsuarios = false,
}) {
  const { user } = useAuth();
  const canManage = canManageAppAccessProfiles(user);
  const perfisSelecionados = formData.app_access_profiles || [];
  const perfisObrigatorios = new Set();
  if (["cliente", "funcionario", "veterinario"].includes(formData.tipo_cadastro)) {
    perfisObrigatorios.add(formData.tipo_cadastro);
  }
  if (formData.is_entregador) perfisObrigatorios.add("entregador");

  const alternarPerfil = (profileType) => {
    const atuais = new Set(perfisSelecionados);
    if (atuais.has(profileType)) atuais.delete(profileType);
    else atuais.add(profileType);
    setFormData((prev) => ({ ...prev, app_access_profiles: Array.from(atuais) }));
  };

  const sugerirUsername = () =>
    String(formData.nome || "usuario")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, ".")
      .replace(/^\.+|\.+$/g, "")
      .slice(0, 40) || "usuario";

  const roleInicial = () =>
    roles.find((role) => String(role.nome || "").toLowerCase() === "caixa")?.role_id ||
    roles[0]?.role_id ||
    null;

  const selecionarConta = (value) => {
    if (value === "__new__") {
      setFormData((prev) => ({
        ...prev,
        auth_user_id: null,
        app_login: {
          username: sugerirUsername(),
          email: prev.email || "",
          password: "",
          role_id: roleInicial(),
        },
      }));
      return;
    }
    setFormData((prev) => ({
      ...prev,
      auth_user_id: value ? Number(value) : null,
      app_login: null,
    }));
  };

  const atualizarNovaConta = (field, value) =>
    setFormData((prev) => ({
      ...prev,
      app_login: { ...(prev.app_login || {}), [field]: value },
    }));

  if (!canManage) return null;

  return (
    <section className="mt-5 rounded-lg border border-indigo-200 bg-indigo-50/60 p-4">
      <div className="mb-3 flex items-start gap-3">
        <div className="rounded-full bg-white p-2 text-indigo-600">
          <FiSmartphone size={18} aria-hidden="true" />
        </div>
        <div>
          <h3 className="font-semibold text-slate-900">Acesso desta pessoa ao app</h3>
          <p className="mt-1 text-xs text-slate-600">
            Vincule a conta usada no login e marque os tipos de acesso. Isso nao permite entrar como
            outra pessoa.
          </p>
          <p className="mt-1 text-xs font-medium text-indigo-700">
            Somente administradores podem alterar estes acessos.
          </p>
        </div>
      </div>

      <label className="block text-sm font-medium text-slate-700" htmlFor="auth-user-id">
        Conta que fara o login
      </label>
      <select
        id="auth-user-id"
        className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
        disabled={loadingUsuarios}
        value={formData.app_login ? "__new__" : formData.auth_user_id || ""}
        onChange={(event) => selecionarConta(event.target.value)}
      >
        <option value="">
          {loadingUsuarios ? "Carregando contas..." : "Sem conta de acesso vinculada"}
        </option>
        {roles.length > 0 && <option value="__new__">Criar nova conta com usuario e senha</option>}
        {usuarios.map((usuario) => (
          <option key={usuario.user_id} value={usuario.user_id} disabled={!usuario.disponivel}>
            {usuario.nome || usuario.username || usuario.email} —{" "}
            {usuario.username || usuario.email} ({usuario.perfil_sistema})
            {!usuario.disponivel ? ` — ja vinculada a ${usuario.pessoa_vinculada_nome}` : ""}
          </option>
        ))}
      </select>

      {formData.app_login && (
        <div className="mt-3 grid gap-3 rounded-lg border border-indigo-200 bg-white p-3 sm:grid-cols-2">
          <div>
            <label
              className="block text-xs font-medium text-slate-700"
              htmlFor="app-login-username"
            >
              Nome de usuario
            </label>
            <input
              id="app-login-username"
              value={formData.app_login.username || ""}
              onChange={(event) => atualizarNovaConta("username", event.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              placeholder="maria.silva"
              autoCapitalize="none"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700" htmlFor="app-login-email">
              E-mail para recuperacao (opcional)
            </label>
            <input
              id="app-login-email"
              type="email"
              value={formData.app_login.email || ""}
              onChange={(event) => atualizarNovaConta("email", event.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              placeholder="Pode ficar vazio"
              autoComplete="email"
            />
          </div>
          <div>
            <label
              className="block text-xs font-medium text-slate-700"
              htmlFor="app-login-password"
            >
              Senha inicial
            </label>
            <input
              id="app-login-password"
              type="password"
              minLength={8}
              maxLength={72}
              value={formData.app_login.password || ""}
              onChange={(event) => atualizarNovaConta("password", event.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              placeholder="Minimo 8 caracteres"
              autoComplete="new-password"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700" htmlFor="app-login-role">
              Perfil no sistema
            </label>
            <select
              id="app-login-role"
              value={formData.app_login.role_id || ""}
              onChange={(event) =>
                atualizarNovaConta(
                  "role_id",
                  event.target.value ? Number(event.target.value) : null,
                )
              }
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              required
            >
              <option value="">Selecione...</option>
              {roles.map((role) => (
                <option key={role.role_id} value={role.role_id}>
                  {role.nome}
                </option>
              ))}
            </select>
          </div>
          <p className="text-xs text-slate-500 sm:col-span-2">
            Sem e-mail, a senha podera ser redefinida pelo administrador na tela de usuarios.
          </p>
        </div>
      )}

      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        {PERFIS_APP.map((perfil) => {
          const obrigatorio = perfisObrigatorios.has(perfil.value);
          const selecionado = obrigatorio || perfisSelecionados.includes(perfil.value);
          return (
            <label
              key={perfil.value}
              className={`flex cursor-pointer items-start gap-2 rounded-lg border p-3 transition-colors ${
                selecionado
                  ? "border-indigo-400 bg-white text-indigo-950"
                  : "border-slate-200 bg-white/70 text-slate-700"
              }`}
            >
              <input
                type="checkbox"
                className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                checked={selecionado}
                disabled={obrigatorio}
                onChange={() => alternarPerfil(perfil.value)}
              />
              <span>
                <span className="flex items-center gap-1 text-sm font-medium">
                  <FiUserCheck aria-hidden="true" /> {perfil.label}
                </span>
                <span className="mt-0.5 block text-xs text-slate-500">{perfil.description}</span>
                {obrigatorio && (
                  <span className="mt-1 block text-[11px] font-medium text-indigo-600">
                    Incluido pelo tipo deste cadastro
                  </span>
                )}
              </span>
            </label>
          );
        })}
      </div>

      {!formData.auth_user_id &&
        !formData.app_login &&
        (perfisSelecionados.length > 0 || perfisObrigatorios.size > 0) && (
          <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
            Os perfis ficam preparados, mas o acesso so sera ativado depois que uma conta de login
            for vinculada.
          </p>
        )}
    </section>
  );
}
