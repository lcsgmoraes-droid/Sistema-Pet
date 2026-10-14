import { Link } from "react-router-dom";

export default function UnknownFailuresNotice({ summary, onShowEvents }) {
  const count = Number(summary?.unknown_status_failures || 0);
  const incomplete = Number(summary?.response_failures || 0);
  if (!count && !incomplete) return null;

  const actionClass = "mt-2 inline-block font-semibold underline underline-offset-2";
  return (
    <div
      role="status"
      className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
    >
      {count > 0 ? (
        <div>
          <strong>{count.toLocaleString("pt-BR")} exceções sem status confirmado.</strong> A
          resposta HTTP não foi registrada nesses eventos. Eles precisam de investigação e aparecem
          separados dos erros 5xx confirmados.
        </div>
      ) : null}
      {incomplete > 0 ? (
        <div>
          <strong>{incomplete.toLocaleString("pt-BR")} respostas interrompidas.</strong> Uma falha
          impediu a conclusão da resposta.
        </div>
      ) : null}
      <div>
        {onShowEvents ? (
          <button type="button" onClick={onShowEvents} className={actionClass}>
            Ver todas as ocorrências
          </button>
        ) : (
          <Link to="/ops/incidentes" className={actionClass}>
            Investigar ocorrências
          </Link>
        )}
      </div>
    </div>
  );
}
