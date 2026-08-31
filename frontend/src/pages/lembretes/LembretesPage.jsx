import "../../styles/Lembretes.css";
import LembreteContatoModal from "./LembreteContatoModal";
import LembretesCampanhasAlertas from "./LembretesCampanhasAlertas";
import LembretesHeader from "./LembretesHeader";
import LembretesList from "./LembretesList";
import LembretesRelatorios from "./LembretesRelatorios";
import LembretesTabs from "./LembretesTabs";
import LembretesValidadeSection from "./LembretesValidadeSection";
import useLembretesController from "./useLembretesController";

export default function LembretesPage() {
  const controller = useLembretesController();

  return (
    <div className="lembretes-container">
      <header className="mb-2">
        <p className="m-0 text-xs font-bold uppercase tracking-[0.18em] text-teal-700 dark:text-teal-300">
          Relacionamento
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900 dark:text-slate-100 sm:text-3xl">
          Central de lembretes
        </h1>
        <p className="mt-1 max-w-3xl text-sm text-slate-600 dark:text-slate-400">
          Priorize retornos, converse com o cliente e acompanhe cada contato até a recompra.
        </p>
      </header>

      <LembretesTabs controller={controller} />

      <main role="tabpanel">
        {controller.abaAtiva === "recompras" && (
          <>
            <LembretesHeader controller={controller} />
            <LembretesList controller={controller} />
          </>
        )}

        {controller.abaAtiva === "validade" && (
          <>
            <PanelIntro
              description="Lotes retirados do estoque vendável ficam aqui até você registrar a decisão."
              title="Controle de validade"
            />
            <LembretesValidadeSection controller={controller} />
          </>
        )}

        {controller.abaAtiva === "relacionamento" && (
          <>
            <PanelIntro
              description="Aniversários, inatividade, brindes e outras oportunidades de campanha sem misturar com recompra."
              title="Alertas de relacionamento"
            />
            <LembretesCampanhasAlertas alertasCampanhas={controller.alertasCampanhas} />
            {!controller.alertasCampanhas && (
              <EmptyPanel text="Nenhum alerta de campanha disponível neste momento." />
            )}
          </>
        )}

        {controller.abaAtiva === "relatorios" && (
          <>
            <PanelIntro
              description="Acompanhe o volume de contatos, o canal usado e as recompras observadas depois do contato."
              title="Histórico e resultados"
            />
            <LembretesRelatorios relatorio={controller.relatorio} />
          </>
        )}
      </main>

      <LembreteContatoModal controller={controller} />
    </div>
  );
}

function PanelIntro({ description, title }) {
  return (
    <div className="mb-4">
      <h2 className="m-0 text-lg font-semibold text-slate-900 dark:text-slate-100">{title}</h2>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p>
    </div>
  );
}

function EmptyPanel({ text }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white px-5 py-12 text-center text-sm text-slate-500 shadow-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400">
      {text}
    </div>
  );
}
