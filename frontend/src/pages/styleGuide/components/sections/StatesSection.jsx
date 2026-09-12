import { Search } from "lucide-react";
import ActionButton from "../../../../components/ui/ActionButton";
import EmptyState from "../../../../components/ui/EmptyState";
import ErrorState from "../../../../components/ui/ErrorState";
import LoadingState from "../../../../components/ui/LoadingState";
import { TextSkeleton } from "../../../../components/Skeletons";
import StyleGuideExample from "../StyleGuideExample";

export default function StatesSection() {
  return (
    <>
      <StyleGuideExample
        label="EmptyState — quando uma lista/busca não tem nenhum resultado"
        note="Sempre com ação de recuperação quando fizer sentido (ex.: limpar filtro, criar o primeiro registro)."
      >
        <div className="w-full">
          <EmptyState
            icon={Search}
            title="Nenhum cliente encontrado"
            description="Tente outro termo de busca ou cadastre um novo cliente."
            action={<ActionButton intent="create">Novo cliente</ActionButton>}
          />
        </div>
      </StyleGuideExample>

      <StyleGuideExample
        label="LoadingState — carregamento de bloco/seção (não a tela inteira)"
        note="Para a tela inteira, preferir um skeleton do layout final em vez de um spinner central."
      >
        <div className="w-full rounded-lg border border-dashed border-slate-200 dark:border-slate-700">
          <LoadingState label="Carregando clientes..." />
        </div>
      </StyleGuideExample>

      <StyleGuideExample
        label="ErrorState — falha ao carregar dados (não confundir com erro de validação de campo)"
        note="Erro de campo usa a prop error do FormField (ver seção de Campos); ErrorState é para quando o bloco inteiro falhou."
      >
        <div className="w-full">
          <ErrorState
            title="Não foi possível carregar os clientes"
            description="Verifique sua conexão e tente novamente."
            action={<ActionButton intent="neutral">Tentar novamente</ActionButton>}
          />
        </div>
      </StyleGuideExample>

      <StyleGuideExample label="TextSkeleton — placeholder de texto enquanto um valor carrega">
        <div className="w-64 space-y-2">
          <TextSkeleton />
          <TextSkeleton short />
        </div>
      </StyleGuideExample>
    </>
  );
}
