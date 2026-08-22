import { useCallback, useEffect, useMemo, useState } from "react";
import {
  FiArrowRight,
  FiBell,
  FiBookOpen,
  FiCheckCircle,
  FiClock,
  FiLayers,
  FiRefreshCw,
} from "react-icons/fi";
import { Link } from "react-router-dom";
import { listarEvolucaoCorePet, marcarNovidadesComoVistas } from "../services/evolucaoCorePet";

const ABAS = [
  {
    id: "novidades",
    label: "Novidades",
    descricao: "Disponível para usar",
    status: ["disponivel"],
    icon: FiCheckCircle,
  },
  {
    id: "andamento",
    label: "Em andamento",
    descricao: "Desenvolvimento e testes",
    status: ["em_desenvolvimento", "em_testes"],
    icon: FiClock,
  },
  {
    id: "estudo",
    label: "Em estudo",
    descricao: "Próximos projetos",
    status: ["em_estudo", "planejado"],
    icon: FiLayers,
  },
];

const STATUS_INFO = {
  disponivel: {
    label: "Disponível",
    classe: "border-emerald-200 bg-emerald-50 text-emerald-700",
  },
  em_testes: {
    label: "Em testes",
    classe: "border-violet-200 bg-violet-50 text-violet-700",
  },
  em_desenvolvimento: {
    label: "Em desenvolvimento",
    classe: "border-blue-200 bg-blue-50 text-blue-700",
  },
  planejado: {
    label: "Planejado",
    classe: "border-amber-200 bg-amber-50 text-amber-700",
  },
  em_estudo: {
    label: "Em estudo",
    classe: "border-slate-200 bg-slate-50 text-slate-600",
  },
};

const FASE_DISPONIBILIDADE_INFO = {
  teste: {
    label: "Disponível — em fase de teste",
    classe: "border-violet-200 bg-violet-50 text-violet-700",
  },
  implantado: {
    label: "Implantado",
    classe: "border-emerald-200 bg-emerald-50 text-emerald-700",
  },
};

function obterStatusInfo(item) {
  if (item.status === "disponivel" && item.fase_disponibilidade) {
    return FASE_DISPONIBILIDADE_INFO[item.fase_disponibilidade] ?? STATUS_INFO.disponivel;
  }
  return STATUS_INFO[item.status] ?? STATUS_INFO.em_estudo;
}

