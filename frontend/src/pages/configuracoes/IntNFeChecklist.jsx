import { FiCheckCircle, FiChevronDown, FiCircle, FiInfo } from "react-icons/fi";

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

export default function IntNFeChecklist({
  activation,
  fiscal,
  certificate,
  csc,
  numbering,
  environment,
}) {
  const linked = Boolean(activation?.vinculado);
  const companyReady = Boolean(activation && activation.pendencias?.length === 0);
  const fiscalReady = Boolean(fiscal?.sincronizado);
  const certificateReady = ["valido", "expirando"].includes(certificate?.situacao);
  const cscHomologation = Boolean(
    csc?.ambientes?.find((item) => item.ambiente_codigo === 2)?.tem_csc,
  );
  const knownSequences = numbering?.series?.length || 0;
  const emissionReady = Boolean(environment?.habilitada);

  return (
    <details className="group rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 p-5 sm:px-7">
        <div>
          <h2 className="font-bold text-slate-950 dark:text-white">Checklist completo</h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            Consulte as etapas concluídas e pendentes quando precisar.
          </p>
        </div>
        <FiChevronDown
          className="shrink-0 text-slate-500 transition-transform group-open:rotate-180"
          aria-hidden="true"
        />
      </summary>

      <ol className="grid gap-3 border-t border-slate-100 p-5 md:grid-cols-2 lg:grid-cols-3 sm:p-7 dark:border-slate-800">
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
            certificateReady ? "Certificado validado." : "Envie o A1 e a senha pelo CorePet."
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
          label="Sequências por modelo e ambiente"
          description={`Use as abas de homologação e produção. NF-e e NFC-e possuem numerações próprias. ${knownSequences ? `${knownSequences} sequência(s) registrada(s).` : "Se a série for nova, ela começa no número 1."}`}
          done={false}
          action
        />
        <Step
          label="Ambiente de emissão"
          description={
            emissionReady
              ? `Emissão direta ativa em ${environment.ambiente}.`
              : "Escolha homologação ou produção para liberar a transmissão pelo CorePet."
          }
          done={emissionReady}
        />
      </ol>
    </details>
  );
}
