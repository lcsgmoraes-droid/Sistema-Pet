import { useEffect, useState } from "react";
import { FiAlertCircle, FiEye, FiEyeOff, FiLock, FiMail, FiShield } from "react-icons/fi";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { usePlatformAuth } from "../contexts/PlatformAuthContext";

export default function PlatformLogin() {
  const { isAuthenticated, login } = usePlatformAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (isAuthenticated) navigate("/ops", { replace: true });
  }, [isAuthenticated, navigate]);

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const result = await login(email.trim().toLowerCase(), password);
    setLoading(false);
    if (result.success) {
      const destination = String(location.state?.from || "/ops");
      navigate(destination.startsWith("/ops") ? destination : "/ops", { replace: true });
      return;
    }
    setError(result.error);
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-10 text-slate-950">
      <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-white p-8 shadow-2xl">
        <div className="text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-xl bg-blue-600 text-white">
            <FiShield className="h-7 w-7" />
          </div>
          <h1 className="mt-4 text-2xl font-bold">CorePet Ops</h1>
          <p className="mt-2 text-sm text-slate-500">
            Acesso exclusivo do administrador da plataforma
          </p>
        </div>

        {error ? (
          <div className="mt-6 flex gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
            <FiAlertCircle className="mt-0.5 shrink-0" />
            {error}
          </div>
        ) : null}

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <label className="block text-sm font-semibold text-slate-700">
            E-mail administrativo
            <span className="relative mt-2 block">
              <FiMail className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="username"
                required
                className="h-12 w-full rounded-lg border border-slate-300 pl-10 pr-3 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              />
            </span>
          </label>

          <label className="block text-sm font-semibold text-slate-700">
            Senha
            <span className="relative mt-2 block">
              <FiLock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                required
                className="h-12 w-full rounded-lg border border-slate-300 pl-10 pr-11 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              />
              <button
                type="button"
                onClick={() => setShowPassword((current) => !current)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400"
                aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
              >
                {showPassword ? <FiEyeOff /> : <FiEye />}
              </button>
            </span>
          </label>

          <button
            type="submit"
            disabled={loading}
            className="h-12 w-full rounded-lg bg-blue-600 font-bold text-white transition hover:bg-blue-700 disabled:opacity-60"
          >
            {loading ? "Entrando..." : "Entrar no CorePet Ops"}
          </button>
        </form>

        <div className="mt-5 space-y-3 text-center text-sm">
          <Link to="/ops/recuperar-senha" className="block font-semibold text-blue-700">
            Esqueci minha senha administrativa
          </Link>
          <Link to="/login" className="block text-slate-500 hover:text-slate-700">
            Acessar uma empresa cliente
          </Link>
        </div>
      </div>
    </div>
  );
}
