import { useEffect, useState } from "react";
import { FiAlertCircle, FiLock, FiMail, FiShield } from "react-icons/fi";
import { Link, useSearchParams } from "react-router-dom";

import platformApi from "../platformApi";

const EMPTY_FORM = { email: "", token: "", password: "", confirmation: "" };

export default function PlatformForgotPassword() {
  const [searchParams] = useSearchParams();
  const [form, setForm] = useState(EMPTY_FORM);
  const [step, setStep] = useState("request");
  const [tokenFromLink, setTokenFromLink] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    const email = (searchParams.get("email") || "").trim();
    const token = (searchParams.get("token") || "").trim();
    if (email || token) {
      setForm((current) => ({ ...current, email, token }));
      setTokenFromLink(Boolean(token));
      setStep("reset");
    }
  }, [searchParams]);

  async function requestReset(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      const response = await platformApi.post("/platform-auth/forgot-password", {
        email: form.email.trim().toLowerCase(),
      });
      setSuccess(
        `Se o e-mail estiver cadastrado, o link e o código chegarão em instantes e expirarão em ${response.data.expires_in_minutes} minutos.`,
      );
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Não foi possível enviar o e-mail agora.");
    } finally {
      setLoading(false);
    }
  }

  async function resetPassword(event) {
    event.preventDefault();
    if (form.password.length < 8) {
      setError("A nova senha deve ter pelo menos 8 caracteres.");
      return;
    }
    if (form.password !== form.confirmation) {
      setError("A confirmação da senha não confere.");
      return;
    }
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      await platformApi.post("/platform-auth/reset-password", {
        email: form.email.trim().toLowerCase(),
        token: form.token.trim(),
        nova_senha: form.password,
      });
      setSuccess("Senha administrativa atualizada. Volte ao login do CorePet Ops.");
      setForm((current) => ({ ...current, token: "", password: "", confirmation: "" }));
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Não foi possível redefinir a senha.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-10">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-2xl">
        <div className="text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-xl bg-blue-600 text-white">
            <FiShield className="h-7 w-7" />
          </div>
          <h1 className="mt-4 text-2xl font-bold text-slate-950">Recuperar acesso Ops</h1>
          <p className="mt-2 text-sm text-slate-500">
            Recuperação exclusiva do administrador da plataforma
          </p>
        </div>

        {error ? (
          <div className="mt-5 flex gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
            <FiAlertCircle className="mt-0.5 shrink-0" /> {error}
          </div>
        ) : null}
        {success ? (
          <div className="mt-5 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
            {success}
          </div>
        ) : null}

        <form
          onSubmit={step === "request" ? requestReset : resetPassword}
          className="mt-6 space-y-4"
        >
          <label className="block text-sm font-semibold text-slate-700">
            E-mail administrativo
            <span className="relative mt-2 block">
              <FiMail className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="email"
                value={form.email}
                onChange={(event) =>
                  setForm((current) => ({ ...current, email: event.target.value }))
                }
                required
                className="h-12 w-full rounded-lg border border-slate-300 pl-10 pr-3"
              />
            </span>
          </label>

          {step === "reset" ? (
            <>
              {!tokenFromLink ? (
                <label className="block text-sm font-semibold text-slate-700">
                  Código de recuperação
                  <input
                    value={form.token}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, token: event.target.value }))
                    }
                    required
                    className="mt-2 h-12 w-full rounded-lg border border-slate-300 px-3"
                  />
                </label>
              ) : null}
              {[
                ["password", "Nova senha"],
                ["confirmation", "Confirmar nova senha"],
              ].map(([field, label]) => (
                <label key={field} className="block text-sm font-semibold text-slate-700">
                  {label}
                  <span className="relative mt-2 block">
                    <FiLock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input
                      type="password"
                      value={form[field]}
                      onChange={(event) =>
                        setForm((current) => ({ ...current, [field]: event.target.value }))
                      }
                      minLength={8}
                      required
                      className="h-12 w-full rounded-lg border border-slate-300 pl-10 pr-3"
                    />
                  </span>
                </label>
              ))}
            </>
          ) : null}

          <button
            type="submit"
            disabled={loading}
            className="h-12 w-full rounded-lg bg-blue-600 font-bold text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {loading
              ? "Processando..."
              : step === "request"
                ? "Enviar instruções"
                : "Salvar nova senha"}
          </button>
        </form>

        <div className="mt-5 space-y-3 text-center text-sm">
          <button
            type="button"
            onClick={() => {
              setStep(step === "request" ? "reset" : "request");
              setTokenFromLink(false);
              setError("");
              setSuccess("");
            }}
            className="block w-full font-semibold text-blue-700"
          >
            {step === "request" ? "Já tenho o código" : "Solicitar novo link"}
          </button>
          <Link to="/ops/login" className="block text-slate-500">
            Voltar ao login do CorePet Ops
          </Link>
        </div>
      </div>
    </div>
  );
}
