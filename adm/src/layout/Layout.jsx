import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { KeyRound, LayoutDashboard, LogOut, Menu, Store, X } from "lucide-react";
import { useAuth } from "../auth/AuthContext";

const ITENS = [
  { para: "/", rotulo: "Dashboard", icone: LayoutDashboard, fim: true },
  { para: "/lojas", rotulo: "Lojas", icone: Store },
];

const classeDoLink = ({ isActive }) =>
  [
    "flex min-h-[44px] items-center gap-3 rounded-lg px-3 text-sm font-medium",
    isActive
      ? "bg-teal-700 text-white dark:bg-teal-600"
      : "text-slate-700 hover:bg-slate-200 dark:text-slate-200 dark:hover:bg-slate-800",
  ].join(" ");

export default function Layout({ outlet = null }) {
  const { admin, sair } = useAuth();
  const [aberto, setAberto] = useState(false);
  const local = useLocation();

  useEffect(() => setAberto(false), [local.pathname]);

  const menu = (
    <nav aria-label="Principal" className="flex h-full flex-col">
      <p className="px-3 pb-4 text-lg font-bold">CorePet · Administração</p>
      <ul className="space-y-1">
        {ITENS.map(({ para, rotulo, icone: Icone, fim }) => (
          <li key={para}>
            <NavLink to={para} end={fim} className={classeDoLink}>
              <Icone className="h-5 w-5" aria-hidden="true" />
              {rotulo}
            </NavLink>
          </li>
        ))}
      </ul>
      <div className="mt-auto space-y-1 border-t border-slate-200 pt-4 dark:border-slate-800">
        <p className="truncate px-3 pb-2 text-xs text-slate-600 dark:text-slate-400" title={admin?.email}>
          {admin?.email}
        </p>
        <NavLink to="/trocar-senha" className={classeDoLink}>
          <KeyRound className="h-5 w-5" aria-hidden="true" />
          Trocar minha senha
        </NavLink>
        <button
          type="button"
          onClick={() => sair()}
          className="flex min-h-[44px] w-full items-center gap-3 rounded-lg px-3 text-sm font-medium text-slate-700 hover:bg-slate-200 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          <LogOut className="h-5 w-5" aria-hidden="true" />
          Sair
        </button>
      </div>
    </nav>
  );

  return (
    <div className="min-h-full lg:flex">
      <header className="flex items-center justify-between border-b border-slate-200 px-4 py-2 dark:border-slate-800 lg:hidden">
        <p className="font-bold">CorePet · Administração</p>
        <button
          type="button"
          aria-label={aberto ? "Fechar menu" : "Abrir menu"}
          aria-expanded={aberto}
          onClick={() => setAberto(!aberto)}
          className="flex h-11 w-11 items-center justify-center rounded-lg hover:bg-slate-200 dark:hover:bg-slate-800"
        >
          {aberto ? <X className="h-6 w-6" aria-hidden="true" /> : <Menu className="h-6 w-6" aria-hidden="true" />}
        </button>
      </header>

      {aberto ? <div className="border-b border-slate-200 p-4 dark:border-slate-800 lg:hidden">{menu}</div> : null}

      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 border-r border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 lg:block">
        {menu}
      </aside>

      <main className="min-w-0 flex-1 px-4 py-6 sm:px-8">
        {outlet ?? <Outlet />}
      </main>
    </div>
  );
}
