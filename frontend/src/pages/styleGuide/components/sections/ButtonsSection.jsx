import { AlertTriangle, FileText, HelpCircle, Info, Pencil, Plus, Trash2, X } from "lucide-react";
import { useState } from "react";
import ActionButton from "../../../../components/ui/ActionButton";
import IconActionButton from "../../../../components/ui/IconActionButton";
import { ACTION_COLOR_RULES } from "../../../../components/ui/actionStyles";
import StyleGuideExample from "../StyleGuideExample";

const INTENT_ICONS = {
  create: Plus,
  edit: Pencil,
  delete: Trash2,
  neutral: X,
  warning: AlertTriangle,
  info: Info,
  pdf: FileText,
};

const TONES = ["solid", "soft", "ghost"];

export default function ButtonsSection() {
  const [carregando, setCarregando] = useState(false);

  return (
    <>
      <StyleGuideExample
        label="ActionButton — intent define a cor, tone define o peso visual"
        note={Object.entries(ACTION_COLOR_RULES)
          .map(([intent, regra]) => `${intent}: ${regra}`)
          .join(" · ")}
      >
        <div className="flex w-full flex-col gap-3">
          {Object.keys(INTENT_ICONS).map((intent) => (
            <div key={intent} className="flex flex-wrap items-center gap-2">
              <span className="w-16 shrink-0 text-xs font-mono text-slate-400">{intent}</span>
              {TONES.map((tone) => (
                <ActionButton key={tone} intent={intent} tone={tone} icon={INTENT_ICONS[intent]}>
                  {tone}
                </ActionButton>
              ))}
            </div>
          ))}
        </div>
      </StyleGuideExample>

      <StyleGuideExample label="ActionButton — estado loading e disabled">
        <ActionButton
          intent="create"
          icon={Plus}
          loading={carregando}
          onClick={() => {
            setCarregando(true);
            setTimeout(() => setCarregando(false), 1500);
          }}
        >
          {carregando ? "Salvando..." : "Clique para simular"}
        </ActionButton>
        <ActionButton intent="create" icon={Plus} disabled>
          Desabilitado
        </ActionButton>
      </StyleGuideExample>

      <StyleGuideExample
        label="IconActionButton — só ícone; título/aria-label é obrigatório para acessibilidade"
        note="Sem title/aria-label, um leitor de tela não consegue anunciar o botão — reforço direto do item 1.7 (catálogo por ação preenche isso sozinho)."
      >
        {Object.keys(INTENT_ICONS).map((intent) => (
          <IconActionButton
            key={intent}
            intent={intent}
            icon={INTENT_ICONS[intent]}
            title={intent}
            aria-label={intent}
          />
        ))}
        <IconActionButton icon={HelpCircle} intent="neutral" title="Ajuda" aria-label="Ajuda" />
      </StyleGuideExample>
    </>
  );
}
