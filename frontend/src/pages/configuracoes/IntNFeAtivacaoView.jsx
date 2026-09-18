import { FiCheckCircle, FiFileText, FiRefreshCw } from "react-icons/fi";
import { Link } from "react-router-dom";

const buttonClass =
  "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-500";

function nextAction(data) {
  const pendingCompanyData = data?.pendencias || [];

  if (pendingCompanyData.length) {
    return {
      title: "Complete os dados da empresa",
      description: "Corrija os itens abaixo para continuar a ativação.",
      items: pendingCompanyData,
    };
  }
  if (data?.pode_vincular) {
    return {
      title: "Recupere o vínculo existente",
      description: "Use os códigos fornecidos pelo suporte da IntNFe para continuar.",
    };
  }
  if (data?.pode_ativar || !data?.vinculado) {
    return {
      title: "Conecte a empresa à IntNFe",
      description: "A integração é automática e não exige copiar códigos técnicos.",
    };
  }
  if (data?.status !== "certificado_validado") {
    return {
      title: "Valide o certificado A1",
      description: "Envie ou confira o certificado na seção logo abaixo.",
    };
  }
  return {
    title: "Continue pelas configurações pendentes",
    description: "O vínculo inicial está pronto. Configure somente os itens indicados abaixo.",
    done: true,
  };
}

export default function IntNFeAtivacaoView({
  data,
  busy,
  error,
  credentials,
  onCredentials,
  onActivate,
  onConsult,
  onBind,
  onReload,
}) {
  const action = data ? nextAction(data) : null;

  return (
    <section
      className="space-y-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7 dark:border-slate-700 dark:bg-slate-900"
      aria-busy={busy}
    >
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <FiFileText className="mt-1 h-7 w-7 shrink-0 text-blue-600" aria-hidden="true" />
          <div>
            <h2 className="text-xl font-bold text-slate-950 dark:text-white">
              Emissão de notas com a IntNFe
            </h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              Prepare sua empresa para os testes de NF-e e NFC-e de produtos.
            </p>
          </div>
        </div>
        <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">
          Ativação em teste · sem valor fiscal
        </span>
      </header>

      {error && (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
        >
          {error}
        </div>
      )}
      {!data ? (
        <div className="space-y-3 text-sm text-slate-600 dark:text-slate-300">
          <p role="status">
            {busy
              ? "Carregando a situação da empresa…"
              : "A situação da ativação não foi carregada."}
          </p>
          {!busy && (
            <button
              type="button"
              onClick={onReload}
              className={`${buttonClass} border border-slate-300`}
            >
              Tentar carregar novamente
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-slate-50 px-4 py-3 dark:bg-slate-800">
            <div>
              <p className="font-semibold text-slate-900 dark:text-white">
                {data.empresa.razao_social || data.empresa.nome_fantasia}
              </p>
              <p className="mt-0.5 text-sm text-slate-600 dark:text-slate-300">
                CNPJ: {data.empresa.cnpj || "Não informado"}
              </p>
            </div>
            {data.pendencias.length > 0 && (
              <Link
                to="/configuracoes/fiscal"
                className="text-sm font-semibold text-blue-700 underline dark:text-blue-300"
              >
                Corrigir dados da empresa
              </Link>
            )}
          </div>

          <div
            role="status"
            aria-live="polite"
            className={`rounded-xl border p-4 text-sm ${
              action.done
                ? "border-emerald-200 bg-emerald-50 text-emerald-950"
                : "border-blue-200 bg-blue-50 text-blue-950"
            }`}
          >
            <div className="flex items-start gap-3">
              {action.done && <FiCheckCircle className="mt-0.5 shrink-0" aria-hidden="true" />}
              <div>
                <p className="text-xs font-bold uppercase tracking-wide opacity-70">
                  {action.done ? "Etapa inicial concluída" : "Próximo passo"}
                </p>
                <p className="mt-1 font-semibold">{action.title}</p>
                <p className="mt-1">{action.description}</p>
              </div>
            </div>
            {action.items?.length > 0 && (
              <ul className="mt-3 list-disc space-y-1 pl-8">
                {action.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            )}
          </div>

          {data.pode_vincular && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-950">
              <h3 className="font-semibold">Encontramos um cadastro anterior</h3>
              <p className="mt-1 text-sm">
                A integração automática não altera o acesso de um emissor que já existia. Peça ao
                suporte para recuperar o vínculo com segurança.
              </p>
              {data.protocolo_suporte && (
                <p className="mt-2 break-all text-xs">
                  Protocolo para o suporte: {data.protocolo_suporte}
                </p>
              )}
              <details className="mt-3 text-sm">
                <summary className="cursor-pointer font-semibold underline">
                  Já recebi os códigos desse emissor
                </summary>
                <form onSubmit={onBind} className="mt-4 space-y-4">
                  <p className="text-slate-600 dark:text-slate-300">
                    Use somente os códigos do emissor desta empresa fornecidos pela IntNFe. Esta é
                    uma recuperação excepcional; os códigos do integrador não servem aqui.
                  </p>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <label className="text-sm font-medium text-slate-700 dark:text-slate-200">
                      Código do emissor
                      <input
                        name="client_id"
                        value={credentials.client_id}
                        onChange={onCredentials}
                        autoComplete="off"
                        maxLength={128}
                        required
                        disabled={busy}
                        className="mt-1 block w-full rounded-lg border border-slate-300 bg-white p-2.5 text-slate-900"
                      />
                    </label>
                    <label className="text-sm font-medium text-slate-700 dark:text-slate-200">
                      Segredo do emissor
                      <input
                        name="client_secret"
                        type="password"
                        value={credentials.client_secret}
                        onChange={onCredentials}
                        autoComplete="new-password"
                        maxLength={4096}
                        required
                        disabled={busy}
                        className="mt-1 block w-full rounded-lg border border-slate-300 bg-white p-2.5 text-slate-900"
                      />
                    </label>
                  </div>
                  <button
                    type="submit"
                    disabled={busy}
                    className={`${buttonClass} bg-blue-600 text-white hover:bg-blue-700`}
                  >
                    Recuperar vínculo
                  </button>
                </form>
              </details>
            </div>
          )}

          <div className="flex flex-wrap gap-3">
            {data.pode_ativar && (
              <button
                type="button"
                onClick={onActivate}
                disabled={busy}
                className={`${buttonClass} bg-blue-600 text-white hover:bg-blue-700`}
              >
                {busy ? "Integrando…" : "Integrar automaticamente"}
              </button>
            )}
            {data.pode_consultar && (
              <button
                type="button"
                onClick={onConsult}
                disabled={busy}
                className={`${buttonClass} border border-slate-300 text-slate-700 dark:text-slate-200`}
              >
                <FiRefreshCw aria-hidden="true" />
                Atualizar situação
              </button>
            )}
            {data.status === "processando" && (
              <button
                type="button"
                onClick={onReload}
                disabled={busy}
                className={`${buttonClass} border border-slate-300 text-slate-700 dark:text-slate-200`}
              >
                Atualizar situação
              </button>
            )}
          </div>
        </>
      )}
    </section>
  );
}
