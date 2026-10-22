import { MessageCircle } from "lucide-react";
import EstadoVazio from "../../components/v2/EstadoVazio/EstadoVazio";

// Casca do módulo CRM (etapa 1.1). O funil de leads entra na etapa 2;
// ver docs/crm/ROADMAP.md.
export default function CrmPage() {
  return (
    <div className="mx-auto w-full max-w-6xl p-4 sm:p-6">
      <header className="mb-4">
        <p className="m-0 text-xs font-bold uppercase tracking-[0.18em] text-teal-700 dark:text-teal-300">
          Relacionamento
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900 dark:text-slate-100 sm:text-3xl">
          CRM
        </h1>
        <p className="mt-1 max-w-3xl text-sm text-slate-600 dark:text-slate-400">
          Acompanhe seus tutores, conversas e oportunidades em um só lugar.
        </p>
      </header>
      <EstadoVazio
        icone={MessageCircle}
        titulo="O funil de leads está chegando"
        descricao="Seu módulo CRM está ativo. As primeiras telas serão liberadas nas próximas etapas."
      />
    </div>
  );
}
