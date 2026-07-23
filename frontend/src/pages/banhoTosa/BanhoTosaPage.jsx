import { useEffect, useState } from "react";
import { FiRefreshCw } from "react-icons/fi";
import { Link } from "react-router-dom";
import { banhoTosaApi } from "./banhoTosaApi";
import { getApiErrorMessage } from "./banhoTosaUtils";
import BanhoTosaAgendaView from "./components/BanhoTosaAgendaView";
import BanhoTosaDashboardView from "./components/BanhoTosaDashboardView";
import BanhoTosaFechamentosView from "./components/BanhoTosaFechamentosView";
import BanhoTosaFilaView from "./components/BanhoTosaFilaView";
import BanhoTosaPacotesView from "./components/BanhoTosaPacotesView";
import BanhoTosaParametrosView from "./components/BanhoTosaParametrosView";
import BanhoTosaRelatoriosView from "./components/BanhoTosaRelatoriosView";
import BanhoTosaRecursosView from "./components/BanhoTosaRecursosView";
import BanhoTosaRetornosView from "./components/BanhoTosaRetornosView";
import BanhoTosaServicosView from "./components/BanhoTosaServicosView";
import BanhoTosaTaxiDogView from "./components/BanhoTosaTaxiDogView";

const navItems = [
  { view: "dashboard", path: "/banho-tosa", label: "Painel" },
  { view: "servicos", path: "/banho-tosa/servicos", label: "Servicos" },
  { view: "parametros", path: "/banho-tosa/parametros", label: "Parametros" },
  { view: "recursos", path: "/banho-tosa/recursos", label: "Recursos" },
  { view: "agenda", path: "/banho-tosa/agenda", label: "Agenda" },
  { view: "fila", path: "/banho-tosa/fila", label: "Fila do dia" },
  { view: "fechamentos", path: "/banho-tosa/fechamentos", label: "Fechamentos" },
  { view: "pacotes", path: "/banho-tosa/pacotes", label: "Pacotes" },
  { view: "retornos", path: "/banho-tosa/retornos", label: "Reagendar" },
  { view: "taxi-dog", path: "/banho-tosa/taxi-dog", label: "Taxi dog" },
  { view: "relatorios", path: "/banho-tosa/relatorios", label: "Relatorios" },
];

export default function BanhoTosaPage({ view = "dashboard" }) {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [dashboard, setDashboard] = useState(null);
  const [config, setConfig] = useState(null);
  const [funcionarios, setFuncionarios] = useState([]);
  const [recursos, setRecursos] = useState([]);
  const [servicos, setServicos] = useState([]);
  const [parametros, setParametros] = useState([]);

  async function carregarDados(silent = false) {
    if (silent) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError("");

    try {
      const [dashboardRes, configRes, funcionariosRes, recursosRes, servicosRes, parametrosRes] =
        await Promise.all([
          banhoTosaApi.dashboard(),
          banhoTosaApi.obterConfiguracao(),
          banhoTosaApi.listarFuncionariosApoio(),
          banhoTosaApi.listarRecursos(),
          banhoTosaApi.listarServicos(),
          banhoTosaApi.listarParametrosPorte(),
        ]);

      setDashboard(dashboardRes.data || null);
      setConfig(configRes.data || null);
      setFuncionarios(Array.isArray(funcionariosRes.data) ? funcionariosRes.data : []);
      setRecursos(Array.isArray(recursosRes.data) ? recursosRes.data : []);
      setServicos(Array.isArray(servicosRes.data) ? servicosRes.data : []);
      setParametros(Array.isArray(parametrosRes.data) ? parametrosRes.data : []);
    } catch (err) {
      setError(getApiErrorMessage(err, "Nao foi possivel carregar Banho & Tosa."));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    carregarDados();
  }, []);

  function renderView() {
    if (view === "servicos") {
      return <BanhoTosaServicosView servicos={servicos} onChanged={carregarDados} />;
    }

    if (view === "parametros") {
      return (
        <BanhoTosaParametrosView
          config={config}
          parametros={parametros}
          onChanged={carregarDados}
        />
      );
    }

    if (view === "recursos") {
      return <BanhoTosaRecursosView recursos={recursos} onChanged={carregarDados} />;
    }

    if (view === "agenda") {
      return (
        <BanhoTosaAgendaView recursos={recursos} servicos={servicos} onChanged={carregarDados} />
      );
    }

    if (view === "fila") {
      return (
        <BanhoTosaFilaView
          config={config}
          funcionarios={funcionarios}
          recursos={recursos}
          onChanged={carregarDados}
        />
      );
    }

    if (view === "fechamentos") {
      return <BanhoTosaFechamentosView onChanged={carregarDados} />;
    }

    if (view === "taxi-dog") {
      return <BanhoTosaTaxiDogView funcionarios={funcionarios} onChanged={carregarDados} />;
    }

    if (view === "pacotes") {
      return <BanhoTosaPacotesView servicos={servicos} onChanged={carregarDados} />;
    }

    if (view === "retornos") {
      return <BanhoTosaRetornosView />;
    }

    if (view === "relatorios") {
      return <BanhoTosaRelatoriosView />;
    }

    return (
      <BanhoTosaDashboardView
        dashboard={dashboard}
        config={config}
        servicos={servicos}
        parametros={parametros}
        onChanged={carregarDados}
      />
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 px-3 py-4 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-4">
        <header className="overflow-hidden rounded-lg border border-slate-200 bg-white p-3 shadow-sm sm:p-4">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <span className="inline-flex rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">
                Central operacional
              </span>
              <h1 className="mt-3 text-xl font-semibold tracking-tight text-slate-950 sm:text-2xl">
                Banho & Tosa
              </h1>
              <p className="mt-1 max-w-3xl text-sm text-slate-600">
                Agenda, operacao, servicos e custos em uma rotina mais organizada.
              </p>
            </div>

            <button
              type="button"
              onClick={() => carregarDados(true)}
              disabled={refreshing}
              className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-3.5 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:opacity-60 sm:w-auto"
            >
              <FiRefreshCw className={refreshing ? "animate-spin" : ""} />
              Atualizar
            </button>
          </div>

          <nav className="-mx-1 mt-4 flex gap-2 overflow-x-auto px-1 pb-1">
            {navItems.map((item) => {
              const active = item.view === view;
              return (
                <Link
                  key={item.view}
                  to={item.path}
                  className={`whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition ${
                    active
                      ? "bg-blue-600 text-white shadow-sm"
                      : "bg-white text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </header>

        {error && (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
            {error}
          </div>
        )}

        {loading ? (
          <div className="rounded-lg border border-slate-200 bg-white p-10 text-center shadow-sm">
            <div className="mx-auto h-10 w-10 animate-spin rounded-full border-4 border-blue-100 border-t-blue-600" />
            <p className="mt-4 text-sm font-semibold text-slate-500">Carregando modulo...</p>
          </div>
        ) : (
          renderView()
        )}
      </div>
    </div>
  );
}
