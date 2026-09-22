import { FiSmartphone, FiUserCheck } from "react-icons/fi";
import { useAuth } from "../../contexts/AuthContext";
import { canManageAppAccessProfiles } from "../../utils/appAccessProfiles";
import InputCheckTexto from "../v2/InputCheckTexto/InputCheckTexto";
import InputCombobox from "../v2/InputCombobox/InputCombobox";
import InputSenha from "../v2/InputSenha/InputSenha";
import InputTexto from "../v2/InputTexto/InputTexto";

const PERFIS_APP = [
  { value: "cliente", label: "Cliente", description: "Compras, pedidos e dados do cliente" },
  {
    value: "gestor",
    label: "Gestor",
    description: "Indicadores financeiros e gerenciais, somente para consulta",
  },
  {
    value: "funcionario",
    label: "Funcionário",
    description: "Rotinas internas liberadas para funcionários",
  },
  {
    value: "banho_tosa",
    label: "Banho & Tosa",
    description: "Agenda, check-in e andamento dos pets",
  },
  { value: "entregador", label: "Entregador", description: "Entregas e rotas do app" },
  { value: "taxi_dog", label: "Taxi Dog", description: "Coleta, rota e devolução dos pets" },
  { value: "veterinario", label: "Veterinário", description: "Agenda e recursos veterinários" },
];

export default function ClientePessoaAcessoAppCard({
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
      .replace(/[̀-ͯ]/g, "")
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

  const opcoesConta = [
    { value: "", label: loadingUsuarios ? "Carregando contas..." : "Sem conta de acesso vinculada" },
    ...(roles.length > 0 ? [{ value: "__new__", label: "Criar nova conta com usuário e senha" }] : []),
    ...usuarios
      .filter((usuario) => usuario.disponivel)
      .map((usuario) => ({
        value: String(usuario.user_id),
        label: `${usuario.nome || usuario.username || usuario.email} — ${
          usuario.username || usuario.email
        } (${usuario.perfil_sistema})`,
      })),
  ];

  const opcoesRole = roles.map((role) => ({ value: String(role.role_id), label: role.nome }));

  return (
    <section className="mt-5 rounded-lg border border-indigo-200 bg-indigo-50/60 p-4 dark:border-indigo-500/30 dark:bg-indigo-500/10">
      <div className="mb-3 flex items-start gap-3">
        <div className="rounded-full bg-white p-2 text-indigo-600 dark:bg-slate-900 dark:text-indigo-300">
          <FiSmartphone size={18} aria-hidden="true" />
        </div>
        <div>
          <h3 className="font-semibold text-slate-900 dark:text-slate-100">
            Acesso desta pessoa ao app
          </h3>
          <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
            Vincule a conta usada no login e marque os tipos de acesso. Isso não permite entrar
            como outra pessoa.
          </p>
          <p className="mt-1 text-xs font-medium text-indigo-700 dark:text-indigo-300">
            Somente administradores podem alterar estes acessos.
          </p>
        </div>
      </div>

      <InputCombobox
        id="pessoa-acesso-conta"
        label="Conta que fará o login"
        disabled={loadingUsuarios}
        opcoes={opcoesConta}
        permitirLimpar={false}
        value={formData.app_login ? "__new__" : String(formData.auth_user_id || "")}
        onChange={selecionarConta}
      />

      {formData.app_login ? (
        <div className="mt-3 grid gap-3 rounded-lg border border-indigo-200 bg-white p-3 dark:border-indigo-500/30 dark:bg-slate-900 sm:grid-cols-2">
          <InputTexto
            id="pessoa-app-login-username"
            label="Nome de usuário"
            required
            value={formData.app_login.username || ""}
            onChange={(username) => atualizarNovaConta("username", username)}
            placeholder="maria.silva"
          />

          <InputTexto
            id="pessoa-app-login-email"
            label="E-mail para recuperação (opcional)"
            type="email"
            value={formData.app_login.email || ""}
            onChange={(email) => atualizarNovaConta("email", email)}
            placeholder="Pode ficar vazio"
          />

          <InputSenha
            id="pessoa-app-login-password"
            label="Senha inicial"
            required
            value={formData.app_login.password || ""}
            onChange={(password) => atualizarNovaConta("password", password)}
            placeholder="Mínimo 8 caracteres"
          />

          <InputCombobox
            id="pessoa-app-login-role"
            label="Perfil no sistema"
            required
            opcoes={opcoesRole}
            permitirLimpar={false}
            value={String(formData.app_login.role_id || "")}
            onChange={(role_id) => atualizarNovaConta("role_id", role_id ? Number(role_id) : null)}
          />

          <p className="text-xs text-slate-500 sm:col-span-2">
            Sem e-mail, a senha poderá ser redefinida pelo administrador na tela de usuários.
          </p>
        </div>
      ) : null}

      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        {PERFIS_APP.map((perfil) => {
          const obrigatorio = perfisObrigatorios.has(perfil.value);
          const selecionado = obrigatorio || perfisSelecionados.includes(perfil.value);
          return (
            <div
              key={perfil.value}
              className={`rounded-lg border p-3 transition-colors ${
                selecionado
                  ? "border-indigo-400 bg-white dark:bg-slate-900"
                  : "border-slate-200 bg-white/70 dark:border-slate-700 dark:bg-slate-900/60"
              }`}
            >
              <InputCheckTexto
                id={`pessoa-perfil-${perfil.value}`}
                checked={selecionado}
                disabled={obrigatorio}
                onChange={() => alternarPerfil(perfil.value)}
              >
                <span className="flex items-center gap-1 text-sm font-medium text-slate-900 dark:text-slate-100">
                  <FiUserCheck aria-hidden="true" /> {perfil.label}
                </span>
                <span className="mt-0.5 block text-xs text-slate-500">{perfil.description}</span>
                {obrigatorio ? (
                  <span className="mt-1 block text-[11px] font-medium text-indigo-600 dark:text-indigo-300">
                    Incluído pelo tipo deste cadastro
                  </span>
                ) : null}
              </InputCheckTexto>
            </div>
          );
        })}
      </div>

      {!formData.auth_user_id &&
      !formData.app_login &&
      (perfisSelecionados.length > 0 || perfisObrigatorios.size > 0) ? (
        <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
          Os perfis ficam preparados, mas o acesso só será ativado depois que uma conta de login
          for vinculada.
        </p>
      ) : null}
    </section>
  );
}
