import { useEffect, useRef, useState } from "react";
import { FiPlusCircle, FiX } from "react-icons/fi";

import platformApi from "../../platformApi";
import { PLAN_EDIT_OPTIONS } from "./opsTenantsConstants";

function extrairErro(error, padrao) {
  return error?.response?.data?.detail || padrao;
}

const SELETOR_FOCAVEL =
  'button:not([disabled]), input:not([disabled]), select:not([disabled]), [href]';

export default function OpsAdicionarLojaModal({ grupo, onClose, onCreated }) {
  const [nomeLoja, setNomeLoja] = useState("");
  const [nomeAcesso, setNomeAcesso] = useState("");
  const [plan, setPlan] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const [resultado, setResultado] = useState(null);
  const painelRef = useRef(null);

  useEffect(() => {
    const primeiroFocavel = painelRef.current?.querySelector(SELETOR_FOCAVEL);
    primeiroFocavel?.focus();
  }, []);

  function handleKeyDown(event) {
    if (event.key === "Escape") {
      onClose();
      return;
    }
    if (event.key !== "Tab") return;

    const focaveis = Array.from(painelRef.current?.querySelectorAll(SELETOR_FOCAVEL) || []);
    if (focaveis.length === 0) return;
    const primeiro = focaveis[0];
    const ultimo = focaveis[focaveis.length - 1];

    if (event.shiftKey && document.activeElement === primeiro) {
      event.preventDefault();
      ultimo.focus();
    } else if (!event.shiftKey && document.activeElement === ultimo) {
      event.preventDefault();
      primeiro.focus();
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (nomeLoja.trim().length < 2) {
      setErro("Informe o nome da loja (pelo menos 2 caracteres).");
      return;
    }
    setErro("");
    setEnviando(true);
    try {
      const { data } = await platformApi.post(
        `/admin/grupos-comerciais/${grupo.grupoId}/lojas`,
        {
          nome_loja: nomeLoja.trim(),
          nome_acesso: nomeAcesso.trim() || undefined,
          plan: plan || undefined,
        },
      );
      setResultado(data);
      onCreated?.();
    } catch (error) {
      setErro(extrairErro(error, "Nao foi possivel provisionar a loja. Tente novamente."));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div
        ref={painelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="adicionar-loja-titulo"
        onKeyDown={handleKeyDown}
        className="w-full max-w-md rounded-lg bg-white p-5 shadow-xl"
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 id="adicionar-loja-titulo" className="text-base font-bold text-slate-900">
              Adicionar loja
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Nova loja dentro do grupo <span className="font-semibold">{grupo.nome}</span>. Sem
              trial gratuito — cliente ja pagante negociando uma loja a mais.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            aria-label="Fechar"
          >
            <FiX className="h-4 w-4" />
          </button>
        </div>

        {resultado ? (
          <div className="mt-4 space-y-3">
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-3 text-sm text-emerald-800">
              <p className="font-semibold">Loja "{resultado.nome}" criada e anexada ao grupo.</p>
              <p className="mt-1">
                Login: {resultado.login_name} · tenant {resultado.tenant_id}
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="inline-flex h-10 w-full items-center justify-center rounded-lg bg-slate-100 px-4 text-sm font-semibold text-slate-700 hover:bg-slate-200"
            >
              Fechar
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-4 space-y-4">
            <label className="block">
              <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                Nome da loja
              </span>
              <input
                type="text"
                value={nomeLoja}
                onChange={(event) => setNomeLoja(event.target.value)}
                placeholder="Ex.: Pet Feliz - Unidade Centro"
                maxLength={150}
                className="mt-1 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-700 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
              />
            </label>
            <label className="block">
              <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                Nome de acesso (opcional)
              </span>
              <input
                type="text"
                value={nomeAcesso}
                onChange={(event) => setNomeAcesso(event.target.value)}
                placeholder="Igual ao nome da loja, se em branco"
                maxLength={150}
                className="mt-1 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-700 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
              />
            </label>
            <label className="block">
              <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                Plano negociado
              </span>
              <select
                value={plan}
                onChange={(event) => setPlan(event.target.value)}
                className="mt-1 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-700 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
              >
                <option value="">Padrao do cadastro</option>
                {PLAN_EDIT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            {erro ? (
              <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {erro}
              </div>
            ) : null}

            <button
              type="submit"
              disabled={enviando}
              className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <FiPlusCircle
                className={`h-4 w-4 ${enviando ? "animate-pulse motion-reduce:animate-none" : ""}`}
              />
              {enviando ? "Criando..." : "Criar loja"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
