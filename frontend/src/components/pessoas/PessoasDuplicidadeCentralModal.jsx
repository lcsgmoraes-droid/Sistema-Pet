import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  GitMerge,
  Loader2,
  RefreshCw,
  ShieldCheck,
  X,
} from "lucide-react";
import ActionButton from "../ui/ActionButton";
import { motivoDuplicidadeLabel } from "./PessoasDuplicidadeBanner";

function chaveSugestao(sugestao) {
  return `${sugestao?.principal?.id || "principal"}:${sugestao?.duplicado?.id || "duplicado"}`;
}

function valorOuTraco(valor) {
  return String(valor || "").trim() || "-";
}

function PessoaCompacta({ pessoa, destaque }) {
  return (
    <div className={`min-w-0 rounded-lg border p-3 ${destaque}`}>
      <div className="truncate font-semibold text-slate-900">
        {pessoa?.nome || "Pessoa sem nome"}
      </div>
      <div className="mt-1 text-xs text-slate-500">
        Código {valorOuTraco(pessoa?.codigo)} · {valorOuTraco(pessoa?.tipo_cadastro)}
      </div>
      <div className="mt-2 grid gap-1 text-xs text-slate-600">
        <span>Documento: {valorOuTraco(pessoa?.documento)}</span>
        <span>Telefone: {valorOuTraco(pessoa?.telefone)}</span>
        <span className="truncate">E-mail: {valorOuTraco(pessoa?.email)}</span>
      </div>
    </div>
  );
}

