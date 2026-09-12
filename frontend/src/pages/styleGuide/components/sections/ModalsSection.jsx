import { useState } from "react";
import ActionButton from "../../../../components/ui/ActionButton";
import { confirmarCorePet, perguntarCorePet } from "../../../../services/corepetDialog";
import StyleGuideExample from "../StyleGuideExample";

export default function ModalsSection() {
  const [resultado, setResultado] = useState("");

  return (
    <StyleGuideExample
      label="CorePetDialogHost — confirmar()/perguntar() (pronto; ver progresso para o Modal genérico ainda planejado)"
      note="Substitui window.confirm/window.prompt em todo o sistema. Já com role=dialog, foco automático e Escape para fechar."
    >
      <ActionButton
        intent="neutral"
        onClick={async () => {
          const ok = await confirmarCorePet("Confirmar esta ação de exemplo?");
          setResultado(ok ? "Confirmado" : "Cancelado");
        }}
      >
        Abrir confirmação
      </ActionButton>
      <ActionButton
        intent="delete"
        onClick={async () => {
          const ok = await confirmarCorePet("Excluir este registro de exemplo?");
          setResultado(ok ? "Confirmado" : "Cancelado");
        }}
      >
        Abrir confirmação (perigosa)
      </ActionButton>
      <ActionButton
        intent="info"
        onClick={async () => {
          const valor = await perguntarCorePet("Digite um motivo de exemplo:");
          setResultado(valor === null ? "Cancelado" : `Digitado: "${valor}"`);
        }}
      >
        Abrir pergunta (input)
      </ActionButton>
      {resultado ? (
        <span className="text-sm font-medium text-slate-600 dark:text-slate-300">{resultado}</span>
      ) : null}
    </StyleGuideExample>
  );
}
