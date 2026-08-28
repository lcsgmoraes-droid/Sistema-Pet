import { Check, Copy, KeyRound, X } from "lucide-react";
import { useState } from "react";
import { formatInitialAccessCredentials } from "../../utils/usuarioAcessoInicial";
import ActionButton from "../ui/ActionButton";
import IconActionButton from "../ui/IconActionButton";

function CredentialRow({ label, value, onCopy, copied }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <div className="mt-1 flex items-center gap-2">
        <code className="min-w-0 flex-1 break-all text-sm font-semibold text-slate-950">
          {value}
        </code>
        <IconActionButton
          icon={copied ? Check : Copy}
          intent="success"
          onClick={onCopy}
          title={copied ? `${label} copiado` : `Copiar ${label.toLowerCase()}`}
        />
      </div>
    </div>
  );
}

export default function UsuarioAcessoInicialModal({ credentials, onClose }) {
  const [copiado, setCopiado] = useState("");

  if (!credentials) return null;

  const copiar = async (value, field) => {
    await navigator.clipboard.writeText(value);
    setCopiado(field);
    window.setTimeout(() => setCopiado(""), 2000);
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/55 p-4">
      <div
        className="w-full max-w-md rounded-xl border border-slate-200 bg-white shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="acesso-inicial-title"
      >
        <div className="flex items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
          <div className="flex items-start gap-3">
            <div className="rounded-lg bg-emerald-100 p-2 text-emerald-700">
              <KeyRound className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h2 id="acesso-inicial-title" className="text-lg font-semibold text-slate-950">
                Acesso criado
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                {credentials.personName || "Entregue estes dados ao usuario."}
              </p>
            </div>
          </div>
          <IconActionButton
            icon={X}
            intent="neutral"
            onClick={onClose}
            title="Fechar"
            tone="ghost"
          />
        </div>

        <div className="space-y-3 px-5 py-4">
          <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            Copie a senha inicial agora. Ela nao sera mostrada novamente depois que esta janela for
            fechada.
          </p>

          <CredentialRow
            label="Loja"
            value={credentials.tenant}
            copied={copiado === "tenant"}
            onCopy={() => copiar(credentials.tenant, "tenant")}
          />
          <CredentialRow
            label="Nome de usuario"
            value={credentials.username}
            copied={copiado === "username"}
            onCopy={() => copiar(credentials.username, "username")}
          />
          <CredentialRow
            label="Senha inicial"
            value={credentials.password}
            copied={copiado === "password"}
            onCopy={() => copiar(credentials.password, "password")}
          />

          <div className="flex flex-col-reverse gap-2 pt-1 sm:flex-row sm:justify-end">
            <ActionButton intent="neutral" onClick={onClose} tone="soft">
              Fechar
            </ActionButton>
            <ActionButton
              icon={copiado === "all" ? Check : Copy}
              intent="success"
              onClick={() => copiar(formatInitialAccessCredentials(credentials), "all")}
            >
              {copiado === "all" ? "Dados copiados" : "Copiar todos os dados"}
            </ActionButton>
          </div>
        </div>
      </div>
    </div>
  );
}