export default function PessoasDuplicidadeCentralModal({
  isOpen,
  sugestoes = [],
  totalSugestoes = 0,
  totalAutomaticas = 0,
  skip = 0,
  limit = 25,
  verificando = false,
  onClose,
  onAtualizar,
  onMudarPagina,
  onRevisarSugestao,
  onRevisarSelecionadas,
  onFundirAutomaticas,
  onFundirAssistidasNome,
}) {
  const [selecionadas, setSelecionadas] = useState(() => new Map());

  useEffect(() => {
    if (!isOpen) setSelecionadas(new Map());
  }, [isOpen]);

  const sugestoesSelecionadas = useMemo(() => Array.from(selecionadas.values()), [selecionadas]);
  const paginaTodaSelecionada =
    sugestoes.length > 0 && sugestoes.every((item) => selecionadas.has(chaveSugestao(item)));
  const inicio = totalSugestoes > 0 ? skip + 1 : 0;
  const fim = Math.min(skip + sugestoes.length, totalSugestoes);
  const temPaginaAnterior = skip > 0;
  const temProximaPagina = skip + limit < totalSugestoes;

  if (!isOpen) return null;

  const alternarSugestao = (sugestao) => {
    const chave = chaveSugestao(sugestao);
    setSelecionadas((atual) => {
      const proxima = new Map(atual);
      if (proxima.has(chave)) proxima.delete(chave);
      else proxima.set(chave, sugestao);
      return proxima;
    });
  };

  const alternarPagina = () => {
    setSelecionadas((atual) => {
      const proxima = new Map(atual);
      sugestoes.forEach((sugestao) => {
        const chave = chaveSugestao(sugestao);
        if (paginaTodaSelecionada) proxima.delete(chave);
        else proxima.set(chave, sugestao);
      });
      return proxima;
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4">
      <div className="flex max-h-[94vh] w-full max-w-7xl flex-col overflow-hidden rounded-xl bg-white shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-full bg-amber-50 text-amber-700">
              <GitMerge size={22} aria-hidden="true" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900">
                Central de revisão de duplicidades
              </h2>
              <p className="text-sm text-slate-500">
                Selecione vários alertas e revise cada fusão em sequência, com dados e histórico
                preservados.
              </p>
            </div>
          </div>
          <button
            aria-label="Fechar central de duplicidades"
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            onClick={onClose}
            type="button"
          >
            <X size={22} />
          </button>
        </div>

        <div className="border-b border-slate-200 bg-slate-50 px-6 py-4">
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-lg border border-amber-200 bg-white p-3">
              <div className="text-xs font-semibold uppercase text-amber-700">Para revisar</div>
              <div className="mt-1 text-2xl font-bold text-slate-900">{totalSugestoes}</div>
            </div>
            <div className="rounded-lg border border-emerald-200 bg-white p-3">
              <div className="text-xs font-semibold uppercase text-emerald-700">Fusão segura</div>
              <div className="mt-1 text-2xl font-bold text-slate-900">{totalAutomaticas}</div>
            </div>
            <div className="rounded-lg border border-blue-200 bg-white p-3">
              <div className="text-xs font-semibold uppercase text-blue-700">Selecionados</div>
              <div className="mt-1 text-2xl font-bold text-slate-900">
                {sugestoesSelecionadas.length}
              </div>
            </div>
          </div>
          <div className="mt-3 flex items-start gap-2 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">
            <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
            <span>
              A seleção múltipla cria uma fila. Cadastros com conflitos não são fundidos às cegas:
              você confirma o principal e os valores de cada par.
            </span>
          </div>
        </div>

        <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-6 py-3">
          <label className="flex cursor-pointer items-center gap-2 text-sm font-medium text-slate-700">
            <input
              aria-label="Selecionar todos os alertas desta página"
              checked={paginaTodaSelecionada}
              className="h-4 w-4 rounded border-slate-300"
              disabled={verificando || sugestoes.length === 0}
              onChange={alternarPagina}
              type="checkbox"
            />
            Selecionar página
          </label>
          <ActionButton
            disabled={verificando}
            icon={verificando ? Loader2 : RefreshCw}
            intent="neutral"
            onClick={onAtualizar}
            size="sm"
            tone="soft"
          >
            Atualizar análise
          </ActionButton>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4">
          {verificando && sugestoes.length === 0 ? (
            <div className="flex items-center justify-center gap-2 p-10 text-slate-500">
              <Loader2 className="animate-spin" size={20} /> Carregando alertas...
            </div>
          ) : sugestoes.length === 0 ? (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-6 text-center text-emerald-900">
              Nenhuma duplicidade pendente de revisão nesta análise.
            </div>
          ) : (
            <div className="space-y-3">
              {sugestoes.map((sugestao) => {
                const chave = chaveSugestao(sugestao);
                const selecionada = selecionadas.has(chave);
                return (
                  <div
                    className={`rounded-xl border p-4 transition ${
                      selecionada ? "border-blue-400 bg-blue-50/40" : "border-slate-200 bg-white"
                    }`}
                    key={chave}
                  >
                    <div className="grid items-start gap-3 lg:grid-cols-[28px_1fr_28px_1fr_auto]">
                      <input
                        aria-label={`Selecionar possível duplicidade entre ${sugestao.principal?.nome || "pessoa"} e ${sugestao.duplicado?.nome || "pessoa"}`}
                        checked={selecionada}
                        className="mt-4 h-4 w-4 rounded border-slate-300"
                        onChange={() => alternarSugestao(sugestao)}
                        type="checkbox"
                      />
                      <PessoaCompacta
                        pessoa={sugestao.principal}
                        destaque="border-blue-200 bg-blue-50/50"
                      />
                      <div className="mt-8 text-center text-slate-400">×</div>
                      <PessoaCompacta
                        pessoa={sugestao.duplicado}
                        destaque="border-amber-200 bg-amber-50/50"
                      />
                      <ActionButton
                        icon={GitMerge}
                        intent="warning"
                        onClick={() => onRevisarSugestao(sugestao)}
                        size="sm"
                        tone="soft"
                      >
                        Revisar
                      </ActionButton>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2 pl-10">
                      {(sugestao.motivos || []).map((motivo) => (
                        <span
                          className="rounded-full bg-amber-100 px-2.5 py-1 text-xs text-amber-800"
                          key={motivo}
                        >
                          {motivoDuplicidadeLabel(motivo)}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-3 border-t border-slate-200 px-6 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <span>
              Mostrando {inicio}–{fim} de {totalSugestoes}
            </span>
            <ActionButton
              aria-label="Página anterior de duplicidades"
              disabled={!temPaginaAnterior || verificando}
              icon={ChevronLeft}
              intent="neutral"
              onClick={() => onMudarPagina(Math.max(0, skip - limit))}
              size="sm"
              tone="soft"
            >
              Anterior
            </ActionButton>
            <ActionButton
              aria-label="Próxima página de duplicidades"
              disabled={!temProximaPagina || verificando}
              icon={ChevronRight}
              iconPosition="right"
              intent="neutral"
              onClick={() => onMudarPagina(skip + limit)}
              size="sm"
              tone="soft"
            >
              Próxima
            </ActionButton>
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            {totalSugestoes > 0 && (
              <ActionButton
                disabled={verificando}
                icon={ShieldCheck}
                intent="create"
                onClick={onFundirAssistidasNome}
                size="md"
                tone="soft"
              >
                Fundir nomes iguais conferidos
              </ActionButton>
            )}
            {totalAutomaticas > 0 && (
              <ActionButton
                disabled={verificando}
                icon={ShieldCheck}
                intent="create"
                onClick={onFundirAutomaticas}
                size="md"
                tone="soft"
              >
                Fundir seguras
              </ActionButton>
            )}
            <ActionButton
              disabled={sugestoesSelecionadas.length === 0 || verificando}
              icon={AlertTriangle}
              intent="warning"
              onClick={() => onRevisarSelecionadas(sugestoesSelecionadas)}
              size="md"
            >
              Revisar selecionados ({sugestoesSelecionadas.length})
            </ActionButton>
          </div>
        </div>
      </div>
    </div>
  );
}
