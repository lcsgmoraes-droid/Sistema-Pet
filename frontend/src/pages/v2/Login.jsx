import { PawPrint } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FiAlertCircle, FiBriefcase } from "react-icons/fi";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import InputSenha from "../../components/v2/InputSenha/InputSenha";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import { getDefaultAuthenticatedRoute } from "../../auth/userRole";
import { useAuth } from "../../contexts/AuthContext";

const COREPET_LOGO = "/brand/corepet/corepet-horizontal.png";

const Login = () => {
  const [identifier, setIdentifier] = useState("");
  const [tenant, setTenant] = useState("");
  const [password, setPassword] = useState("");
  const [availableTenants, setAvailableTenants] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { cancelTenantSelection, login, selectTenant } = useAuth();
  const navigate = useNavigate();
  const loginComUsuario = Boolean(identifier.trim() && !identifier.includes("@"));

  const redirectAfterLogin = () => {
    const savedUser = localStorage.getItem("user");
    if (!savedUser) {
      navigate("/lembretes");
      return;
    }

    navigate(getDefaultAuthenticatedRoute(JSON.parse(savedUser)));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const result = await login(identifier.trim().toLowerCase(), password, tenant.trim() || null);
      if (result.success && result.requiresTenantSelection) {
        setAvailableTenants(result.tenants);
      } else if (result.success) {
        redirectAfterLogin();
      } else {
        setError(result.error || "Erro desconhecido ao fazer login");
      }
    } catch {
      setError("Erro inesperado ao fazer login");
    } finally {
      setLoading(false);
    }
  };

  const handleTenantSelection = async (tenantId) => {
    setError("");
    setLoading(true);

    const result = await selectTenant(tenantId);
    if (result.success) {
      redirectAfterLogin();
    } else {
      setError(result.error || "Erro ao selecionar empresa");
    }

    setLoading(false);
  };

  const handleAnotherAccount = async () => {
    setLoading(true);
    await cancelTenantSelection();
    setAvailableTenants([]);
    setPassword("");
    setError("");
    setLoading(false);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-[#0f3f43] via-[#0f8b8d] to-[#f2a541] p-4">
      <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-2xl">
        <div className="mb-8 text-center">
          <img
            src={COREPET_LOGO}
            alt="CorePet"
            className="mx-auto mb-5 h-20 w-auto max-w-full object-contain"
          />
          <p className="mt-2 text-slate-600">Gestão integrada para petshops</p>
        </div>

        {error ? (
          <div className="mb-6 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
            <FiAlertCircle className="mt-0.5 shrink-0" />
            <div className="text-sm">
              <div>{error}</div>
              {String(error).toLowerCase().includes("email") &&
                String(error).toLowerCase().includes("confirm") && (
                  <Link
                    to={`/verificar-email?email=${encodeURIComponent(identifier)}`}
                    className="mt-2 inline-block font-semibold text-red-800 underline"
                  >
                    Confirmar e-mail ou reenviar link
                  </Link>
                )}
            </div>
          </div>
        ) : null}

        {availableTenants.length > 0 ? (
          <div className="space-y-4">
            <div className="rounded-xl border border-[#0f8b8d]/20 bg-[#0f8b8d]/5 p-4">
              <h1 className="text-xl font-bold text-slate-900">Escolha a empresa</h1>
              <p className="mt-1 text-sm text-slate-600">
                Seu acesso pertence a mais de uma empresa. Selecione onde deseja trabalhar agora.
              </p>
            </div>

            <div className="space-y-3">
              {availableTenants.map((tenantOption) => (
                <button
                  key={tenantOption.id}
                  type="button"
                  disabled={loading}
                  onClick={() => handleTenantSelection(tenantOption.id)}
                  className="flex w-full items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 text-left transition hover:border-[#0f8b8d] hover:bg-[#0f8b8d]/5 focus:outline-none focus:ring-2 focus:ring-[#0f8b8d] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[#0f8b8d]/10 text-[#0f8b8d]">
                    <FiBriefcase className="text-xl" />
                  </span>
                  <span>
                    <span className="block font-semibold text-slate-900">{tenantOption.name}</span>
                    <span className="block text-xs text-slate-500">Entrar nesta empresa</span>
                  </span>
                </button>
              ))}
            </div>

            <button
              type="button"
              disabled={loading}
              onClick={handleAnotherAccount}
              className="w-full text-sm font-semibold text-[#0f8b8d] hover:text-[#0d7375] disabled:opacity-50"
            >
              Entrar com outra conta
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <InputTexto
              id="login-identificador"
              label="E-mail ou nome de usuário"
              placeholder="seu@email.com ou maria.silva"
              value={identifier}
              onChange={setIdentifier}
              autoComplete="username"
              required
            />

            {loginComUsuario ? (
              <InputTexto
                id="login-loja"
                label="Loja"
                placeholder="Nome ou código da loja"
                value={tenant}
                onChange={setTenant}
                help="O administrador da loja informa este nome junto com seu usuário."
                required
              />
            ) : null}

            <InputSenha
              id="login-senha"
              value={password}
              onChange={setPassword}
              autoComplete="current-password"
              required
            />

            <BotaoInteracao
              icon={PawPrint}
              disabled={loading}
              loading={loading}
              tamanho="grande"
              larguraTotal
              type="submit"
            >
              {loading ? "Entrando..." : "Entrar"}
            </BotaoInteracao>
          </form>
        )}

        {availableTenants.length === 0 ? (
          <>
            <div className="mt-4 text-center">
              <Link
                to="/recuperar-senha"
                className="text-sm font-semibold text-blue-600 hover:text-blue-700"
              >
                Esqueci minha senha
              </Link>
            </div>

            <div className="mt-6 text-center">
              <p className="text-slate-600">
                Não tem uma conta?{" "}
                <Link to="/register" className="font-semibold text-blue-600 hover:text-blue-700">
                  Criar conta
                </Link>
              </p>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
};

export default Login;
