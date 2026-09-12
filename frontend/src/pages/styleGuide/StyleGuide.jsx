import { LayoutGrid } from "lucide-react";
import PageHeader from "../../components/ui/PageHeader";
import StyleGuideProgress from "./components/StyleGuideProgress";
import StyleGuideSection from "./components/StyleGuideSection";
import ButtonsSection from "./components/sections/ButtonsSection";
import FieldsSection from "./components/sections/FieldsSection";
import LayoutSection from "./components/sections/LayoutSection";
import ModalsSection from "./components/sections/ModalsSection";
import StatesSection from "./components/sections/StatesSection";
import TypographySection from "./components/sections/TypographySection";
import V2FieldsSection from "./components/sections/V2FieldsSection";

const NAV = [
  { id: "progresso", label: "Progresso" },
  { id: "v2", label: "Componentes v2" },
  { id: "tipografia", label: "Tipografia" },
  { id: "botoes", label: "Botões (legado)" },
  { id: "campos", label: "Campos (legado)" },
  { id: "modais", label: "Modais" },
  { id: "estados", label: "Estados de tela" },
  { id: "layout", label: "Blocos de layout" },
];

export default function StyleGuide() {
  return (
    <div className="p-6">
      <div className="mx-auto max-w-[1200px] space-y-8">
        <PageHeader
          icon={LayoutGrid}
          title="Style Guide"
          subtitle="Andamento e regras visuais dos componentes padronizados do CorePet — ver Documentacao/Roadmap/Fase-1-CI-CD-e-Padronizacao.md (itens 1.6 a 1.9)"
        />

        <nav className="flex flex-wrap gap-2 border-b border-slate-200 pb-4 dark:border-slate-800">
          {NAV.map((item) => (
            <a
              key={item.id}
              href={`#${item.id}`}
              className="rounded-full border border-slate-200 px-3 py-1 text-xs font-semibold text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              {item.label}
            </a>
          ))}
        </nav>

        <section id="progresso">
          <h2 className="text-lg font-bold text-slate-950 dark:text-slate-100">
            Progresso da padronização
          </h2>
          <p className="mt-1 max-w-3xl text-sm text-slate-500 dark:text-slate-400">
            Todo componente planejado no roadmap entra nesta lista assim que é criado. Ver definição
            de pronto em cada item da Fase 1 para o que falta antes de virar "Pronto".
          </p>
          <div className="mt-5">
            <StyleGuideProgress />
          </div>
        </section>

        <StyleGuideSection
          id="v2"
          title="Componentes v2 (components/v2/)"
          description="Cada tipo de campo e cada ação de botão é um componente próprio, sem prop de cor/tamanho — reaproveita uma base (InputTexto, BotaoBase) e se especializa. É a implementação real dos itens 1.6/1.7 do roadmap."
        >
          <V2FieldsSection />
        </StyleGuideSection>

        <StyleGuideSection
          id="tipografia"
          title="Tipografia"
          description="Título, subtítulo, texto de destaque, texto simples e texto de ajuda — uma única fonte para cada um (item 1.7)."
        >
          <TypographySection />
        </StyleGuideSection>

        <StyleGuideSection
          id="botoes"
          title="Botões"
          description="ActionButton/IconActionButton são a base; o catálogo por ação (Save/Cancel/Delete/Help...) ainda está planejado (item 1.7)."
        >
          <ButtonsSection />
        </StyleGuideSection>

        <StyleGuideSection
          id="campos"
          title="Campos de formulário"
          description="Nenhuma tela deveria usar <input>/<select>/<textarea> nativos diretamente (item 1.6)."
        >
          <FieldsSection />
        </StyleGuideSection>

        <StyleGuideSection
          id="modais"
          title="Modais"
          description="CorePetDialogHost já resolve confirmação/pergunta; falta a casca genérica para conteúdo arbitrário (item 1.7)."
        >
          <ModalsSection />
        </StyleGuideSection>

        <StyleGuideSection
          id="estados"
          title="Estados de tela"
          description="Vazio, carregando e erro — quando usar cada um, para nunca deixar uma tela em branco sem explicação."
        >
          <StatesSection />
        </StyleGuideSection>

        <StyleGuideSection
          id="layout"
          title="Blocos de layout"
          description="Estrutura de página, cartões de conteúdo, indicadores de status e seletores curtos."
        >
          <LayoutSection />
        </StyleGuideSection>
      </div>
    </div>
  );
}
