import { FiSmartphone, FiUserCheck } from "react-icons/fi";

const PERFIS_APP = [
  { value: "cliente", label: "Cliente", description: "Compras, pedidos e dados do cliente" },
  {
    value: "funcionario",
    label: "Funcionario",
    description: "Rotinas internas liberadas para funcionarios",
  },
  { value: "entregador", label: "Entregador", description: "Entregas e rotas do app" },
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
  loadingUsuarios = false,
}) {
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
        </div>
      </div>

      <label className="block text-sm font-medium text-slate-700" htmlFor="auth-user-id">
        Conta que fara o login
      </label>
      <select
        id="auth-user-id"
        className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
        disabled={loadingUsuarios}
        value={formData.auth_user_id || ""}
        onChange={(event) =>
          setFormData((prev) => ({
            ...prev,
            auth_user_id: event.target.value ? Number(event.target.value) : null,
          }))
        }
      >
        <option value="">
          {loadingUsuarios ? "Carregando contas..." : "Sem conta de acesso vinculada"}
        </option>
        {usuarios.map((usuario) => (
          <option key={usuario.user_id} value={usuario.user_id} disabled={!usuario.disponivel}>
            {usuario.nome || usuario.email} — {usuario.email} ({usuario.perfil_sistema})
            {!usuario.disponivel ? ` — ja vinculada a ${usuario.pessoa_vinculada_nome}` : ""}
          </option>
        ))}
      </select>

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

      {!formData.auth_user_id && (perfisSelecionados.length > 0 || perfisObrigatorios.size > 0) && (
        <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          Os perfis ficam preparados, mas o acesso so sera ativado depois que uma conta de login for
          vinculada.
        </p>
      )}
    </section>
  );
}
