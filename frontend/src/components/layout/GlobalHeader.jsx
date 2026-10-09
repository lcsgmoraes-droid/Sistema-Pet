import {
  FiBell,
  FiCheckCircle,
  FiChevronDown,
  FiChevronUp,
  FiCreditCard,
  FiHelpCircle,
  FiLock,
  FiLogOut,
  FiMoon,
  FiRepeat,
  FiSun,
} from "react-icons/fi";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../../contexts/AuthContext";
import useNovidadesNaoVistas from "../../hooks/useNovidadesNaoVistas";
import { useTheme } from "../../theme/ThemeContext";
import ChangePasswordModal from "./ChangePasswordModal";
import { resolveLayoutSessionIdentity } from "./layoutSessionIdentity";

const COREPET_LOGO = "/brand/corepet/corepet-horizontal.png";

// Hambúrguer que vira X (e volta) com uma animação simples de 3 barras — o estado dele É o
// estado da sidebar (aberta = X, recolhida/fechada = hambúrguer). Antes vivia dentro da
// sidebar (só desktop, com uma versão separada só-fechar no mobile); agora é um único
// controle aqui no header, valendo pros dois modos.
function BotaoAlternarMenu({ aberto, onClick, title }) {
  const barra =
    "absolute left-1/2 top-1/2 h-0.5 w-3.5 -translate-x-1/2 rounded-full bg-[#0f5f63] transition-all duration-300 dark:bg-cyan-200";

  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      aria-expanded={aberto}
      aria-label={title}
      className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg border border-[#d8eee9] bg-white shadow-sm transition-colors hover:bg-[#d8eee9] dark:border-slate-800 dark:bg-slate-900 dark:hover:bg-slate-800"
    >
      <span className="relative block h-3.5 w-3.5">
        <span
          className={`${barra} ${aberto ? "translate-y-0 rotate-45" : "-translate-y-1 rotate-0"}`}
        />
        <span className={`${barra} ${aberto ? "opacity-0" : "opacity-100"}`} />
        <span
          className={`${barra} ${aberto ? "translate-y-0 -rotate-45" : "translate-y-1 rotate-0"}`}
        />
      </span>
    </button>
  );
}

