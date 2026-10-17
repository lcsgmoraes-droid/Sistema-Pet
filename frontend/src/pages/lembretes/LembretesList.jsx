import { Bell, Search } from "lucide-react";
import EstadoVazio from "../../components/v2/EstadoVazio/EstadoVazio";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import SeletorOpcoes from "../../components/v2/SeletorOpcoes/SeletorOpcoes";
import LembreteCard from "./LembreteCard";
import { PRAZOS, TIPOS_LEMBRETE } from "./lembretesUtils";

const OPCOES_TIPO = [
  { value: "todos", label: "Todos os tipos" },
  ...Object.entries(TIPOS_LEMBRETE).map(([value, label]) => ({ value, label })),
];

export default function LembretesList({ controller }) {
  const opcoesPrazo = PRAZOS.map((prazo) => ({
    valor: prazo.id,
    rotulo: `${prazo.label} · ${controller.contadoresPrazo[prazo.id] || 0}`,
  }));

  return (
    <section className="rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="border-b border-slate-200 p-4 dark:border-slate-800 sm:p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="m-0 text-base font-semibold text-slate-900 dark:text-slate-100">
              Fila de recompra
            </h2>
            <p className="v2-texto-ajuda mt-1">
              Cada faixa de prazo é exclusiva; atrasados não contam nos próximos 7 dias.
            </p>
          </div>
          <div className="lg:w-80">
            <InputTexto
              id="lembretes-busca"
              left={<Search className="h-4 w-4 text-slate-400" aria-hidden="true" />}
              onChange={controller.setBusca}
              placeholder="Cliente, pet ou produto"
              type="search"
              value={controller.busca}
            />
          </div>
        </div>
        <div className="mt-4 flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
          <SeletorOpcoes
            aoSelecionar={controller.setFiltroPrazo}
            opcoes={opcoesPrazo}
            rotulo="Prazo"
            valorSelecionado={controller.filtroPrazo}
          />
          <div className="xl:w-64">
            <InputCombobox
              id="lembretes-tipo"
              label="Tipo"
              onChange={(valor) => controller.setFiltroTipo(valor || "todos")}
              opcoes={OPCOES_TIPO}
              permitirLimpar={false}
              value={controller.filtroTipo}
            />
          </div>
        </div>
      </div>

      {controller.loading ? (
        <div className="p-5">
          <EstadoVazio icone={Bell} titulo="Carregando lembretes..." />
        </div>
      ) : controller.lembretesFiltrados.length === 0 ? (
        <div className="p-5">
          <EstadoVazio
            icone={Bell}
            titulo={
              controller.lembretes.length
                ? "Nenhum item corresponde aos filtros."
                : "Nenhuma recompra prevista."
            }
          />
        </div>
      ) : (
        <div className="divide-y divide-slate-100 dark:divide-slate-800">
          {controller.lembretesFiltrados.map((lembrete) => (
            <LembreteCard controller={controller} key={lembrete.id} lembrete={lembrete} />
          ))}
        </div>
      )}
    </section>
  );
}
