import { useState } from "react";
import { createPortal } from "react-dom";
import api from "../../api";
import { clearAuthTokens } from "../../auth/tokenStorage";

export default function ChangePasswordModal({ onClose }) {
  const [senhaAtual, setSenhaAtual] = useState("");
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);

  const salvar = async (evento) => {
    evento.preventDefault();
    setErro("");
    if (novaSenha.length < 8) {
      setErro("A nova senha deve ter pelo menos 8 caracteres.");
      return;
    }
    if (novaSenha !== confirmacao) {
      setErro("A confirmação não corresponde à nova senha.");
      return;
    }

    setSalvando(true);
    try {
      await api.post("/auth/change-password", {
        senha_atual: senhaAtual,
        nova_senha: novaSenha,
      });
      clearAuthTokens();
      localStorage.removeItem("tenants");
      localStorage.removeItem("user");
      localStorage.removeItem("selectedTenant");
      window.location.assign("/login?senha=alterada");
    } catch (error) {
      const detalhe = error.response?.data?.detail;
      setErro(
        typeof detalhe === "string"
          ? detalhe
          : "Não foi possível alterar a senha. Tente novamente.",
      );
      setSalvando(false);
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="change-password-title"
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl dark:bg-slate-900"
      >
        <h2
          id="change-password-title"
          className="text-xl font-semibold text-slate-900 dark:text-white"
        >
          Alterar minha senha
        </h2>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Informe sua senha atual e escolha uma nova senha. Depois, entre novamente em seus
          dispositivos.
        </p>
        <form onSubmit={salvar} className="mt-5 space-y-4">
          {[
            ["senha-atual", "Senha atual", senhaAtual, setSenhaAtual, "current-password"],
            ["nova-senha", "Nova senha", novaSenha, setNovaSenha, "new-password"],
            [
              "confirmar-senha",
              "Confirmar nova senha",
              confirmacao,
              setConfirmacao,
              "new-password",
            ],
          ].map(([id, label, value, onChange, autoComplete]) => (
            <label
              key={id}
              htmlFor={id}
              className="block text-sm font-medium text-slate-700 dark:text-slate-200"
            >
              {label}
              <input
                id={id}
                type="password"
                value={value}
                onChange={(evento) => onChange(evento.target.value)}
                autoComplete={autoComplete}
                required
                disabled={salvando}
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-[#0f8b8d] focus:ring-2 focus:ring-[#0f8b8d]/20 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
              />
            </label>
          ))}
          {erro && (
            <p role="alert" className="text-sm text-red-600 dark:text-red-300">
              {erro}
            </p>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={salvando}
              className="rounded-lg px-4 py-2 text-slate-700 hover:bg-slate-100 disabled:opacity-50 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={salvando}
              className="rounded-lg bg-[#0f5f63] px-4 py-2 font-medium text-white hover:bg-[#0d7375] disabled:opacity-50"
            >
              {salvando ? "Salvando..." : "Salvar nova senha"}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body,
  );
}
