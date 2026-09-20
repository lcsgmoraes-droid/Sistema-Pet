import { useMemo, useState } from "react";
import { FiBell, FiGift, FiMessageCircle, FiRefreshCw, FiSearch } from "react-icons/fi";
import { formatarDataHora } from "./lembretesFormatters";

const PERIODS = [
  { id: "hoje", label: "Hoje", accepts: (days) => days === 0 },
  { id: "amanha", label: "Amanhã", accepts: (days) => days === 1 },
  { id: "7dias", label: "Próximos 7 dias", accepts: (days) => days >= 0 && days <= 7 },
  { id: "30dias", label: "Próximos 30 dias", accepts: (days) => days >= 0 && days <= 30 },
];

function normalize(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
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

  const counts = useMemo(
    () =>
      Object.fromEntries(
        PERIODS.map((item) => [
          item.id,
          controller.aniversariantes.filter((birthday) => item.accepts(birthday.dias_restantes))
            .length,
        ]),
      ),
    [controller.aniversariantes],
  );

  return (
    <section className="mb-5 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <header className="border-b border-slate-200 p-4 dark:border-slate-700 sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-pink-50 text-pink-700 ring-1 ring-pink-200 dark:bg-pink-500/10 dark:text-pink-300 dark:ring-pink-500/30">
              <FiGift aria-hidden="true" />
            </span>
            <div>
              <h2 className="m-0 text-base font-semibold text-slate-900 dark:text-slate-100">
                Aniversariantes — tutor e pet
              </h2>
              <p className="mt-1 max-w-2xl text-xs text-slate-500 dark:text-slate-400">
                Prepare uma mensagem individual, abra o WhatsApp ou envie novamente uma notificação
                pelo app.
              </p>
            </div>
          </div>
          <button
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            disabled={controller.loadingAniversariantes}
            onClick={() => void controller.carregarAniversariantes()}
            type="button"
          >
            <FiRefreshCw
              aria-hidden="true"
              className={controller.loadingAniversariantes ? "animate-spin" : ""}
            />
            Atualizar
          </button>
        </div>

        <div className="mt-4 flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap gap-2" aria-label="Período dos aniversários">
            {PERIODS.map((item) => (
              <button
                className={`rounded-full px-3 py-1.5 text-xs font-semibold ring-1 ring-inset transition ${
                  period === item.id
                    ? "bg-pink-600 text-white ring-pink-600"
                    : "bg-white text-slate-600 ring-slate-200 hover:bg-slate-50 dark:bg-slate-900 dark:text-slate-300 dark:ring-slate-700 dark:hover:bg-slate-800"
                }`}
                key={item.id}
                onClick={() => setPeriod(item.id)}
                type="button"
              >
                {item.label} · {counts[item.id] || 0}
              </button>
            ))}
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <label className="relative block sm:w-64">
              <span className="sr-only">Buscar aniversariante</span>
              <FiSearch
                aria-hidden="true"
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
              />
              <input
                className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm text-slate-800 outline-none focus:border-pink-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Tutor ou pet"
                type="search"
                value={search}
              />
            </label>
            <select
              aria-label="Tipo de aniversariante"
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-pink-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200"
              onChange={(event) => setType(event.target.value)}
              value={type}
            >
              <option value="todos">Tutor e pet</option>
              <option value="tutor">Somente tutores</option>
              <option value="pet">Somente pets</option>
            </select>
          </div>
        </div>
      </header>

      {controller.loadingAniversariantes ? (
        <Empty text="Carregando aniversariantes..." />
      ) : filtered.length === 0 ? (
        <Empty text="Nenhum aniversariante encontrado neste período." />
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
        <span className="inline-flex rounded-full bg-pink-50 px-2.5 py-1 text-xs font-bold text-pink-700 ring-1 ring-inset ring-pink-200 dark:bg-pink-500/10 dark:text-pink-300 dark:ring-pink-500/30">
          {dateLabel(item)}
        </span>
        <p className="mt-2 text-sm font-semibold text-slate-800 dark:text-slate-200">
          {birthdayDate}
        </p>
        <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
          {item.idade > 0 ? `${item.idade} anos` : "Idade não informada"}
        </p>
      </div>

      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="m-0 text-base font-semibold text-slate-900 dark:text-slate-100">
            {item.aniversariante_nome}
          </h3>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            {item.tipo_aniversario === "pet" ? "Pet" : "Tutor"}
          </span>
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
          <FiMessageCircle aria-hidden="true" className="mr-1 inline" />
          {item.contatos_total || 0} contato(s) neste aniversário
          {lastContact?.criado_em ? ` · último em ${formatarDataHora(lastContact.criado_em)}` : ""}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2 xl:justify-end">
        <button
          className="inline-flex items-center gap-2 rounded-lg bg-teal-700 px-3 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-800"
          onClick={() => controller.abrirContato(item)}
          type="button"
        >
          <FiMessageCircle aria-hidden="true" /> Criar mensagem
        </button>
        <button
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-45 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
          disabled={!item.cliente_tem_app || pushLoading}
          onClick={() => controller.enviarPush(item)}
          title={
            item.cliente_tem_app
              ? "Enviar novamente uma notificação no app"
              : "Push indisponível: cliente sem conta vinculada no app"
          }
          type="button"
        >
          <FiBell className={pushLoading ? "animate-pulse" : ""} aria-hidden="true" />
          {pushLoading ? "Enviando..." : "Push"}
        </button>
      </div>
    </article>
  );
}

function Empty({ text }) {
  return (
    <div className="px-5 py-12 text-center text-sm text-slate-500 dark:text-slate-400">
      <FiGift aria-hidden="true" className="mx-auto mb-3" size={24} />
      {text}
    </div>
  );
}
