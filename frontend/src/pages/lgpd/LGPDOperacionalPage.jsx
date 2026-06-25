import { CheckCircle2, Clock3, FileText, RefreshCw, ShieldCheck } from "lucide-react";
import ActionButton from "../../components/ui/ActionButton";
import MetricCard from "../../components/ui/MetricCard";
import PageHeader from "../../components/ui/PageHeader";
import LGPDAnonymizeDialog from "./LGPDAnonymizeDialog";
import LGPDNewRequestModal from "./LGPDNewRequestModal";
import LGPDPrivacyModal from "./LGPDPrivacyModal";
import LGPDRequestModal from "./LGPDRequestModal";
import LGPDSolicitacoesPanel from "./LGPDSolicitacoesPanel";
import LGPDTitularPanel from "./LGPDTitularPanel";
import useLGPDOperacionalController from "./useLGPDOperacionalController";

export default function LGPDOperacionalPage() {
  const controller = useLGPDOperacionalController();

  return (
    <div className="space-y-5 p-4 md:p-6">
      <PageHeader
        icon={ShieldCheck}
        title="LGPD e Privacidade"
        subtitle="Solicitacoes, preferencias, dossie e trilha de acesso dos titulares."
        actions={
          <ActionButton
            icon={RefreshCw}
            intent="neutral"
            tone="soft"
            onClick={controller.refreshAll}
            loading={controller.loading}
          >
            Atualizar
          </ActionButton>
        }
      />

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <MetricCard
          intent={controller.pendingCount ? "amber" : "emerald"}
          icon={<Clock3 className="h-5 w-5" />}
          label="Pendentes"
          value={controller.pendingCount}
          subtitle="Solicitacoes ainda sem tratamento."
        />
        <MetricCard
          intent={controller.reviewCount ? "blue" : "slate"}
          icon={<FileText className="h-5 w-5" />}
          label="Em analise"
          value={controller.reviewCount}
          subtitle="Demandas em acompanhamento operacional."
        />
        <MetricCard
          intent="emerald"
          icon={<CheckCircle2 className="h-5 w-5" />}
          label="Concluidas no filtro"
          value={controller.completedCount}
          subtitle="Itens retornados pelo filtro atual."
        />
      </div>

      <LGPDTitularPanel {...controller} />
      <LGPDSolicitacoesPanel {...controller} />
      <LGPDRequestModal {...controller} />
      <LGPDNewRequestModal {...controller} />
      <LGPDPrivacyModal {...controller} />
      <LGPDAnonymizeDialog {...controller} />
    </div>
  );
}
