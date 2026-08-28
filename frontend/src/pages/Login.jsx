import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FiAlertCircle, FiBriefcase, FiEye, FiEyeOff, FiLock, FiUser } from "react-icons/fi";
import { useAuth } from "../contexts/AuthContext";

const COREPET_LOGO = "/brand/corepet/corepet-horizontal.png";

const Login = () => {
  const [identifier, setIdentifier] = useState("");
  const [tenant, setTenant] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const loginComUsuario = Boolean(identifier.trim() && !identifier.includes("@"));

  const redirectAfterLogin = () => {
    const savedUser = localStorage.getItem("user");
    if (!savedUser) {
      navigate("/lembretes");
      return;
    }

    const user = JSON.parse(savedUser);
    const roleName = user.role?.name?.toLowerCase();

    if (roleName === "caixa") {
      navigate("/pdv");
    } else if (roleName === "admin" || roleName === "gerente") {
      navigate("/dashboard");
    } else {
      navigate("/lembretes");
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const result = await login(identifier.trim().toLowerCase(), password, tenant.trim() || null);
      if (result.success) {
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0f3f43] via-[#0f8b8d] to-[#f2a541] flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-md p-8 animate-fade-in">
        <div className="text-center mb-8">
          <img
            src={COREPET_LOGO}
            alt="CorePet"
            className="mx-auto mb-5 h-20 w-auto max-w-full object-contain"
          />
          <p className="text-gray-600 mt-2">Gestao integrada para petshops</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2 text-red-700">
            <FiAlertCircle className="flex-shrink-0 mt-0.5" />
            <div className="text-sm">
              <div>{error}</div>
              {String(error).toLowerCase().includes("email") &&
                String(error).toLowerCase().includes("confirm") && (
                  <Link
                    to={`/verificar-email?email=${encodeURIComponent(identifier)}`}
                    className="inline-block mt-2 font-semibold text-red-800 underline"
                  >
                    Confirmar e-mail ou reenviar link
                  </Link>
                )}
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              E-mail ou nome de usuario
            </label>
            <div className="relative">
              <FiUser className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={identifier}
                autoComplete="username"
                onChange={(event) => setIdentifier(event.target.value)}
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0f8b8d] focus:border-transparent outline-none transition"
                placeholder="seu@email.com ou maria.silva"
                required
              />
            </div>
          </div>

          {loginComUsuario && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Loja</label>
              <div className="relative">
                <FiBriefcase className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={tenant}
                  onChange={(event) => setTenant(event.target.value)}
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0f8b8d] focus:border-transparent outline-none transition"
                  placeholder="Nome ou codigo da loja"
                  required
                />
              </div>
              <p className="mt-1 text-xs text-gray-500">
                O administrador da loja informa este nome junto com seu usuario.
              </p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Senha</label>
            <div className="relative">
              <FiLock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                autoComplete="current-password"
                onChange={(event) => setPassword(event.target.value)}
                className="w-full pl-10 pr-12 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0f8b8d] focus:border-transparent outline-none transition"
                placeholder="Sua senha"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword((value) => !value)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition"
                aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
              >
                {showPassword ? <FiEyeOff /> : <FiEye />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#0f8b8d] hover:bg-[#0d7375] text-white font-semibold py-3 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </form>

        <div className="mt-4 text-center">
          <Link
            to="/recuperar-senha"
            className="text-sm text-[#0f8b8d] hover:text-[#0d7375] font-semibold"
          >
            Esqueci minha senha
          </Link>
        </div>

        <div className="mt-6 text-center">
          <p className="text-gray-600">
            Nao tem uma conta?{" "}
            <Link to="/register" className="text-[#0f8b8d] hover:text-[#0d7375] font-semibold">
              Criar conta
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;
