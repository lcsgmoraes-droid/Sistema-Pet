import { FiCheckCircle, FiCircle, FiInfo } from "react-icons/fi";

function Step({ label, description, done, action = false }) {
  const Icon = done ? FiCheckCircle : action ? FiInfo : FiCircle;
  const style = done
    ? "border-emerald-200 bg-emerald-50 text-emerald-950"
    : action
      ? "border-blue-200 bg-blue-50 text-blue-950"
      : "border-slate-200 bg-white text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200";
  return (
    <li className={`rounded-xl border p-4 ${style}`}>
      <div className="flex items-start gap-2">
        <Icon className="mt-0.5 shrink-0" aria-hidden="true" />
        <div>
          <p className="text-sm font-semibold">{label}</p>
          <p className="mt-1 text-xs leading-5">{description}</p>
        </div>
      </div>
    </li>
  );
}

export default function IntNFeChecklist({ activation, fiscal, certificate, csc, numbering }) {
  const linked = Boolean(activation?.vinculado);
  const companyReady = Boolean(activation && activation.pendencias?.length === 0);
  const fiscalReady = Boolean(fiscal?.sincronizado);
  const certificateReady = ["valido", "expirando"].includes(certificate?.situacao);
  const cscHomologation = Boolean(
    csc?.ambientes?.find((item) => item.ambiente_codigo === 2)?.tem_csc,
  );
  const nfeReady = linked && fiscalReady && certificateReady;
  const nfceReady = nfeReady && cscHomologation;
  const knownSequences = numbering?.series?.length || 0;

  return (
    <section className="space-y-4 rounded-2xl border border-slate-200 bg-slate-50 p-5 sm:p-7 dark:border-slate-700 dark:bg-slate-950/40">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-slate-950 dark:text-white">
            Checklist de preparação fiscal
          </h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            O CorePet atualiza este quadro conforme cada configuração é concluída.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs font-semibold">
          <span
            className={`rounded-full px-3 py-1 ${nfeReady ? "bg-emerald-100 text-emerald-900" : "bg-slate-200 text-slate-700"}`}
          >
            NF-e homologação: {nfeReady ? "base pronta" : "pendente"}
          </span>
          <span
            className={`rounded-full px-3 py-1 ${nfceReady ? "bg-emerald-100 text-emerald-900" : "bg-slate-200 text-slate-700"}`}
          >
            NFC-e homologação: {nfceReady ? "base pronta" : "pendente"}
          </span>
        </div>
      </header>

      <ol className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        <Step
          label="Dados da empresa"
          description={
            companyReady
              ? "Campos básicos completos."
              : "Complete os campos indicados no cadastro da empresa."
          }
          done={companyReady}
        />
        <Step
          label="Vínculo com a IntNFe"
          description={
            linked ? "Emitente vinculado ao CorePet." : "Clique em integrar para criar o vínculo."
          }
          done={linked}
        />
        <Step
          label="Cadastro fiscal"
          description={
            fiscalReady
              ? "Dados sincronizados automaticamente."
              : "Revise os campos fiscais pendentes."
          }
          done={fiscalReady}
        />
        <Step
          label="Certificado A1"
          description={
            certificateReady ? certificate.mensagem : "Envie o A1 e a senha pelo CorePet."
          }
          done={certificateReady}
        />
        <Step
          label="CSC para NFC-e"
          description={
            cscHomologation
              ? "CSC de homologação cadastrado."
              : "Necessário somente para NFC-e; obtenha o código na SEFAZ."
          }
          done={cscHomologation}
        />
        <Step
          label="Série e última numeração"
          description={`Confira manualmente no sistema anterior. ${knownSequences ? `${knownSequences} sequência(s) registrada(s).` : "Se a série for nova, ela começa no número 1."}`}
          done={false}
          action
        />
      </ol>
    </section>
  );
}
