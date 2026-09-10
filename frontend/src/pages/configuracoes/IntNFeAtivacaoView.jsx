import { FiCheckCircle, FiCircle, FiFileText, FiRefreshCw } from "react-icons/fi";
import { Link } from "react-router-dom";

const buttonClass =
  "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-500";

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
  const steps = [
    { label: "Dados da empresa", done: data && data.pendencias.length === 0 },
    { label: "Vínculo com o emissor", done: data?.vinculado },
    { label: "Certificado A1", done: data?.status === "certificado_validado" },
  ];

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
              Prepare sua empresa para os testes de NF-e de produtos.
            </p>
          </div>
        </div>
        <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">
          Homologação · sem valor fiscal
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
          <div className="rounded-xl bg-slate-50 p-4 dark:bg-slate-800">
            <p className="font-semibold text-slate-900 dark:text-white">
              {data.empresa.razao_social || data.empresa.nome_fantasia}
            </p>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              CNPJ: {data.empresa.cnpj || "Não informado"}
            </p>
            <Link
              to="/configuracoes/fiscal"
              className="mt-3 inline-block text-sm font-semibold text-blue-700 underline dark:text-blue-300"
            >
              Conferir dados da empresa
            </Link>
          </div>

          <ol className="grid gap-3 sm:grid-cols-3" aria-label="Etapas da ativação">
            {steps.map(({ label, done }, index) => (
              <li
                key={label}
                className={`rounded-xl border p-4 text-sm ${done ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-slate-200 text-slate-700 dark:border-slate-700 dark:text-slate-200"}`}
              >
                <div className="mb-2 flex items-center gap-2">
                  {done ? <FiCheckCircle aria-hidden="true" /> : <FiCircle aria-hidden="true" />}
                  <span className="text-xs">{done ? "Concluído" : "Pendente"}</span>
                </div>
                <strong>
                  {index + 1}. {label}
                </strong>
              </li>
            ))}
          </ol>

          <div
            role="status"
            aria-live="polite"
            className="space-y-2 rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-950"
          >
            <p className="font-medium">{data.mensagem}</p>
            {data.pendencias.length > 0 && (
              <ul className="list-disc space-y-1 pl-5">
                {data.pendencias.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            )}
            {data.certificado_valido_ate && (
              <p>
                Validade do certificado:{" "}
                {new Date(data.certificado_valido_ate).toLocaleDateString("pt-BR")}
              </p>
            )}
            {data.protocolo_suporte && (
              <p className="break-all text-xs">
                Protocolo para o suporte: {data.protocolo_suporte}
              </p>
            )}
          </div>

          {data.pode_vincular && (
            <form
              onSubmit={onBind}
              className="space-y-4 rounded-xl border border-slate-200 p-4 dark:border-slate-700"
            >
              <div>
                <h3 className="font-semibold text-slate-900 dark:text-white">
                  Vincular cadastro existente
                </h3>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                  Informe os códigos fornecidos pela IntNFe para esta empresa. Os códigos do
                  integrador não devem ser usados aqui.
                </p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="text-sm font-medium text-slate-700 dark:text-slate-200">
                  Código do emitente (clientId)
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
                  Segredo do emitente (clientSecret)
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
                Verificar e vincular
              </button>
            </form>
          )}

          {data.pode_ativar && (
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Ao ativar, o CorePet envia o CNPJ, a razão social e o nome fantasia à IntNFe para
              preparar o cadastro fiscal da empresa.
            </p>
          )}
          <div className="flex flex-wrap gap-3">
            {data.pode_ativar && (
              <button
                type="button"
                onClick={onActivate}
                disabled={busy}
                className={`${buttonClass} bg-blue-600 text-white hover:bg-blue-700`}
              >
                {busy ? "Verificando…" : "Ativar emissão em teste"}
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
                Consultar vínculo e certificado
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
          <p className="border-t border-slate-100 pt-4 text-sm text-slate-500 dark:border-slate-800 dark:text-slate-400">
            Esta etapa prepara o vínculo. A emissão de notas pelo PDV será liberada após os testes
            de homologação.
          </p>
        </>
      )}
    </section>
  );
}
