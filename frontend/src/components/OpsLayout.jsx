import { NavLink, Outlet, Link } from "react-router-dom";
import {
  FiActivity,
  FiArrowLeft,
  FiAlertTriangle,
  FiBarChart2,
  FiDatabase,
  FiHome,
  FiLogOut,
  FiServer,
  FiShield,
} from "react-icons/fi";

import { useAuth } from "../contexts/AuthContext";

const navItems = [
  {
    to: "/ops",
    label: "Cockpit",
    description: "Saude e alertas",
    icon: FiHome,
    end: true,
  },
  {
    to: "/ops/incidentes",
    label: "Incidentes",
    description: "Tenant, rota e request",
    icon: FiAlertTriangle,
  },
  {
    to: "/ops/observabilidade",
    label: "Observabilidade",
    description: "Erros, lentidao e tenants",
    icon: FiActivity,
  },
];

function getInitials(user) {
  const source = user?.nome || user?.name || user?.email || "Ops";
  return String(source)
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "OP";
}

export default function OpsLayout() {
  const { user, logout } = useAuth();
  const roleName = user?.role?.name || "admin";

  return (
    <div className="min-h-screen bg-slate-100 text-slate-950">
      <aside className="fixed inset-y-0 left-0 z-30 flex w-72 flex-col border-r border-slate-800 bg-slate-950 text-white shadow-xl">
        <div className="border-b border-slate-800 px-5 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-blue-600">
              <FiShield className="h-6 w-6" />
            </div>
            <div>
              <div className="text-base font-bold tracking-tight">MLProHub Ops</div>
              <div className="text-xs text-slate-400">Central operacional</div>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2">
              <div className="flex items-center gap-1 text-slate-400">
                <FiServer className="h-3.5 w-3.5" />
                Ambiente
              </div>
              <div className="mt-1 font-semibold text-emerald-300">Producao</div>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2">
              <div className="flex items-center gap-1 text-slate-400">
                <FiDatabase className="h-3.5 w-3.5" />
                Acesso
              </div>
              <div className="mt-1 truncate font-semibold text-blue-200">{roleName}</div>
            </div>
          </div>
        </div>

        <nav className="flex-1 space-y-2 overflow-y-auto px-3 py-4">
          <div className="px-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
            Operacao
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  [
                    "flex items-center gap-3 rounded-lg px-3 py-3 transition",
                    isActive
                      ? "bg-blue-600 text-white shadow-sm"
                      : "text-slate-300 hover:bg-slate-900 hover:text-white",
                  ].join(" ")
                }
              >
                <Icon className="h-5 w-5 shrink-0" />
                <span>
                  <span className="block text-sm font-semibold">{item.label}</span>
                  <span className="block text-xs text-current opacity-70">{item.description}</span>
                </span>
              </NavLink>
            );
          })}
        </nav>

        <div className="border-t border-slate-800 p-4">
          <Link
            to="/lembretes"
            className="mb-3 flex items-center gap-2 rounded-lg border border-slate-800 px-3 py-2 text-sm font-semibold text-slate-200 transition hover:bg-slate-900 hover:text-white"
          >
            <FiArrowLeft className="h-4 w-4" />
            Voltar ao Pet Shop
          </Link>

          <div className="flex items-center gap-3 rounded-lg bg-slate-900 px-3 py-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-700 text-sm font-bold">
              {getInitials(user)}
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-semibold">{user?.nome || user?.name || "Operador"}</div>
              <div className="truncate text-xs text-slate-400">{user?.email || "sessao ativa"}</div>
            </div>
            <button
              type="button"
              onClick={logout}
              className="rounded-md p-2 text-slate-400 transition hover:bg-slate-800 hover:text-white"
              title="Sair"
            >
              <FiLogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      <div className="min-h-screen pl-72">
        <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 px-6 py-4 backdrop-blur">
          <div className="flex items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-blue-600">
                <FiBarChart2 className="h-4 w-4" />
                Plataforma MLProHub
              </div>
              <h1 className="mt-1 text-xl font-bold text-slate-950">Central de saude e suporte</h1>
            </div>
            <div className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
              Operacao monitorada
            </div>
          </div>
        </header>

        <main>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
