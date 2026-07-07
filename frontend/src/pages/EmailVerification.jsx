import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PawPrint } from "lucide-react";
import { FiAlertCircle, FiCheckCircle, FiMail } from "react-icons/fi";
import api from "../api";
import { buildCorePetLoginUrl } from "./emailVerificationLinks";

const EmailVerification = () => {
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState(searchParams.get("email") || "");
  const [token, setToken] = useState(searchParams.get("token") || "");
  const [status, setStatus] = useState("idle");
  const [message, setMessage] = useState("");
  const canal = (searchParams.get("canal") || "").trim().toLowerCase();
  const isAppFlow = ["app", "mobile", "aplicativo"].includes(canal);

  const verify = async (manualToken = token) => {
    if (!manualToken) {
      setStatus("idle");
      return;
    }

    setStatus("loading");
    setMessage("");
    try {
      const response = await api.post("/auth/verify-email", {
        email: email || undefined,
        token: manualToken,
      });
      setStatus("success");
      setMessage(
        isAppFlow
          ? "Email confirmado com sucesso. Abrindo o app para login..."
          : response.data?.message || "Email confirmado com sucesso.",
      );
      if (isAppFlow) {
        window.setTimeout(() => {
          window.location.assign(buildCorePetLoginUrl(email));
        }, 900);
      }
    } catch (error) {
      setStatus("error");
      setMessage(error.response?.data?.detail || "Nao foi possivel confirmar este e-mail.");
    }
  };

  const resend = async () => {
    if (!email) {
      setStatus("error");
      setMessage("Informe o e-mail para reenviar o link.");
      return;
    }

    setStatus("loading");
    setMessage("");
    try {
      const response = await api.post("/auth/resend-verification", { email });
      setStatus("resent");
      setMessage(
        response.data?.message || "Se o email precisar de confirmacao, enviaremos um novo link.",
      );
    } catch (error) {
      setStatus("error");
      setMessage(error.response?.data?.detail || "Nao foi possivel reenviar agora.");
    }
  };

  useEffect(() => {
    if (token) {
      verify(token);
    }
  }, []);

  const isSuccess = status === "success";

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 via-purple-700 to-purple-900 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
            <PawPrint className="w-8 h-8 text-blue-600" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900">Confirmar e-mail</h1>
          <p className="text-gray-600 mt-2">Ative sua conta antes de entrar no sistema.</p>
        </div>

        {message && (
          <div
            className={`mb-6 p-4 rounded-lg flex items-start gap-2 ${
              isSuccess || status === "resent"
                ? "bg-green-50 border border-green-200 text-green-700"
                : "bg-red-50 border border-red-200 text-red-700"
            }`}
          >
            {isSuccess || status === "resent" ? (
              <FiCheckCircle className="flex-shrink-0 mt-0.5" />
            ) : (
              <FiAlertCircle className="flex-shrink-0 mt-0.5" />
            )}
            <span className="text-sm">{message}</span>
          </div>
        )}

        {!isSuccess && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
              <div className="relative">
                <FiMail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                  placeholder="seu@email.com"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Codigo de confirmacao
              </label>
              <input
                type="text"
                inputMode="numeric"
                value={token}
                onChange={(event) => setToken(event.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                placeholder="Digite o codigo de 6 digitos"
              />
            </div>

            <button
              type="button"
              onClick={() => verify()}
              disabled={status === "loading"}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {status === "loading" ? "Confirmando..." : "Confirmar e-mail"}
            </button>

            <button
              type="button"
              onClick={resend}
              disabled={status === "loading"}
              className="w-full border border-gray-300 hover:bg-gray-50 text-gray-700 font-semibold py-3 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Reenviar link
            </button>
          </div>
        )}

        <div className="mt-6 text-center">
          {isSuccess && isAppFlow ? (
            <a
              href={buildCorePetLoginUrl(email)}
              className="text-blue-600 hover:text-blue-700 font-semibold"
            >
              Abrir app para login
            </a>
          ) : (
            <Link to="/login" className="text-blue-600 hover:text-blue-700 font-semibold">
              Ir para login
            </Link>
          )}
        </div>
      </div>
    </div>
  );
};

export default EmailVerification;
