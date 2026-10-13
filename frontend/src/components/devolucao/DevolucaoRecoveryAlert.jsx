import { AlertCircle, ExternalLink } from "lucide-react";

export default function DevolucaoRecoveryAlert({ recuperacao, loading, onRecuperar }) {
  if (!recuperacao) return null;
  return (
    <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
      <div className="flex items-start gap-2">
        <AlertCircle aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0" />
        <div className="min-w-0">
          <p className="text-sm font-medium">{recuperacao.mensagem}</p>
          <p className="mt-2 text-sm">{recuperacao.orientacao}</p>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {recuperacao.acoes.map((acao) =>
          acao.href ? (
            <a
              key={acao.id}
              href={acao.href}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-lg border border-red-300 bg-white px-3 py-2 text-sm font-semibold hover:bg-red-100 focus-visible:ring-2 focus-visible:ring-red-500"
            >
              {acao.label}
              <ExternalLink aria-hidden="true" className="h-4 w-4" />
            </a>
          ) : (
            <button
              key={acao.id}
              type="button"
              disabled={loading}
              onClick={() => onRecuperar(acao.id)}
              className="rounded-lg border border-red-300 bg-white px-3 py-2 text-sm font-semibold hover:bg-red-100 focus-visible:ring-2 focus-visible:ring-red-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {acao.label}
            </button>
          ),
        )}
      </div>
    </div>
  );
}