function formatarData(value) {
  if (!value) return "";
  const [ano, mes, dia] = String(value).split("-").map(Number);
  if (!ano || !mes || !dia) return "";
  return new Date(ano, mes - 1, dia).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function CardEvolucao({ item }) {
  const status = obterStatusInfo(item);
  const implantado = item.status === "disponivel" && item.fase_disponibilidade === "implantado";
  const dataStatus = implantado
    ? item.implantado_em
    : item.status === "disponivel"
      ? item.publicado_em
      : item.atualizado_em;
  const rotuloData = implantado
    ? "Implantado"
    : item.status === "disponivel"
      ? "Disponível"
      : "Atualizado";
  return (
    <article
      className={`rounded-2xl border bg-white p-5 shadow-sm transition-shadow hover:shadow-md dark:bg-slate-900 ${
        item.destaque
          ? "border-[#a8d8d2] dark:border-cyan-700"
          : "border-slate-200 dark:border-slate-800"
      }`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${status.classe}`}>
          {status.label}
        </span>
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          {item.modulo}
        </span>
        {item.destaque ? (
          <span className="rounded-full bg-[#fff4d6] px-2.5 py-1 text-xs font-semibold text-[#8a6514]">
            Destaque
          </span>
        ) : null}
      </div>

      <h2 className="mt-4 text-lg font-bold text-slate-900 dark:text-white">{item.titulo}</h2>
      <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.resumo}</p>

      <div className="mt-4 flex flex-wrap gap-2">
        {(item.plataformas ?? []).map((plataforma) => (
          <span
            key={plataforma}
            className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400"
          >
            {plataforma}
          </span>
        ))}
      </div>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4 dark:border-slate-800">
        <span className="text-xs text-slate-400">
          {rotuloData} em {formatarData(dataStatus)}
        </span>
        {item.status === "disponivel" && item.caminho_ajuda ? (
          <Link
            to={item.caminho_ajuda}
            className="inline-flex items-center gap-2 text-sm font-semibold text-[#0f6f73] hover:text-[#0b5558] dark:text-cyan-300"
          >
            Ver como usar <FiArrowRight aria-hidden="true" />
          </Link>
        ) : null}
      </div>
    </article>
  );
}

export default function EvolucaoCorePet() {
  const [aba, setAba] = useState("novidades");
  const [itens, setItens] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro("");
    try {
      const response = await listarEvolucaoCorePet();
      setItens(response.itens);
      marcarNovidadesComoVistas(response.itens);
    } catch {
      setErro("Não foi possível carregar as novidades agora.");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const abaAtual = ABAS.find((item) => item.id === aba) ?? ABAS[0];
  const itensFiltrados = useMemo(
    () => itens.filter((item) => abaAtual.status.includes(item.status)),
    [abaAtual.status, itens],
  );

  return (
    <div className="min-h-screen bg-slate-50 pb-12 dark:bg-slate-950">
      <header className="bg-gradient-to-br from-[#0f5f63] via-[#0f7f80] to-[#c69a2d] px-4 py-10 text-white">
        <div className="mx-auto max-w-6xl">
          <div className="flex items-start justify-between gap-6">
            <div>
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-cyan-100">
                <FiBell aria-hidden="true" /> Novidades e próximos passos
              </div>
              <h1 className="text-3xl font-bold">Evolução do CorePet</h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-cyan-50 sm:text-base">
                Veja o que já pode ser usado, acompanhe o que está sendo construído e conheça as
                ideias que estamos estudando.
              </p>
            </div>
            <Link
              to="/ajuda?aba=central"
              className="hidden items-center gap-2 rounded-xl border border-white/30 bg-white/10 px-4 py-2.5 text-sm font-semibold hover:bg-white/20 sm:inline-flex"
            >
              <FiBookOpen aria-hidden="true" /> Central de Ajuda
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <div className="grid gap-3 sm:grid-cols-3">
          {ABAS.map((item) => {
            const Icone = item.icon;
            const quantidade = itens.filter((registro) =>
              item.status.includes(registro.status),
            ).length;
            const ativa = aba === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setAba(item.id)}
                className={`rounded-2xl border p-4 text-left transition-all ${
                  ativa
                    ? "border-[#0f8b8d] bg-[#e8f6f3] shadow-sm dark:border-cyan-500 dark:bg-cyan-950/30"
                    : "border-slate-200 bg-white hover:border-[#9bcfc9] dark:border-slate-800 dark:bg-slate-900"
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <Icone
                    className={ativa ? "text-[#0f6f73] dark:text-cyan-300" : "text-slate-400"}
                  />
                  <span className="rounded-full bg-white px-2 py-0.5 text-xs font-bold text-slate-600 shadow-sm dark:bg-slate-800 dark:text-slate-300">
                    {quantidade}
                  </span>
                </div>
                <p className="mt-3 font-bold text-slate-900 dark:text-white">{item.label}</p>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{item.descricao}</p>
              </button>
            );
          })}
        </div>

        {aba === "estudo" ? (
          <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Projetos em estudo ou planejados podem mudar conforme os testes e as prioridades. Quando
            entrarem em desenvolvimento, aparecerão na aba “Em andamento”.
          </div>
        ) : null}

        {carregando ? (
          <div className="flex min-h-64 items-center justify-center text-slate-500">
            <FiRefreshCw className="mr-2 animate-spin" /> Carregando evolução...
          </div>
        ) : erro ? (
          <div className="mt-8 rounded-2xl border border-red-200 bg-red-50 p-6 text-center">
            <p className="text-sm text-red-700">{erro}</p>
            <button
              type="button"
              onClick={carregar}
              className="mt-4 rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white"
            >
              Tentar novamente
            </button>
          </div>
        ) : itensFiltrados.length ? (
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            {itensFiltrados.map((item) => (
              <CardEvolucao key={item.id} item={item} />
            ))}
          </div>
        ) : (
          <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-8 text-center dark:border-slate-800 dark:bg-slate-900">
            <FiCheckCircle className="mx-auto text-3xl text-[#0f8b8d]" />
            <p className="mt-3 font-semibold text-slate-800 dark:text-white">
              Nenhum item nesta etapa no momento.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
