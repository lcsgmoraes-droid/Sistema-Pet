import { Bell, Gift, MessageCircle, RefreshCw, Search } from "lucide-react";
import { useMemo, useState } from "react";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import EstadoVazio from "../../components/v2/EstadoVazio/EstadoVazio";
import Etiqueta from "../../components/v2/Etiqueta/Etiqueta";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import SeletorOpcoes from "../../components/v2/SeletorOpcoes/SeletorOpcoes";
import { formatarDataHora } from "./lembretesFormatters";

const PERIODS = [
  { id: "hoje", label: "Hoje", accepts: (days) => days === 0 },
  { id: "amanha", label: "Amanhã", accepts: (days) => days === 1 },
  { id: "7dias", label: "Próximos 7 dias", accepts: (days) => days >= 0 && days <= 7 },
  { id: "30dias", label: "Próximos 30 dias", accepts: (days) => days >= 0 && days <= 30 },
];

const OPCOES_TIPO = [
  { value: "todos", label: "Tutor e pet" },
  { value: "tutor", label: "Somente tutores" },
  { value: "pet", label: "Somente pets" },
];

function normalize(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

function dateLabel(item) {
  if (item.dias_restantes === 0) return "Hoje";
  if (item.dias_restantes === 1) return "Amanhã";
  return `Em ${item.dias_restantes} dias`;
}

export default function LembretesAniversariantes({ controller }) {
  const [period, setPeriod] = useState("7dias");
  const [type, setType] = useState("todos");
  const [search, setSearch] = useState("");
  const filtered = useMemo(() => {
    const selectedPeriod = PERIODS.find((item) => item.id === period) || PERIODS[2];
    const term = normalize(search);
    return controller.aniversariantes.filter((item) => {
      if (!selectedPeriod.accepts(item.dias_restantes)) return false;
      if (type !== "todos" && item.tipo_aniversario !== type) return false;
      return (
        !term ||
        [item.aniversariante_nome, item.cliente_nome, item.pet_nome].some((value) =>
          normalize(value).includes(term),
        )
      );
    });
  }, [controller.aniversariantes, period, search, type]);

  const opcoesPeriodo = useMemo(
    () =>
      PERIODS.map((item) => ({
        valor: item.id,
        rotulo: `${item.label} · ${
          controller.aniversariantes.filter((birthday) => item.accepts(birthday.dias_restantes))
            .length
        }`,
      })),
    [controller.aniversariantes],
  );

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <header className="border-b border-slate-200 p-4 dark:border-slate-700 sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="m-0 text-base font-semibold text-slate-900 dark:text-slate-100">
              Aniversariantes — tutor e pet
            </h2>
            <p className="v2-texto-ajuda mt-1 max-w-2xl">
              Prepare uma mensagem individual, abra o WhatsApp ou envie novamente uma notificação
              pelo app.
            </p>
          </div>
          <BotaoInteracao
            icon={RefreshCw}
            loading={controller.loadingAniversariantes}
            onClick={() => void controller.carregarAniversariantes()}
          >
            Atualizar
          </BotaoInteracao>
        </div>

        <div className="mt-4 flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
          <SeletorOpcoes
            aoSelecionar={setPeriod}
            opcoes={opcoesPeriodo}
            rotulo="Período"
            valorSelecionado={period}
          />
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="sm:w-64">
              <InputTexto
                id="aniversariantes-busca"
                left={<Search className="h-4 w-4 text-slate-400" aria-hidden="true" />}
                onChange={setSearch}
                placeholder="Tutor ou pet"
                type="search"
                value={search}
              />
            </div>
            <div className="sm:w-52">
              <InputCombobox
                id="aniversariantes-tipo"
                onChange={(valor) => setType(valor || "todos")}
                opcoes={OPCOES_TIPO}
                permitirLimpar={false}
                value={type}
              />
            </div>
          </div>
        </div>
      </header>

      {controller.loadingAniversariantes ? (
        <div className="p-5">
          <EstadoVazio icone={Gift} titulo="Carregando aniversariantes..." />
        </div>
      ) : filtered.length === 0 ? (
        <div className="p-5">
          <EstadoVazio icone={Gift} titulo="Nenhum aniversariante encontrado neste período." />
        </div>
      ) : (
        <div className="divide-y divide-slate-100 dark:divide-slate-800">
          {filtered.map((item) => (
            <BirthdayRow controller={controller} item={item} key={item.id} />
          ))}
        </div>
      )}
    </section>
  );
}

function BirthdayRow({ controller, item }) {
  const pushLoading = controller.acaoContato === `push-${item.contato_chave}`;
  const birthdayDate = new Date(`${item.data_aniversario}T12:00:00`).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
  });
  const lastContact = item.ultimo_contato;
  return (
    <article className="grid gap-4 p-4 transition hover:bg-slate-50/70 dark:hover:bg-slate-800/30 sm:p-5 xl:grid-cols-[145px_minmax(0,1fr)_auto] xl:items-center">
      <div>
        <Etiqueta tom="informativo">{dateLabel(item)}</Etiqueta>
        <p className="mt-2 text-sm font-semibold text-slate-800 dark:text-slate-200">
          {birthdayDate}
        </p>
        <p className="v2-texto-ajuda mt-0.5">
          {item.idade > 0 ? `${item.idade} anos` : "Idade não informada"}
        </p>
      </div>

      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="m-0 text-base font-semibold text-slate-900 dark:text-slate-100">
            {item.aniversariante_nome}
          </h3>
          <Etiqueta>{item.tipo_aniversario === "pet" ? "Pet" : "Tutor"}</Etiqueta>
        </div>
        {item.tipo_aniversario === "pet" && (
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            Tutor: {item.cliente_nome}
          </p>
        )}
        <p
          className={`mt-2 text-xs ${
            item.contatado_hoje
              ? "font-semibold text-amber-700 dark:text-amber-300"
              : "text-slate-500 dark:text-slate-400"
          }`}
        >
          <MessageCircle aria-hidden="true" className="mr-1 inline h-3 w-3" />
          {item.contatos_total || 0} contato(s) neste aniversário
          {lastContact?.criado_em ? ` · último em ${formatarDataHora(lastContact.criado_em)}` : ""}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2 xl:justify-end">
        <BotaoInteracao icon={MessageCircle} onClick={() => controller.abrirContato(item)}>
          Criar mensagem
        </BotaoInteracao>
        <BotaoInteracao
          disabled={!item.cliente_tem_app}
          icon={Bell}
          loading={pushLoading}
          onClick={() => controller.enviarPush(item)}
          title={
            item.cliente_tem_app
              ? "Enviar novamente uma notificação no app"
              : "Push indisponível: cliente sem conta vinculada no app"
          }
        >
          {pushLoading ? "Enviando..." : "Push"}
        </BotaoInteracao>
      </div>
    </article>
  );
}
