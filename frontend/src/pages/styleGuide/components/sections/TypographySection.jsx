import StyleGuideExample from "../StyleGuideExample";

export default function TypographySection() {
  return (
    <StyleGuideExample
      label="Prévia da escala-alvo (Title, SectionTitle, Subtitle, Text, HelpText ainda não existem como componente — ver progresso acima)"
      note="Classes extraídas do que já existe hoje em PageHeader.jsx e Panel.jsx. Quando os componentes forem criados (item 1.7), devem gerar exatamente esta saída."
    >
      <div className="w-full space-y-2">
        <div className="text-xl font-bold text-slate-950 dark:text-slate-100">
          Título de página (Title)
        </div>
        <div className="text-base font-semibold text-slate-900 dark:text-slate-100">
          Título de bloco/card (SectionTitle)
        </div>
        <div className="text-xs text-slate-500 dark:text-slate-400">
          Linha de apoio abaixo de um título (Subtitle)
        </div>
        <p className="text-sm text-slate-700 dark:text-slate-300">
          Parágrafo padrão de conteúdo (Text)
        </p>
        <div className="text-xs text-slate-500 dark:text-slate-400">
          Texto de ajuda pequeno, abaixo de um campo ou seção (HelpText)
        </div>
      </div>
    </StyleGuideExample>
  );
}
