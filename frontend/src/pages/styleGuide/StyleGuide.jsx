import { LayoutGrid } from "lucide-react";
import StyleGuideProgress from "./components/StyleGuideProgress";
import StyleGuideSection from "./components/StyleGuideSection";
import FormularioExemploSection from "./components/sections/FormularioExemploSection";
import TypographySection from "./components/sections/TypographySection";
import V2CardsSection from "./components/sections/V2CardsSection";
import V2FieldsSection from "./components/sections/V2FieldsSection";

const NAV = [
  { id: "progresso", label: "Progresso" },
  { id: "v2", label: "Componentes v2" },
  { id: "v2-cartoes", label: "Cartões e navegação" },
  { id: "tipografia", label: "Tipografia" },
  { id: "formulario-exemplo", label: "Formulário de exemplo" },
];

export default function StyleGuide() {
  return (
    <div className="p-6">
      <div className="mx-auto max-w-[1200px] space-y-8">
        <div className="flex items-center gap-2.5">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-200">
            <LayoutGrid className="h-6 w-6" aria-hidden="true" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-950 dark:text-slate-100">Style Guide</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Andamento e regras visuais de <code>components/v2/</code> — ver
              Documentacao/Roadmap/Fase-1-CI-CD-e-Padronizacao.md (itens 1.6 a 1.9)
            </p>
          </div>
        </div>

        <p className="max-w-3xl text-xs text-slate-500 dark:text-slate-400">
          Esta página mostra só o que faz parte da nossa estruturação nova (
          <code>components/v2/</code>). Nada de <code>components/ui/</code> ou de outros componentes
          antigos aparece aqui — se algo antigo precisa ser reaproveitado, ele é recriado dentro de{" "}
          <code>v2/</code>, o original não é tocado nem trazido pra cá.
        </p>

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
          description="Cada tipo de campo e cada ação de botão é um componente próprio, sem prop de cor/tamanho — reaproveita uma base (InputTexto, BotaoBase) e se especializa. Todo grupo mostra os estados ativo, com erro e desabilitado lado a lado."
        >
          <V2FieldsSection />
        </StyleGuideSection>

        <StyleGuideSection
          id="v2-cartoes"
          title="Cartões e navegação (components/v2/)"
          description="Cartão indicador clicável (dashboards), placeholder de painel sem dado, filtro de opções em pill e link de navegação secundário — nasceram da limpeza da tela /dashboard e reaparecem em qualquer painel com números e navegação."
        >
          <V2CardsSection />
        </StyleGuideSection>

        <StyleGuideSection
          id="tipografia"
          title="Tipografia (src/styles/v2-tipografia.css)"
          description='Título, subtítulo, texto de destaque, texto simples, texto de ajuda e rótulo (item 1.7) — resolvido como classe Tailwind, não como componente React: texto não tem comportamento, só precisa de um único ponto de ajuste de tamanho/cor. Mudou o tamanho de ".v2-titulo-secao"? Muda uma vez no CSS, toda tela que usa a classe atualiza.'
        >
          <TypographySection />
        </StyleGuideSection>

        <StyleGuideSection
          id="formulario-exemplo"
          title="Formulário de exemplo"
          description="Todos os componentes acima juntos, como numa tela real de cadastro — para auditar espaçamento, alinhamento e consistência em conjunto, não só isolados. Regra de bloqueio: nenhum componente novo é considerado pronto sem aparecer aqui funcionando ao lado dos outros. Clique em Salvar vazio para ver a validação de erro em ação."
        >
          <FormularioExemploSection />
        </StyleGuideSection>
      </div>
    </div>
  );
}
