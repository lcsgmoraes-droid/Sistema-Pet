import { AlertTriangle, Building2, History, SearchX, UserRound } from "lucide-react";
import { useState } from "react";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import EstadoVazio from "../../components/v2/EstadoVazio/EstadoVazio";
import InputCheckGroup from "../../components/v2/InputCheckGroup/InputCheckGroup";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import { MODULOS_INFO, MODULOS_PREMIUM } from "../../contexts/ModulosContext";
import { modulosAlterados, modulosAtivos, modulosDoPlano, nomeDoModulo } from "./opsLojasUtils";
import OpsLojasHistoricoModal from "./OpsLojasHistoricoModal";
import useOpsLojas from "./useOpsLojas";

const OPCOES_DE_MODULO = [...MODULOS_PREMIUM]
  .sort((a, b) =>
    nomeDoModulo(a, MODULOS_INFO).localeCompare(nomeDoModulo(b, MODULOS_INFO), "pt-BR"),
  )
  .map((codigo) => ({ value: codigo, label: nomeDoModulo(codigo, MODULOS_INFO) }));

const ROTULO_DE_STATUS = {
  active: "Ativa",
  ativo: "Ativa",
  trial: "Em teste",
  inactive: "Inativa",
  suspended: "Suspensa",
};

function CartaoDaLoja({ loja, onAlternar, onHistorico, salvando }) {
  const ativos = modulosAtivos(loja);
  const doPlano = modulosDoPlano(loja);
  const responsavel = loja.principal;

  return (
    <li className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-base font-bold text-slate-950 dark:text-slate-100">{loja.nome}</h3>
          <p className="mt-0.5 flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
            <UserRound className="h-3.5 w-3.5" aria-hidden="true" />
            {responsavel
              ? `${responsavel.nome || "Sem nome"} · ${responsavel.email || "sem e-mail"}`
              : "Nenhum usuário cadastrado"}
          </p>
          <p className="mt-0.5 text-xs text-slate-400 dark:text-slate-500">ID {loja.id}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full border border-slate-300 px-2 py-0.5 text-xs font-semibold text-slate-700 dark:border-slate-600 dark:text-slate-200">
            {ROTULO_DE_STATUS[String(loja.status || "").toLowerCase()] ||
              loja.status ||
              "Sem status"}
          </span>
          <BotaoInteracao icon={History} tamanho="pequeno" onClick={() => onHistorico(loja)}>
            Histórico
          </BotaoInteracao>
        </div>
      </div>

      {loja.acesso_bloqueado_por_cobranca ? (
        <p className="mt-3 flex items-center gap-1 text-sm font-medium text-red-700 dark:text-red-300">
          <AlertTriangle className="h-4 w-4" aria-hidden="true" />
          Cobrança com problema: a loja está sem acesso aos módulos, mesmo os ativados.
        </p>
      ) : null}

      <div className="mt-3">
        <InputCheckGroup
          name={`modulos-${loja.id}`}
          label={`Módulos ativos: ${ativos.length} de ${OPCOES_DE_MODULO.length}`}
          opcoes={OPCOES_DE_MODULO}
          value={ativos}
          disabled={salvando}
          onChange={(proximos) => {
            const mudanca = modulosAlterados(ativos, proximos);
            if (mudanca) onAlternar(loja, mudanca.modulo, mudanca.ativar);
          }}
        />
      </div>

      {doPlano.length > 0 ? (
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
          Vêm do plano ou do teste grátis (não se desligam aqui):{" "}
          {doPlano.map((codigo) => nomeDoModulo(codigo, MODULOS_INFO)).join(", ")}.
        </p>
      ) : null}
    </li>
  );
}

export default function OpsLojasPage() {
  const { alternarModulo, busca, carregando, cortou, erro, grupos, lojas, salvando, setBusca } =
    useOpsLojas();
  const [historico, setHistorico] = useState(null); // { loja } ou { loja: null } (geral)
  const nomesPorId = Object.fromEntries(lojas.map((loja) => [loja.id, loja.nome]));

  return (
    <div className="mx-auto w-full max-w-6xl p-4 sm:p-6">
      <header className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="m-0 text-xs font-bold uppercase tracking-[0.18em] text-teal-700 dark:text-teal-300">
            Plataforma
          </p>
          <h1 className="mt-1 text-2xl font-bold text-slate-950 dark:text-slate-100 sm:text-3xl">
            Lojas e módulos
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600 dark:text-slate-400">
            Veja cada loja, o agrupamento dela e os módulos ativos. Clique em um módulo para ativar
            ou desativar.
          </p>
        </div>
        <BotaoInteracao icon={History} onClick={() => setHistorico({ loja: null })}>
          Histórico geral
        </BotaoInteracao>
      </header>

      <div className="mb-4 max-w-md">
        <InputTexto
          id="ops-lojas-busca"
          label="Buscar loja"
          placeholder="Nome ou ID da loja"
          value={busca}
          onChange={setBusca}
        />
      </div>

      {erro ? (
        <p role="alert" className="mb-3 text-sm font-medium text-red-700 dark:text-red-300">
          {erro}
        </p>
      ) : null}

      {carregando ? (
        <div role="status" aria-label="Carregando as lojas" className="space-y-3">
          {[0, 1, 2].map((item) => (
            <div
              key={item}
              className="h-40 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-900"
            />
          ))}
        </div>
      ) : lojas.length === 0 ? (
        <EstadoVazio
          icone={busca.trim() ? SearchX : Building2}
          titulo={busca.trim() ? "Nenhuma loja encontrada" : "Nenhuma loja cadastrada"}
          descricao={busca.trim() ? "Tente outro nome ou limpe a busca." : undefined}
        />
      ) : (
        <div className="space-y-6">
          {grupos.map((grupo) => (
            <section key={grupo.chave} aria-label={`Agrupamento ${grupo.nome}`}>
              <h2 className="mb-2 flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-200">
                <Building2 className="h-4 w-4" aria-hidden="true" />
                Agrupamento: {grupo.nome}
                <span className="text-xs font-normal text-slate-500 dark:text-slate-400">
                  ({grupo.lojas.length} {grupo.lojas.length === 1 ? "loja" : "lojas"})
                </span>
              </h2>
              <ul className="space-y-3">
                {grupo.lojas.map((loja) => (
                  <CartaoDaLoja
                    key={loja.id}
                    loja={loja}
                    salvando={Boolean(salvando[loja.id])}
                    onAlternar={alternarModulo}
                    onHistorico={(alvo) => setHistorico({ loja: alvo })}
                  />
                ))}
              </ul>
            </section>
          ))}
          {cortou ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Mostrando as primeiras lojas. Use a busca para achar uma específica.
            </p>
          ) : null}
        </div>
      )}
      {historico ? (
        <OpsLojasHistoricoModal
          loja={historico.loja}
          nomesPorId={nomesPorId}
          onFechar={() => setHistorico(null)}
        />
      ) : null}
    </div>
  );
}
