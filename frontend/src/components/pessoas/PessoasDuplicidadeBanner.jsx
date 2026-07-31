import { AlertTriangle, CheckCircle2, GitMerge, Loader2, RefreshCw } from "lucide-react";
import ActionButton from "../ui/ActionButton";

function motivoLabel(motivo) {
  const mapa = {
    cpf_conflitante: "CPF diferente",
    cnpj_conflitante: "CNPJ diferente",
    crmv_conflitante: "CRMV diferente",
    email_conflitante: "email diferente",
    telefone_conflitante: "telefone diferente",
    celular_conflitante: "celular diferente",
    nome_diferente: "nome diferente",
    contas_app_diferentes: "contas de app diferentes",
    sem_identidade_forte_compartilhada: "sem CPF, CNPJ ou CRMV valido em comum",
  };
  return mapa[motivo] || motivo;
}

export default function PessoasDuplicidadeBanner({
  sugestoes = [],
  totalSugestoes = sugestoes.length,
  totalAutomaticas = 0,
  verificando = false,
  onVerificar,
  onFundirAutomaticas,
  onRevisarSugestao,
}) {
  if (!verificando && !totalAutomaticas && sugestoes.length === 0) return null;

  const primeiraSugestao = sugestoes[0];

  return (
    <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <div className="mt-0.5 rounded-full bg-white p-2 text-amber-600">
            {verificando ? (
              <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
            ) : sugestoes.length ? (
              <AlertTriangle className="h-5 w-5" aria-hidden="true" />
            ) : (
              <CheckCircle2 className="h-5 w-5" aria-hidden="true" />
            )}
          </div>
          <div className="min-w-0">
            <div className="font-semibold">
              {verificando
                ? "Verificando cadastros duplicados..."
                : sugestoes.length
                  ? `${totalSugestoes} possivel(is) duplicidade(s) para revisar`
                  : `${totalAutomaticas} duplicidade(s) segura(s) pronta(s) para fundir`}
            </div>
            {primeiraSugestao ? (
              <div className="mt-1 truncate text-amber-800">
                {primeiraSugestao.principal?.nome || "Pessoa"} x{" "}
                {primeiraSugestao.duplicado?.nome || "duplicado"}:{" "}
                {(primeiraSugestao.motivos || []).map(motivoLabel).join(", ")}
              </div>
            ) : (
              <div className="mt-1 text-amber-800">
                A varredura preserva historico e vinculos usando a fusao de pessoas.
              </div>
            )}
          </div>
        </div>

        <div className="flex flex-wrap gap-2 lg:justify-end">
          {primeiraSugestao && (
            <ActionButton
              icon={GitMerge}
              intent="warning"
              onClick={() => onRevisarSugestao(primeiraSugestao)}
              size="md"
            >
              Revisar
            </ActionButton>
          )}
          {totalAutomaticas > 0 && (
            <ActionButton
              disabled={verificando}
              icon={GitMerge}
              intent="warning"
              onClick={onFundirAutomaticas}
              size="md"
            >
              {totalAutomaticas > 25
                ? `Fundir 25 de ${totalAutomaticas} seguras`
                : `Fundir ${totalAutomaticas} segura(s)`}
            </ActionButton>
          )}
          <ActionButton
            disabled={verificando}
            icon={verificando ? Loader2 : RefreshCw}
            intent="neutral"
            onClick={onVerificar}
            size="md"
            tone="soft"
          >
            Analisar agora
          </ActionButton>
        </div>
      </div>
    </div>
  );
}
