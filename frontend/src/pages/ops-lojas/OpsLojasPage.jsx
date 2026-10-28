import { Building2, SearchX } from "lucide-react";
import { useNavigate } from "react-router-dom";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import EstadoVazio from "../../components/v2/EstadoVazio/EstadoVazio";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import { MODULOS_INFO } from "../../contexts/ModulosContext";
import {
  nomesDosModulosAtivos,
  rotuloDoStatus,
  rotuloDoUltimoAcesso,
  totaisDasLojas,
} from "./opsLojasUtils";
import useOpsLojas from "./useOpsLojas";

const MODULOS_VISIVEIS = 4;

function ModulosDaLoja({ loja }) {
  const nomes = nomesDosModulosAtivos(loja, MODULOS_INFO);
  if (nomes.length === 0) {
    return <span className="text-slate-500 dark:text-slate-400">Nenhum módulo ativo</span>;
  }
  const extras = nomes.length - MODULOS_VISIVEIS;
  return (
    <span title={nomes.join(", ")}>
      <strong>{nomes.length}</strong>{" "}
      <span className="text-slate-600 dark:text-slate-300">
        {nomes.slice(0, MODULOS_VISIVEIS).join(", ")}
        {extras > 0 ? ` e mais ${extras}` : ""}
      </span>
    </span>
  );
}

export default function OpsLojasPage() {
  const navigate = useNavigate();
  const { busca, carregando, cortou, erro, grupos, lojas, setBusca } = useOpsLojas();
  const totais = totaisDasLojas(lojas);

  return (
    <div className="mx-auto w-full max-w-7xl p-4 sm:p-6">
      <header className="mb-4">
        <p className="m-0 text-xs font-bold uppercase tracking-[0.18em] text-teal-700 dark:text-teal-300">
          Clientes
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-950 dark:text-slate-100 sm:text-3xl">
          Lojas
        </h1>
        <p className="mt-1 max-w-3xl text-sm text-slate-600 dark:text-slate-400">
          Cada loja com o agrupamento, os módulos ativos e quantos usuários têm acesso. Abra uma
          loja para ver os usuários, ativar ou desativar módulos e consultar o histórico.
        </p>
      </header>

      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div className="w-full max-w-md">
          <InputTexto
            id="ops-lojas-busca"
            label="Buscar loja"
            placeholder="Nome ou ID da loja"
            value={busca}
            onChange={setBusca}
          />
        </div>
        {!carregando && lojas.length > 0 ? (
          <p className="text-sm text-slate-600 dark:text-slate-300">
            {totais.lojas} loja(s) · {totais.usuarios} usuário(s)
            {totais.semUsuarioAtivo > 0
              ? ` · ${totais.semUsuarioAtivo} sem nenhum usuário ativo`
              : ""}
          </p>
        ) : null}
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
              className="h-24 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-900"
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
        <div className="space-y-5">
          {grupos.map((grupo) => (
            <section key={grupo.chave} aria-label={`Agrupamento ${grupo.nome}`}>
              <h2 className="mb-2 flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-200">
                <Building2 className="h-4 w-4" aria-hidden="true" />
                Agrupamento: {grupo.nome}
                <span className="text-xs font-normal text-slate-500 dark:text-slate-400">
                  ({grupo.lojas.length} {grupo.lojas.length === 1 ? "loja" : "lojas"})
                </span>
              </h2>
              <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
                <table className="w-full min-w-[820px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
                      <th className="p-3 font-semibold">Ações</th>
                      <th className="p-3 font-semibold">Loja</th>
                      <th className="p-3 font-semibold">Situação</th>
                      <th className="p-3 font-semibold">Plano</th>
                      <th className="p-3 font-semibold">Usuários</th>
                      <th className="p-3 font-semibold">Módulos ativos</th>
                      <th className="p-3 font-semibold">Último acesso</th>
                    </tr>
                  </thead>
                  <tbody>
                    {grupo.lojas.map((loja) => (
                      <tr
                        key={loja.id}
                        className="border-b border-slate-100 align-top last:border-0 dark:border-slate-800"
                      >
                        <td className="p-3">
                          <BotaoInteracao
                            tamanho="pequeno"
                            onClick={() => navigate(`/ops/lojas/${loja.id}`)}
                          >
                            Abrir
                          </BotaoInteracao>
                        </td>
                        <td className="p-3">
                          <span className="font-semibold text-slate-950 dark:text-slate-100">
                            {loja.nome}
                          </span>
                          <span className="block text-xs text-slate-500 dark:text-slate-400">
                            {loja.principal?.email || "Sem responsável cadastrado"}
                          </span>
                        </td>
                        <td className="p-3">
                          {rotuloDoStatus(loja.status)}
                          {loja.acesso_bloqueado_por_cobranca ? (
                            <span className="block text-xs font-medium text-red-700 dark:text-red-300">
                              Cobrança com problema
                            </span>
                          ) : null}
                        </td>
                        <td className="p-3">{loja.plano || "—"}</td>
                        <td className="p-3">
                          <strong>{loja.usuarios.ativos}</strong> ativo(s)
                          <span className="block text-xs text-slate-500 dark:text-slate-400">
                            de {loja.usuarios.total}
                          </span>
                        </td>
                        <td className="max-w-xs p-3">
                          <ModulosDaLoja loja={loja} />
                        </td>
                        <td className="whitespace-nowrap p-3">
                          {rotuloDoUltimoAcesso(loja.usuarios.ultimo_acesso)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ))}
          {cortou ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Mostrando as primeiras lojas. Use a busca para achar uma específica.
            </p>
          ) : null}
        </div>
      )}
    </div>
  );
}