// Barra fixa no topo, 100% da largura, acima da sidebar — reúne a marca e o
// controle de recolher/expandir (antes repetidos dentro da sidebar), a conta
// do usuário (antes um dropdown no rodapé da sidebar) e o seletor de "loja
// atuando", que agora é escolhida depois do login, não mais na tela dele.
export default function GlobalHeader({ isMobile, sidebarOpen, onToggleSidebar, user, logout }) {
  const [menuUsuarioAberto, setMenuUsuarioAberto] = useState(false);
  const [trocarSenhaAberto, setTrocarSenhaAberto] = useState(false);
  const [seletorLojaAberto, setSeletorLojaAberto] = useState(false);
  const [minhasLojas, setMinhasLojas] = useState([]);
  const [trocandoLojaId, setTrocandoLojaId] = useState(null);
  const [erroTroca, setErroTroca] = useState("");
  const userMenuRef = useRef(null);
  const lojaMenuRef = useRef(null);
  const novidadesNaoVistas = useNovidadesNaoVistas();
  const { isDark, toggleTheme } = useTheme();
  const { fetchMyTenants, switchTenant } = useAuth();

  const nomeUsuario = user?.name || user?.username || user?.email;
  const nivelAcesso = user?.role?.name || "";
  const inicialUsuario = (
    user?.name?.[0] ||
    user?.username?.[0] ||
    user?.email?.[0] ||
    ""
  ).toUpperCase();
  const { tenantLabel } = resolveLayoutSessionIdentity(user);
  const tenantAtualId = user?.tenant?.id;
  const outrasLojas = minhasLojas.filter((loja) => loja.id !== tenantAtualId);
  const podeTrocarLoja = minhasLojas.length > 1;

  useEffect(() => {
    let ativo = true;
    if (!user?.id) {
      setMinhasLojas([]);
      return undefined;
    }
    fetchMyTenants().then((lista) => {
      if (ativo) setMinhasLojas(lista);
    });
    return () => {
      ativo = false;
    };
  }, [user?.id]);

  useEffect(() => {
    if (!menuUsuarioAberto && !seletorLojaAberto) return undefined;

    const aoClicarFora = (evento) => {
      if (menuUsuarioAberto && !userMenuRef.current?.contains(evento.target)) {
        setMenuUsuarioAberto(false);
      }
      if (seletorLojaAberto && !lojaMenuRef.current?.contains(evento.target)) {
        setSeletorLojaAberto(false);
      }
    };
    const aoPressionarTecla = (evento) => {
      if (evento.key === "Escape") {
        setMenuUsuarioAberto(false);
        setSeletorLojaAberto(false);
      }
    };

    document.addEventListener("mousedown", aoClicarFora);
    document.addEventListener("keydown", aoPressionarTecla);
    return () => {
      document.removeEventListener("mousedown", aoClicarFora);
      document.removeEventListener("keydown", aoPressionarTecla);
    };
  }, [menuUsuarioAberto, seletorLojaAberto]);

  const trocarLoja = async (tenantId) => {
    setErroTroca("");
    setTrocandoLojaId(tenantId);
    const resultado = await switchTenant(tenantId);
    if (!resultado.success) {
      setErroTroca(resultado.error || "Não foi possível trocar de loja.");
      setTrocandoLojaId(null);
    }
    // Em caso de sucesso, switchTenant já recarrega a página — não precisa
    // limpar nenhum estado local aqui.
  };

  return (
    <header className="erp-topbar relative z-[60] flex h-14 w-full flex-shrink-0 items-center justify-between gap-3 border-b border-[#d8eee9] bg-white/90 px-4 dark:border-slate-800 dark:bg-slate-950/90">
      <div className="flex items-center gap-2">
        <img
          src={COREPET_LOGO}
          alt="CorePet"
          className="h-8 w-auto max-w-[140px] object-contain"
        />
        <BotaoAlternarMenu
          aberto={sidebarOpen}
          onClick={onToggleSidebar}
          title={
            isMobile
              ? sidebarOpen
                ? "Fechar menu"
                : "Abrir menu"
              : sidebarOpen
                ? "Recolher menu"
                : "Expandir menu"
          }
        />
      </div>

      <div className="flex items-center gap-3">
        <div ref={lojaMenuRef} className="relative">
          <button
            type="button"
            onClick={() => podeTrocarLoja && setSeletorLojaAberto((aberto) => !aberto)}
            disabled={!podeTrocarLoja}
            aria-haspopup={podeTrocarLoja ? "menu" : undefined}
            aria-expanded={podeTrocarLoja ? seletorLojaAberto : undefined}
            className={`flex items-center gap-2 rounded-lg border-2 border-[#0f5f63] bg-[#0f5f63] px-3.5 py-2 text-sm font-bold text-white shadow-sm transition-colors dark:border-cyan-500 dark:bg-cyan-700 ${
              podeTrocarLoja ? "cursor-pointer hover:bg-[#0c4d50] dark:hover:bg-cyan-600" : "cursor-default"
            }`}
            title={podeTrocarLoja ? `Loja selecionada: ${tenantLabel} — clique para trocar` : `Loja selecionada: ${tenantLabel}`}
          >
            <FiCheckCircle className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
            <span className="max-w-[12rem] truncate" title={tenantLabel}>
              {tenantLabel}
            </span>
            {podeTrocarLoja ? (
              <>
                <FiRepeat className="h-3.5 w-3.5 flex-shrink-0" aria-hidden="true" />
                {seletorLojaAberto ? (
                  <FiChevronUp className="h-3.5 w-3.5 flex-shrink-0" />
                ) : (
                  <FiChevronDown className="h-3.5 w-3.5 flex-shrink-0" />
                )}
              </>
            ) : null}
          </button>

          {podeTrocarLoja && seletorLojaAberto ? (
            <div
              role="menu"
              aria-label="Trocar de loja"
              className="absolute right-0 top-full z-30 mt-2 w-64 overflow-hidden rounded-xl border border-[#d8eee9] bg-white py-1 shadow-lg dark:border-slate-800 dark:bg-slate-900"
            >
              <div className="px-4 py-2 text-xs font-bold uppercase tracking-wide text-slate-400 dark:text-slate-500">
                Trocar de loja
              </div>
              {outrasLojas.map((loja) => (
                <button
                  key={loja.id}
                  type="button"
                  role="menuitem"
                  disabled={trocandoLojaId === loja.id}
                  onClick={() => trocarLoja(loja.id)}
                  className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-gray-700 transition-all hover:bg-gray-50 disabled:cursor-wait disabled:opacity-60 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  <span className="truncate">{loja.name || loja.login_name}</span>
                  {trocandoLojaId === loja.id ? (
                    <span className="ml-auto text-xs text-slate-400">Trocando…</span>
                  ) : null}
                </button>
              ))}
              {erroTroca ? (
                <div className="px-4 py-2 text-xs text-rose-600 dark:text-rose-400">{erroTroca}</div>
              ) : null}
            </div>
          ) : null}
        </div>

        <div ref={userMenuRef} className="relative">
          <button
            type="button"
            onClick={() => setMenuUsuarioAberto((aberto) => !aberto)}
            aria-haspopup="menu"
            aria-expanded={menuUsuarioAberto}
            className="flex items-center gap-2.5 rounded-lg px-2 py-1.5 text-left transition-all hover:bg-[#d8eee9]/60 dark:hover:bg-slate-900/60"
          >
            <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-[#0f5f63] text-sm font-bold text-white">
              {inicialUsuario}
            </span>
            <span className="flex min-w-0 flex-col items-start">
              <span className="max-w-[10rem] truncate text-sm font-medium text-gray-900 dark:text-slate-100">
                {nomeUsuario}
              </span>
              {nivelAcesso ? (
                <span className="max-w-[10rem] truncate text-xs text-slate-400 dark:text-slate-500">
                  {nivelAcesso}
                </span>
              ) : null}
            </span>
            {menuUsuarioAberto ? (
              <FiChevronUp className="flex-shrink-0 text-gray-400 dark:text-slate-500" />
            ) : (
              <FiChevronDown className="flex-shrink-0 text-gray-400 dark:text-slate-500" />
            )}
          </button>

          {menuUsuarioAberto ? (
            <div
              role="menu"
              aria-label="Menu do usuário"
              className="absolute right-0 top-full z-30 mt-2 w-64 overflow-hidden rounded-xl border border-[#d8eee9] bg-white py-1 shadow-lg dark:border-slate-800 dark:bg-slate-900"
            >
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  toggleTheme();
                  setMenuUsuarioAberto(false);
                }}
                className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-gray-700 transition-all hover:bg-gray-50 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                {isDark ? (
                  <FiSun className="flex-shrink-0 text-lg" />
                ) : (
                  <FiMoon className="flex-shrink-0 text-lg" />
                )}
                <span className="v2-menu-item font-medium">
                  {isDark ? "Usar tela clara" : "Usar tela escura"}
                </span>
              </button>
              <Link
                to="/meu-plano"
                role="menuitem"
                onClick={() => setMenuUsuarioAberto(false)}
                className="flex w-full items-center gap-3 px-4 py-2.5 text-emerald-700 transition-all hover:bg-emerald-50 dark:text-emerald-300 dark:hover:bg-emerald-500/10"
              >
                <FiCreditCard className="flex-shrink-0 text-lg" />
                <span className="v2-menu-item font-medium">Meu Plano</span>
              </Link>
              <Link
                to="/novidades"
                role="menuitem"
                onClick={() => setMenuUsuarioAberto(false)}
                className="flex w-full items-center gap-3 px-4 py-2.5 text-[#9a6b05] transition-all hover:bg-[#fff1c9] dark:text-amber-300 dark:hover:bg-amber-500/10"
              >
                <FiBell className="flex-shrink-0 text-lg" />
                <span className="v2-menu-item font-medium">Novidades</span>
                {novidadesNaoVistas > 0 ? (
                  <span
                    className="ml-auto inline-flex min-w-5 items-center justify-center rounded-full bg-red-600 px-1.5 py-0.5 text-[10px] font-bold text-white"
                    aria-label={`${novidadesNaoVistas} novidade(s) não vista(s)`}
                  >
                    {novidadesNaoVistas > 9 ? "9+" : novidadesNaoVistas}
                  </span>
                ) : null}
              </Link>
              <Link
                to="/ajuda"
                role="menuitem"
                onClick={() => setMenuUsuarioAberto(false)}
                className="flex w-full items-center gap-3 px-4 py-2.5 text-[#0f5f63] transition-all hover:bg-[#d8eee9] dark:text-cyan-200 dark:hover:bg-slate-800"
              >
                <FiHelpCircle className="flex-shrink-0 text-lg" />
                <span className="v2-menu-item font-medium">Ajuda & Planos</span>
              </Link>
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setMenuUsuarioAberto(false);
                  setTrocarSenhaAberto(true);
                }}
                className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-gray-700 transition-all hover:bg-gray-50 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                <FiLock className="flex-shrink-0 text-lg" />
                <span className="v2-menu-item font-medium">Trocar senha</span>
              </button>
              <div className="my-1 border-t border-[#d8eee9] dark:border-slate-800" />
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setMenuUsuarioAberto(false);
                  logout();
                }}
                className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-gray-700 transition-all hover:bg-red-50 hover:text-red-600 dark:text-slate-300 dark:hover:bg-red-500/10 dark:hover:text-red-200"
              >
                <FiLogOut className="flex-shrink-0 text-lg" />
                <span className="v2-menu-item font-medium">Sair</span>
              </button>
            </div>
          ) : null}
        </div>
      </div>

      {trocarSenhaAberto ? (
        <ChangePasswordModal onClose={() => setTrocarSenhaAberto(false)} />
      ) : null}
    </header>
  );
}
