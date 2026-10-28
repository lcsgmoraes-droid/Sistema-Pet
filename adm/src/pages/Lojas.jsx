import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronRight, Search, Store } from "lucide-react";
import { obter } from "../api/cliente";
import { Aviso, Carregando, Etiqueta, VazioComTexto } from "../components/ui";
import {
  nomesDosModulosAtivos,
  ordenarLojas,
  rotuloDoStatus,
  rotuloDoUltimoAcesso,
  totaisDasLojas,
} from "../lib/formatadores";

export default function Lojas() {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState("");
  const [busca, setBusca] = useState("");

  useEffect(() => {
    let ativo = true;
    (async () => {
      try {
        const resposta = await obter("/admin/lojas");
        if (ativo) setDados(resposta);
      } catch (falha) {
        if (ativo) setErro(falha.message);
      }
    })();
    return () => {
      ativo = false;
    };
  }, []);

  const lojas = useMemo(() => {
    const todas = ordenarLojas(dados?.items || []);
    const termo = busca.trim().toLocaleLowerCase("pt-BR");
    if (!termo) return todas;
    return todas.filter((loja) =>
      [loja.nome, loja.grupo?.nome, loja.principal?.email].some((valor) =>
        String(valor || "").toLocaleLowerCase("pt-BR").includes(termo),
      ),
    );
  }, [dados, busca]);

  const totais = totaisDasLojas(dados?.items || []);
  const catalogo = dados?.catalogo_de_modulos || [];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Lojas</h1>
        {dados ? (
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            {totais.lojas} lojas · {totais.usuarios} usuários · {totais.semUsuarioAtivo} sem usuário ativo
          </p>
        ) : null}
      </div>

      <div className="relative max-w-md">
        <label htmlFor="busca" className="sr-only">
          Buscar loja
        </label>
        <Search className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-500" aria-hidden="true" />
        <input
          id="busca"
          type="search"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          placeholder="Buscar por loja, grupo ou e-mail"
          className="min-h-[44px] w-full rounded-lg border border-slate-300 bg-white pl-10 pr-3 text-base dark:border-slate-600 dark:bg-slate-900"
        />
      </div>

      {erro ? <Aviso tom="erro">{erro}</Aviso> : null}
      {!dados && !erro ? <Carregando rotulo="Carregando lojas" /> : null}
      {dados?.cortou ? (
        <Aviso tom="atencao">Mostrando só as primeiras {dados.limite} lojas. Use a busca para achar as demais.</Aviso>
      ) : null}
      {dados && lojas.length === 0 ? (
        <VazioComTexto icone={Store} titulo="Nenhuma loja encontrada" descricao="Ajuste a busca para ver outras lojas." />
      ) : null}

      <ul className="space-y-3">
        {lojas.map((loja) => {
          const modulos = nomesDosModulosAtivos(loja, catalogo);
          return (
            <li key={loja.id}>
              <Link
                to={`/lojas/${loja.id}`}
                className="flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-4 hover:border-teal-600 dark:border-slate-800 dark:bg-slate-900"
              >
                <div className="min-w-0 flex-1 space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold">{loja.nome}</p>
                    <Etiqueta tom={loja.status === "active" ? "ok" : "atencao"}>{rotuloDoStatus(loja.status)}</Etiqueta>
                    {loja.acesso_bloqueado_por_cobranca ? <Etiqueta tom="erro">Bloqueada por cobrança</Etiqueta> : null}
                    {loja.grupo ? <Etiqueta>Grupo {loja.grupo.nome}</Etiqueta> : null}
                  </div>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    {loja.usuarios.ativos} de {loja.usuarios.total} usuários ativos · último acesso:{" "}
                    {rotuloDoUltimoAcesso(loja.usuarios.ultimo_acesso)}
                  </p>
                  <p className="text-sm">
                    <span className="font-medium">{loja.total_de_modulos_ativos} módulos:</span>{" "}
                    {modulos.length ? modulos.join(", ") : "nenhum ativo"}
                  </p>
                </div>
                <span className="flex items-center gap-1 text-sm font-medium text-teal-800 dark:text-teal-300">
                  Gerenciar
                  <ChevronRight className="h-5 w-5" aria-hidden="true" />
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
