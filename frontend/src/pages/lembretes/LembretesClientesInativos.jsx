import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import {
  FiChevronLeft,
  FiChevronRight,
  FiClock,
  FiCopy,
  FiMessageCircle,
  FiRefreshCw,
  FiSearch,
  FiUser,
  FiUsers,
} from "react-icons/fi";
import { useNavigate } from "react-router-dom";

import api from "../../api";
import { formatMoneyBRL } from "../../utils/formatters";
import { whatsappUrl } from "./lembretesUtils";

const PRAZOS_INATIVIDADE = [30, 60, 90];

function dataCurta(valor) {
  if (!valor) return "Sem data";
  return new Date(valor).toLocaleDateString("pt-BR", {
    timeZone: "America/Sao_Paulo",
  });
}

function telefoneValido(valor) {
  return String(valor || "").replace(/\D/g, "").length >= 10;
}

export default function LembretesClientesInativos() {
  const navigate = useNavigate();
  const [dias, setDias] = useState(30);
  const [busca, setBusca] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");
  const [pagina, setPagina] = useState(1);
  const [resultado, setResultado] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro("");
    try {
      const response = await api.get("/clientes/inativos", {
        params: {
          dias_sem_compra: dias,
          busca: buscaAplicada || undefined,
          pagina,
          por_pagina: 25,
        },
      });
      setResultado(response.data);
    } catch (error) {
      console.error("Erro ao carregar clientes inativos:", error);
      setErro(error?.response?.data?.detail || "Não foi possível carregar os clientes inativos.");
    } finally {
      setCarregando(false);
    }
  }, [buscaAplicada, dias, pagina]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const aplicarBusca = (event) => {
    event.preventDefault();
    setPagina(1);
    setBuscaAplicada(busca.trim());
  };

  const mudarPrazo = (novoPrazo) => {
    setDias(novoPrazo);
    setPagina(1);
  };

  const abrirWhatsApp = (cliente) => {
    const url = whatsappUrl(cliente.telefone, cliente.mensagem_sugerida);
    if (!url || !telefoneValido(cliente.telefone)) {
      toast.error("Cliente sem telefone válido para WhatsApp");
      return;
    }
    const popup = window.open("about:blank", "_blank");
    if (!popup) {
      toast.error("O navegador bloqueou a nova aba do WhatsApp");
      return;
    }
    popup.opener = null;
    popup.location.replace(url);
    toast.success("Conversa preparada no WhatsApp");
  };

  const copiarMensagem = async (cliente) => {
    try {
      await navigator.clipboard.writeText(cliente.mensagem_sugerida);
      toast.success("Mensagem copiada");
    } catch {
      toast.error("Não foi possível copiar a mensagem");
    }
  };

  const resumo = resultado?.resumo || {};
  const clientes = resultado?.clientes || [];
  const paginacao = resultado?.paginacao || {
    pagina: 1,
    total_paginas: 1,
    total: 0,
  };

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <header className="border-b border-slate-200 px-4 py-5 dark:border-slate-700 sm:px-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-50 text-teal-700 ring-1 ring-teal-200 dark:bg-teal-500/10 dark:text-teal-300 dark:ring-teal-500/30">
              <FiUsers aria-hidden="true" />
            </span>
            <div>
              <h2 className="m-0 text-base font-semibold text-slate-900 dark:text-slate-100">
                Clientes inativos
              </h2>
              <p className="mt-1 max-w-2xl text-xs text-slate-500 dark:text-slate-400">
                Clientes que já compraram, mas não voltaram no período escolhido. Nenhuma mensagem é
                enviada automaticamente.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => void carregar()}
            disabled={carregando}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <FiRefreshCw className={carregando ? "animate-spin" : ""} aria-hidden="true" />
            Atualizar
          </button>
        </div>

        <div className="mt-4 flex flex-wrap gap-2" aria-label="Período sem compra">
          {PRAZOS_INATIVIDADE.map((prazo) => (
            <button
              key={prazo}
              type="button"
              onClick={() => mudarPrazo(prazo)}
              className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
                dias === prazo
                  ? "bg-teal-600 text-white shadow-sm"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
              }`}
            >
              {prazo}+ dias
            </button>
          ))}
        </div>

        <form onSubmit={aplicarBusca} className="mt-4 flex max-w-xl gap-2">
          <label className="relative min-w-0 flex-1">
            <FiSearch
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />
            <span className="sr-only">Buscar cliente inativo</span>
            <input
              type="search"
              value={busca}
              onChange={(event) => setBusca(event.target.value)}
              placeholder="Buscar por nome, código, telefone ou e-mail"
              className="w-full rounded-lg border border-slate-200 bg-white py-2.5 pl-9 pr-3 text-sm text-slate-900 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
            />
          </label>
          <button
            type="submit"
            className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
          >
            Buscar
          </button>
        </form>
      </header>

      {!carregando && !erro && (
        <div className="grid grid-cols-1 gap-3 border-b border-slate-200 p-4 dark:border-slate-700 sm:grid-cols-3 sm:p-5">
          <ResumoCard
            icon={FiClock}
            label={`Sem comprar há ${dias}+ dias`}
            value={resumo.total_inativos || 0}
          />
          <ResumoCard
            icon={FiMessageCircle}
            label="Com WhatsApp"
            tone="green"
            value={resumo.com_whatsapp || 0}
          />
          <ResumoCard
            icon={FiUser}
            label="Sem telefone válido"
            tone="amber"
            value={resumo.sem_whatsapp || 0}
          />
        </div>
      )}

      {carregando && (
        <div className="px-5 py-12 text-center text-sm text-slate-500 dark:text-slate-400">
          Carregando clientes inativos...
        </div>
      )}

      {!carregando && erro && (
        <div className="px-5 py-10 text-center">
          <p className="text-sm text-red-600 dark:text-red-300">{erro}</p>
          <button
            type="button"
            onClick={() => void carregar()}
            className="mt-3 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 dark:border-slate-700 dark:text-slate-200"
          >
            Tentar novamente
          </button>
        </div>
      )}

      {!carregando && !erro && clientes.length === 0 && (
        <div className="px-5 py-12 text-center text-sm text-slate-500 dark:text-slate-400">
          Nenhum cliente inativo encontrado com esses filtros.
        </div>
      )}

      {!carregando && !erro && clientes.length > 0 && (
        <>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[940px] text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-950/50 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-3 text-left">Cliente</th>
                  <th className="px-4 py-3 text-center">Inatividade</th>
                  <th className="px-4 py-3 text-right">Última compra</th>
                  <th className="px-4 py-3 text-center">Compras</th>
                  <th className="px-4 py-3 text-right">Total comprado</th>
                  <th className="px-4 py-3 text-right">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {clientes.map((cliente) => {
                  const podeUsarWhatsApp = telefoneValido(cliente.telefone);
                  return (
                    <tr
                      key={cliente.cliente_id}
                      className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40"
                    >
                      <td className="px-4 py-3">
                        <p className="font-semibold text-slate-900 dark:text-slate-100">
                          {cliente.nome}
                        </p>
                        <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                          {cliente.codigo ? `Código ${cliente.codigo}` : `ID ${cliente.cliente_id}`}
                          {cliente.telefone ? ` · ${cliente.telefone}` : " · Sem telefone"}
                        </p>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="inline-flex rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-800 ring-1 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-200 dark:ring-amber-500/30">
                          {cliente.dias_sem_comprar} dias
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right text-slate-600 dark:text-slate-300">
                        {dataCurta(cliente.ultima_compra)}
                      </td>
                      <td className="px-4 py-3 text-center text-slate-600 dark:text-slate-300">
                        {Number(cliente.total_compras || 0).toLocaleString("pt-BR")}
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-slate-900 dark:text-slate-100">
                        {formatMoneyBRL(cliente.total_gasto)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => abrirWhatsApp(cliente)}
                            disabled={!podeUsarWhatsApp}
                            title={
                              podeUsarWhatsApp
                                ? "Abrir conversa com mensagem pronta"
                                : "Cliente sem telefone válido"
                            }
                            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-40"
                          >
                            <FiMessageCircle aria-hidden="true" /> WhatsApp
                          </button>
                          <button
                            type="button"
                            onClick={() => void copiarMensagem(cliente)}
                            title="Copiar mensagem sugerida"
                            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                          >
                            <FiCopy aria-hidden="true" /> Copiar
                          </button>
                          <button
                            type="button"
                            onClick={() => navigate(`/clientes/${cliente.cliente_id}/financeiro`)}
                            className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                          >
                            Ver cliente
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <footer className="flex items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 dark:border-slate-700 sm:px-5">
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Página {paginacao.pagina} de {paginacao.total_paginas} · {paginacao.total} cliente(s)
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                aria-label="Página anterior"
                disabled={pagina <= 1}
                onClick={() => setPagina((atual) => Math.max(1, atual - 1))}
                className="rounded-lg border border-slate-200 p-2 text-slate-600 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:text-slate-300"
              >
                <FiChevronLeft aria-hidden="true" />
              </button>
              <button
                type="button"
                aria-label="Próxima página"
                disabled={pagina >= paginacao.total_paginas}
                onClick={() => setPagina((atual) => atual + 1)}
                className="rounded-lg border border-slate-200 p-2 text-slate-600 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:text-slate-300"
              >
                <FiChevronRight aria-hidden="true" />
              </button>
            </div>
          </footer>
        </>
      )}
    </section>
  );
}

function ResumoCard({ icon: Icon, label, tone = "slate", value }) {
  const tones = {
    slate:
      "border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-200",
    green:
      "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200",
    amber:
      "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200",
  };

  return (
    <div className={`rounded-xl border px-4 py-3 ${tones[tone]}`}>
      <div className="flex items-center gap-2 text-xs font-medium opacity-80">
        <Icon aria-hidden="true" /> {label}
      </div>
      <p className="mt-1 text-2xl font-bold">{Number(value || 0).toLocaleString("pt-BR")}</p>
    </div>
  );
}
