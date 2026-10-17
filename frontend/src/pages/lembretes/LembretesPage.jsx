import { BellRing } from "lucide-react";
import PageHeader from "../../components/ui/PageHeader";
import LembreteContatoModal from "./LembreteContatoModal";
import LembretesAniversariantes from "./LembretesAniversariantes";
import LembretesBlingAutocadastros from "./LembretesBlingAutocadastros";
import LembretesCampanhasAlertas from "./LembretesCampanhasAlertas";
import LembretesClientesInativos from "./LembretesClientesInativos";
import LembretesHeader from "./LembretesHeader";
import LembretesList from "./LembretesList";
import LembretesRelatorios from "./LembretesRelatorios";
import LembretesTabs from "./LembretesTabs";
import LembretesValidadeSection from "./LembretesValidadeSection";
import useLembretesController from "./useLembretesController";

export default function LembretesPage() {
  const controller = useLembretesController();

  return (
    <div className="p-6">
      <div className="mx-auto max-w-[1600px] space-y-5">
        <PageHeader
          icon={BellRing}
          subtitle="Priorize retornos, converse com o cliente e acompanhe cada contato até a recompra."
          title="Central de lembretes"
        />

        <LembretesTabs controller={controller} />

        <main role="tabpanel">
          {controller.abaAtiva === "relatorios" && (
            <>
              <PanelIntro
                description="Acompanhe o volume de contatos, o canal usado e as recompras observadas depois do contato."
                title="Histórico e resultados"
              />
              <LembretesRelatorios relatorio={controller.relatorio} />
            </>
          )}

          {controller.abaAtiva === "bling" && (
            <>
              <PanelIntro
                description="Produtos que o sistema cadastrou sozinho ao encontrar um SKU do Bling sem cadastro."
                title="Auto cadastro Bling"
              />
              <LembretesBlingAutocadastros autocadastrosBling={controller.autocadastrosBling} />
            </>
          )}

          {controller.abaAtiva === "relacionamento" && (
            <div className="grid gap-6">
              <PanelIntro
                description="Clientes inativos, brindes e outras oportunidades de campanha sem misturar com recompra."
                title="Alertas de relacionamento"
              />
              <LembretesCampanhasAlertas alertasCampanhas={controller.alertasCampanhas} />
              <LembretesClientesInativos />
            </div>
          )}

          {controller.abaAtiva === "aniversarios" && (
            <LembretesAniversariantes controller={controller} />
          )}

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
        </main>

        <LembreteContatoModal controller={controller} />
      </div>
    </div>
  );
}

function PanelIntro({ description, title }) {
  return (
    <div className="mb-4">
      <h2 className="m-0 text-lg font-semibold text-slate-900 dark:text-slate-100">{title}</h2>
      <p className="v2-texto-ajuda mt-1">{description}</p>
    </div>
  );
}
