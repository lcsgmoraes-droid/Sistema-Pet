import { PawPrint } from "lucide-react";
import { useState } from "react";
import ActionButton from "../../../../components/ui/ActionButton";
import PageHeader from "../../../../components/ui/PageHeader";
import Panel from "../../../../components/ui/Panel";
import SegmentedControl from "../../../../components/ui/SegmentedControl";
import StatusBadge from "../../../../components/ui/StatusBadge";
import StyleGuideExample from "../StyleGuideExample";

const INTENTS = ["success", "info", "warning", "danger", "neutral", "purple"];

export default function LayoutSection() {
  const [periodo, setPeriodo] = useState("mes");

  return (
    <>
      <StyleGuideExample label="PageHeader — topo de toda página do sistema">
        <div className="w-full rounded-lg border border-dashed border-slate-200 p-3 dark:border-slate-700">
          <PageHeader
            icon={PawPrint}
            title="Título da página"
            subtitle="Linha de apoio opcional"
            actions={<ActionButton intent="create">Ação principal</ActionButton>}
          />
        </div>
      </StyleGuideExample>

      <StyleGuideExample label="Panel — bloco/card de conteúdo, com título e ações opcionais">
        <div className="w-full">
          <Panel title="Título do bloco" subtitle="Descrição curta do que o bloco mostra">
            <p className="text-sm text-slate-600 dark:text-slate-300">Conteúdo do bloco aqui.</p>
          </Panel>
        </div>
      </StyleGuideExample>

      <StyleGuideExample
        label="StatusBadge — intents diretos e mapeamento automático por status de negócio"
        note='Ex.: <StatusBadge status="pago" /> já sabe que é verde/"Pago" sem precisar passar intent.'
      >
        {INTENTS.map((intent) => (
          <StatusBadge key={intent} intent={intent}>
            {intent}
          </StatusBadge>
        ))}
        <StatusBadge status="pago" />
        <StatusBadge status="pendente" />
        <StatusBadge status="vencida" />
      </StyleGuideExample>

      <StyleGuideExample label="SegmentedControl — alternar entre poucas opções mutuamente exclusivas">
        <SegmentedControl
          ariaLabel="Período"
          value={periodo}
          onChange={setPeriodo}
          options={[
            { value: "dia", label: "Dia" },
            { value: "mes", label: "Mês" },
            { value: "ano", label: "Ano" },
          ]}
        />
      </StyleGuideExample>
    </>
  );
}
