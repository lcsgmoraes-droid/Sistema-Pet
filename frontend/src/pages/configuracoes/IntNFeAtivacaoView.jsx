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
            {data.certificado_alerta && (
              <p className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-amber-950">
                {data.certificado_alerta}
              </p>
            )}
            {data.protocolo_suporte && (
              <p className="break-all text-xs">
                Protocolo para o suporte: {data.protocolo_suporte}
              </p>
            )}
          </div>

          {data.pode_vincular && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-950">
              <h3 className="font-semibold">Encontramos um cadastro anterior</h3>
              <p className="mt-1 text-sm">
                A integração automática não altera o acesso de um emissor que já existia. Peça ao
                suporte para recuperar o vínculo com segurança.
              </p>
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

          {data.pode_ativar && (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950">
              <p className="font-semibold">Integração automática</p>
              <p className="mt-1">
                Ao continuar, você autoriza o CorePet a criar e administrar o emissor desta empresa
                na IntNFe. O CorePet envia os dados cadastrais, recebe os códigos técnicos e os
                guarda de forma protegida. Você não precisa copiar nem informar códigos.
              </p>
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
