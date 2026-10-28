import { AlertTriangle, History, LayoutList, Package, Users } from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router-dom";
import AbasNavegacao from "../../components/v2/AbasNavegacao/AbasNavegacao";
import InputCheckGroup from "../../components/v2/InputCheckGroup/InputCheckGroup";
import LinkPadrao from "../../components/v2/LinkPadrao/LinkPadrao";
import { MODULOS_INFO, MODULOS_PREMIUM } from "../../contexts/ModulosContext";
import OpsLojasHistorico from "./OpsLojasHistorico";
import {
  formatarData,
  formatarQuando,
  modulosAlterados,
  modulosAtivos,
  modulosDoPlano,
  nomeDoModulo,
  rotuloDoStatus,
  rotuloDoUltimoAcesso,
  situacaoDoUsuario,
} from "./opsLojasUtils";
import useOpsLojaDetalhe from "./useOpsLojaDetalhe";

const OPCOES_DE_MODULO = [...MODULOS_PREMIUM]
  .sort((a, b) =>
    nomeDoModulo(a, MODULOS_INFO).localeCompare(nomeDoModulo(b, MODULOS_INFO), "pt-BR"),
  )
  .map((codigo) => ({ value: codigo, label: nomeDoModulo(codigo, MODULOS_INFO) }));

function Campo({ rotulo, children }) {
  return (
    <div>
      <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">{rotulo}</dt>
      <dd className="m-0 mt-0.5 text-sm text-slate-900 dark:text-slate-100">{children || "—"}</dd>
    </div>
  );
}

function Cartao({ id, titulo, children }) {
  return (
    <section
      aria-labelledby={id}
      className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900"
    >
      <h2 id={id} className="mb-3 text-sm font-bold text-slate-950 dark:text-slate-100">
        {titulo}
      </h2>
      {children}
    </section>
  );
}

function AbaResumo({ loja }) {
  const plano = loja.plano || {};
  const segmentos = [plano.pet, plano.vet, plano.banho_tosa].filter(Boolean).join(" · ");
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Cartao id="loja-identificacao" titulo="Quem é a loja">
        <dl className="grid gap-3 sm:grid-cols-2">
          <Campo rotulo="Nome">{loja.nome}</Campo>
          <Campo rotulo="Situação">{rotuloDoStatus(loja.status)}</Campo>
          <Campo rotulo="Tipo">{loja.tipo}</Campo>
          <Campo rotulo="Cadastrada em">{formatarData(loja.criada_em)}</Campo>
          <Campo rotulo="Responsável">
            {loja.responsavel
              ? `${loja.responsavel.nome || "Sem nome"} · ${loja.responsavel.email || "sem e-mail"}`
              : "Nenhum usuário cadastrado"}
          </Campo>
          <Campo rotulo="Código da loja">
            <span className="break-all text-xs">{loja.id}</span>
          </Campo>
        </dl>
      </Cartao>

      <Cartao id="loja-plano" titulo="Plano e cobrança">
        <dl className="grid gap-3 sm:grid-cols-2">
          <Campo rotulo="Plano">{plano.geral}</Campo>
          <Campo rotulo="Planos por área">{segmentos}</Campo>
          <Campo rotulo="Situação da cobrança">{plano.situacao_da_cobranca}</Campo>
          <Campo rotulo="Origem da assinatura">{plano.origem_da_assinatura}</Campo>
        </dl>
        <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
          Para propostas, links de contratação e comprovantes, use{" "}
          <LinkPadrao to="/ops/tenants" tamanho="text-xs">
            Cobrança e implantação
          </LinkPadrao>
          .
        </p>
      </Cartao>

      <Cartao id="loja-grupo" titulo="Agrupamento">
        {loja.grupo ? (
          <>
            <p className="m-0 text-sm font-semibold text-slate-900 dark:text-slate-100">
              {loja.grupo.nome}
            </p>
            <ul className="mt-2 space-y-1 text-sm">
              {loja.lojas_do_grupo.map((outra) => (
                <li key={outra.id}>
                  {outra.atual ? (
                    <span>
                      {outra.nome} <span className="text-slate-500">(esta loja)</span>
                    </span>
                  ) : (
                    <LinkPadrao to={`/ops/lojas/${outra.id}`}>{outra.nome}</LinkPadrao>
                  )}
                  {outra.papel ? (
                    <span className="text-xs text-slate-500 dark:text-slate-400">
                      {" "}
                      · {outra.papel}
                    </span>
                  ) : null}
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className="m-0 text-sm text-slate-600 dark:text-slate-300">
            Esta loja não está em nenhum agrupamento.
          </p>
        )}
      </Cartao>

      <Cartao id="loja-uso" titulo="Uso">
        <dl className="grid gap-3 sm:grid-cols-2">
          <Campo rotulo="Usuários ativos">
            {loja.usuarios_resumo.ativos} de {loja.usuarios_resumo.total}
          </Campo>
          <Campo rotulo="Módulos ativos">{modulosAtivos(loja).length}</Campo>
          <Campo rotulo="Registros no sistema">
            {loja.uso?.records_total?.toLocaleString("pt-BR")}
          </Campo>
          <Campo rotulo="Imagens">
            {loja.uso?.image_count != null
              ? `${loja.uso.image_count.toLocaleString("pt-BR")} (${loja.uso.image_mb} MB)`
              : null}
          </Campo>
        </dl>
      </Cartao>
    </div>
  );
}

function AbaModulos({ loja, onAlternar, salvando }) {
  const ativos = modulosAtivos(loja);
  const doPlano = modulosDoPlano(loja);
  return (
    <div className="space-y-3">
      {loja.acesso_bloqueado_por_cobranca ? (
        <p className="flex items-center gap-1 text-sm font-medium text-red-700 dark:text-red-300">
          <AlertTriangle className="h-4 w-4" aria-hidden="true" />
          Cobrança com problema: a loja está sem acesso aos módulos, mesmo os ativados.
        </p>
      ) : null}
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Clique em um módulo para ativar ou desativar. Cada mudança fica registrada na aba Histórico.
      </p>
      <InputCheckGroup
        name={`modulos-${loja.id}`}
        label={`Módulos ativos: ${ativos.length} de ${OPCOES_DE_MODULO.length}`}
        opcoes={OPCOES_DE_MODULO}
        value={ativos}
        disabled={salvando}
        onChange={(proximos) => {
          const mudanca = modulosAlterados(ativos, proximos);
          if (mudanca) onAlternar(mudanca.modulo, mudanca.ativar);
        }}
      />
      {doPlano.length > 0 ? (
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Vêm do plano ou do teste grátis (não se desligam aqui):{" "}
          {doPlano.map((codigo) => nomeDoModulo(codigo, MODULOS_INFO)).join(", ")}.
        </p>
      ) : null}
    </div>
  );
}

function AbaUsuarios({ loja }) {
  if (loja.usuarios.length === 0) {
    return (
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Nenhum usuário tem acesso a esta loja.
      </p>
    );
  }
  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
            <th className="p-3 font-semibold">Nome</th>
            <th className="p-3 font-semibold">Acesso</th>
            <th className="p-3 font-semibold">Perfil</th>
            <th className="p-3 font-semibold">Situação</th>
            <th className="p-3 font-semibold">E-mail confirmado</th>
            <th className="p-3 font-semibold">Último acesso</th>
          </tr>
        </thead>
        <tbody>
          {loja.usuarios.map((usuario) => (
            <tr
              key={usuario.id}
              className="border-b border-slate-100 align-top last:border-0 dark:border-slate-800"
            >
              <td className="p-3 font-medium">{usuario.nome || "Sem nome"}</td>
              <td className="p-3">
                {usuario.email || usuario.usuario || usuario.telefone_de_login || "—"}
              </td>
              <td className="p-3">{usuario.perfil || "Sem perfil"}</td>
              <td className="p-3">{situacaoDoUsuario(usuario)}</td>
              <td className="p-3">{usuario.email_verificado ? "Sim" : "Não"}</td>
              <td className="whitespace-nowrap p-3" title={formatarQuando(usuario.ultimo_acesso)}>
                {rotuloDoUltimoAcesso(usuario.ultimo_acesso)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function OpsLojaDetalhePage() {
  const { lojaId } = useParams();
  const { alternarModulo, carregando, erro, loja, salvando } = useOpsLojaDetalhe(lojaId);
  const [aba, setAba] = useState("resumo");

  if (carregando) {
    return (
      <div
        className="mx-auto w-full max-w-6xl p-4 sm:p-6"
        role="status"
        aria-label="Carregando a loja"
      >
        <div className="h-40 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-900" />
      </div>
    );
  }
  if (erro || !loja) {
    return (
      <div className="mx-auto w-full max-w-6xl space-y-3 p-4 sm:p-6">
        <LinkPadrao to="/ops/lojas">← Voltar para as lojas</LinkPadrao>
        <p role="alert" className="text-sm font-medium text-red-700 dark:text-red-300">
          {erro || "Loja não encontrada."}
        </p>
      </div>
    );
  }

  const abas = [
    { id: "resumo", label: "Resumo", icon: LayoutList },
    { id: "modulos", label: "Módulos", icon: Package, contador: modulosAtivos(loja).length },
    { id: "usuarios", label: "Usuários", icon: Users, contador: loja.usuarios_resumo.total },
    { id: "historico", label: "Histórico", icon: History },
  ];

  return (
    <div className="mx-auto w-full max-w-6xl space-y-4 p-4 sm:p-6">
      <header>
        <LinkPadrao to="/ops/lojas">← Voltar para as lojas</LinkPadrao>
        <h1 className="mt-2 text-2xl font-bold text-slate-950 dark:text-slate-100 sm:text-3xl">
          {loja.nome}
        </h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          {rotuloDoStatus(loja.status)}
          {loja.grupo ? ` · Agrupamento: ${loja.grupo.nome}` : " · Sem agrupamento"}
          {` · ${loja.usuarios_resumo.ativos} usuário(s) ativo(s)`}
        </p>
      </header>

      <AbasNavegacao abas={abas} ativa={aba} onChange={setAba} ariaLabel="Seções da loja" />

      <div role="tabpanel">
        {aba === "resumo" ? <AbaResumo loja={loja} /> : null}
        {aba === "modulos" ? (
          <AbaModulos loja={loja} onAlternar={alternarModulo} salvando={salvando} />
        ) : null}
        {aba === "usuarios" ? <AbaUsuarios loja={loja} /> : null}
        {aba === "historico" ? <OpsLojasHistorico lojaId={loja.id} /> : null}
      </div>
    </div>
  );
}
