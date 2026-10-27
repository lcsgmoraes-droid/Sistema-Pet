import { AlertTriangle, CheckCircle2, Circle, Copy } from "lucide-react";
import { useState } from "react";
import toast from "react-hot-toast";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import BotaoSalva from "../../components/v2/BotaoSalva/BotaoSalva";
import InputCheckbox from "../../components/v2/InputCheckbox/InputCheckbox";
import InputSenha from "../../components/v2/InputSenha/InputSenha";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import LinkPadrao from "../../components/v2/LinkPadrao/LinkPadrao";
import {
  LINKS_META,
  PASSOS_DO_WEBHOOK,
  PASSOS_NA_META,
  PASSOS_NO_SISTEMA,
  ROTULO_DA_QUALIDADE,
  passoDoErro,
  passosConcluidos,
  resumoDoVinculo,
} from "./guiaMeta";
import useConexaoMeta from "./useConexaoMeta";

const TOM_DO_RESUMO = {
  ok: "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-100",
  atencao:
    "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-100",
  erro: "border-red-300 bg-red-50 text-red-900 dark:border-red-700 dark:bg-red-950/40 dark:text-red-100",
  neutro:
    "border-slate-300 bg-slate-50 text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100",
};

function Cartao({ id, numero, titulo, resumo, concluido, destaque, children }) {
  const Icone = concluido ? CheckCircle2 : Circle;
  return (
    <section
      id={`passo-${id}`}
      aria-labelledby={`passo-${id}-titulo`}
      className={[
        "scroll-mt-4 rounded-2xl border bg-white p-4 shadow-sm dark:bg-slate-900 sm:p-5",
        destaque
          ? "border-amber-400 ring-2 ring-amber-200 dark:border-amber-500 dark:ring-amber-900"
          : "border-slate-200 dark:border-slate-700",
      ].join(" ")}
    >
      <h2
        id={`passo-${id}-titulo`}
        className="flex items-center gap-2 text-base font-bold text-slate-950 dark:text-slate-100"
      >
        <Icone
          className={["h-5 w-5 flex-none", concluido ? "text-emerald-600" : "text-slate-400"].join(
            " ",
          )}
          aria-hidden="true"
        />
        <span>
          {numero}. {titulo}
        </span>
        <span className="sr-only">{concluido ? " (feito)" : " (pendente)"}</span>
      </h2>
      {resumo ? <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{resumo}</p> : null}
      <div className="mt-3 space-y-3">{children}</div>
    </section>
  );
}

function CampoCopiavel({ id, label, valor }) {
  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(valor);
      toast.success("Copiado.");
    } catch {
      toast.error("Não foi possível copiar. Selecione o texto e copie manualmente.");
    }
  };
  return (
    <div className="flex items-end gap-2">
      <div className="min-w-0 flex-1">
        <InputTexto id={id} label={label} value={valor || ""} readOnly onChange={() => {}} />
      </div>
      <BotaoInteracao icon={Copy} onClick={copiar} disabled={!valor}>
        Copiar
      </BotaoInteracao>
    </div>
  );
}

function PassoNaMeta({ passo, numero, feito, onAlternar, destaque }) {
  return (
    <Cartao
      id={passo.id}
      numero={numero}
      titulo={passo.titulo}
      resumo={passo.resumo}
      concluido={feito}
      destaque={destaque}
    >
      <ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-800 dark:text-slate-200">
        {passo.itens.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      {passo.links.length > 0 ? (
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          {passo.links.map((link) => (
            <LinkPadrao key={link.href} href={LINKS_META[link.href]} novaJanela>
              {link.rotulo}
            </LinkPadrao>
          ))}
        </div>
      ) : null}
      <label className="flex items-center text-sm text-slate-700 dark:text-slate-300">
        <InputCheckbox
          rotulo={`Já fiz o passo: ${passo.titulo}`}
          checked={feito}
          onChange={() => onAlternar(passo.id)}
        />
        Já fiz este passo
      </label>
    </Cartao>
  );
}

function FormularioDeCredenciais({ estado, onSalvar, salvando }) {
  const atuais = estado?.credenciais || {};
  const [waba, setWaba] = useState(atuais.waba_id || "");
  const [numeroId, setNumeroId] = useState(atuais.phone_number_id || "");
  const [token, setToken] = useState("");
  const [segredo, setSegredo] = useState("");
  const [tentou, setTentou] = useState(false);

  const erros = {
    waba: waba.replace(/\D/g, "").length >= 5 ? "" : "Cole o ID da conta do WhatsApp Business.",
    numero: numeroId.replace(/\D/g, "").length >= 5 ? "" : "Cole o ID do número de telefone.",
    token: token.trim() || atuais.tem_token ? "" : "Cole o token permanente.",
    segredo: segredo.trim() || atuais.tem_app_secret ? "" : "Cole a chave secreta do app.",
  };
  const valido = !Object.values(erros).some(Boolean);

  const enviar = async (evento) => {
    evento.preventDefault();
    setTentou(true);
    if (!valido) return;
    const ok = await onSalvar({
      waba_id: waba,
      phone_number_id: numeroId,
      access_token: token || null,
      app_secret: segredo || null,
    });
    if (ok) {
      setToken("");
      setSegredo("");
      setTentou(false);
    }
  };

  return (
    <form noValidate onSubmit={enviar} className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <InputTexto
          id="meta-waba"
          label="ID da conta do WhatsApp Business"
          value={waba}
          inputMode="numeric"
          onChange={setWaba}
          error={tentou ? erros.waba : ""}
          required
        />
        <InputTexto
          id="meta-numero"
          label="ID do número de telefone"
          value={numeroId}
          inputMode="numeric"
          onChange={setNumeroId}
          error={tentou ? erros.numero : ""}
          required
        />
        <InputSenha
          id="meta-token"
          label="Token permanente"
          value={token}
          autoComplete="off"
          placeholder={atuais.tem_token ? "Já salvo. Cole outro só para trocar." : "Cole o token"}
          onChange={setToken}
          error={tentou ? erros.token : ""}
          required
        />
        <InputSenha
          id="meta-segredo"
          label="Chave secreta do app (App Secret)"
          value={segredo}
          autoComplete="off"
          placeholder={
            atuais.tem_app_secret ? "Já salva. Cole outra só para trocar." : "Cole a chave secreta"
          }
          onChange={setSegredo}
          error={tentou ? erros.segredo : ""}
          required
        />
      </div>
      <p className="text-xs text-slate-500 dark:text-slate-400">
        O token e a chave secreta ficam guardados com criptografia e nunca voltam para esta tela.
      </p>
      <BotaoSalva type="submit" loading={salvando}>
        Salvar dados
      </BotaoSalva>
    </form>
  );
}

function ResultadoDoTeste({ resultado, onInscrever, inscrevendo }) {
  if (!resultado) return null;
  return (
    <ul className="space-y-2" aria-label="Resultado do teste">
      {resultado.passos.map((item) => (
        <li key={item.id} className="flex items-start gap-2 text-sm">
          {item.ok ? (
            <CheckCircle2
              className="mt-0.5 h-4 w-4 flex-none text-emerald-600"
              aria-hidden="true"
            />
          ) : (
            <AlertTriangle className="mt-0.5 h-4 w-4 flex-none text-amber-600" aria-hidden="true" />
          )}
          <span className="text-slate-800 dark:text-slate-200">
            <span className="sr-only">{item.ok ? "Deu certo: " : "Atenção: "}</span>
            {item.mensagem}
            {item.passo_do_guia && passoDoErro(item.passo_do_guia) ? (
              <>
                {" "}
                <a
                  className="font-semibold text-blue-600 underline dark:text-cyan-300"
                  href={`#passo-${passoDoErro(item.passo_do_guia)}`}
                >
                  Ver o passo
                </a>
              </>
            ) : null}
            {item.pode_corrigir ? (
              <>
                {" "}
                <button
                  type="button"
                  onClick={onInscrever}
                  disabled={inscrevendo}
                  className="font-semibold text-blue-600 underline disabled:opacity-60 dark:text-cyan-300"
                >
                  Inscrever o app agora
                </button>
              </>
            ) : null}
          </span>
        </li>
      ))}
    </ul>
  );
}

export default function ConectarWhatsAppPage() {
  const conexao = useConexaoMeta();
  const { estado, ocupado, resultadoDoTeste } = conexao;

  if (conexao.carregando) {
    return (
      <div className="mx-auto w-full max-w-3xl p-4 sm:p-6" role="status" aria-label="Carregando">
        <div className="h-24 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-900" />
      </div>
    );
  }

  if (!estado) {
    return (
      <div className="mx-auto w-full max-w-3xl p-4 sm:p-6">
        <p role="alert" className="text-sm font-medium text-red-700 dark:text-red-300">
          {conexao.erro || "Não foi possível abrir esta página."}
        </p>
      </div>
    );
  }

  const resumo = resumoDoVinculo(estado);
  const feitos = passosConcluidos(estado);
  const erroNoTeste = resultadoDoTeste?.passos?.find((item) => item.passo_do_guia);
  const passoComProblema = erroNoTeste ? passoDoErro(erroNoTeste.passo_do_guia) : null;
  const status = estado.status || {};

  return (
    <div className="mx-auto w-full max-w-3xl space-y-4 p-4 sm:p-6">
      <header>
        <LinkPadrao to="/crm" tamanho="text-sm">
          ← Voltar ao CRM
        </LinkPadrao>
        <p className="m-0 mt-3 text-xs font-bold uppercase tracking-[0.18em] text-teal-700 dark:text-teal-300">
          Canal de WhatsApp
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-950 dark:text-slate-100 sm:text-3xl">
          Conectar o WhatsApp oficial
        </h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          O WhatsApp da loja passa a funcionar pela API oficial da Meta, com o seu número e a sua
          conta. Siga os passos na ordem. Você marca o que já fez e o sistema confere o resto.
        </p>
      </header>

      <div className={`rounded-2xl border p-4 ${TOM_DO_RESUMO[resumo.tom]}`} role="status">
        <p className="m-0 text-base font-bold">{resumo.texto}</p>
        <p className="m-0 mt-1 text-sm">{resumo.detalhe}</p>
        {status.numero ? (
          <p className="m-0 mt-2 text-sm">
            Número: {status.numero}
            {status.nome_verificado ? ` · ${status.nome_verificado}` : ""}
            {status.qualidade
              ? ` · Qualidade: ${ROTULO_DA_QUALIDADE[status.qualidade] || status.qualidade}`
              : ""}
          </p>
        ) : null}
        {status.codigo === "erro" && status.detalhe ? (
          <p className="m-0 mt-2 text-sm font-medium">{status.detalhe}</p>
        ) : null}
      </div>

      <aside className="rounded-2xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-950 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-100">
        <p className="m-0 font-semibold">Como funciona hoje</p>
        <p className="m-0 mt-1">
          Por enquanto a conexão é assistida: você cria a conta e o app na Meta e cola os dados
          aqui. Em breve vamos oferecer a conexão com poucos cliques, sem criar app. A Meta cobra as
          mensagens pagas direto do cartão da conta da loja; veja os valores na{" "}
          <LinkPadrao href={LINKS_META.precos} novaJanela tamanho="text-sm">
            tabela de preços da Meta
          </LinkPadrao>
          . Quer ver o passo a passo oficial?{" "}
          <LinkPadrao href={LINKS_META.documentacao} novaJanela tamanho="text-sm">
            Documentação da Meta
          </LinkPadrao>
          .
        </p>
      </aside>

      {PASSOS_NA_META.map((passo, indice) => (
        <PassoNaMeta
          key={passo.id}
          passo={passo}
          numero={indice + 1}
          feito={conexao.passosFeitos.includes(passo.id)}
          onAlternar={conexao.alternarPasso}
          destaque={passoComProblema === passo.id}
        />
      ))}

      <Cartao
        id="credenciais"
        numero={PASSOS_NO_SISTEMA[0].numero}
        titulo={PASSOS_NO_SISTEMA[0].titulo}
        resumo="Copie da Meta e cole nos campos. Pode voltar aqui e trocar quando precisar."
        concluido={feitos.credenciais}
      >
        <FormularioDeCredenciais
          key={`${estado.credenciais.waba_id}-${estado.credenciais.phone_number_id}`}
          estado={estado}
          onSalvar={conexao.salvarCredenciais}
          salvando={ocupado === "salvar"}
        />
      </Cartao>

      <Cartao
        id="webhook"
        numero={PASSOS_NO_SISTEMA[1].numero}
        titulo={PASSOS_NO_SISTEMA[1].titulo}
        resumo="É assim que as respostas dos tutores chegam até o CorePet."
        concluido={feitos.webhook}
      >
        <CampoCopiavel
          id="meta-webhook-url"
          label="Endereço de retorno (Callback URL)"
          valor={estado.webhook_url}
        />
        <CampoCopiavel
          id="meta-verify-token"
          label="Token de verificação"
          valor={estado.verify_token}
        />
        <ol className="list-decimal space-y-1.5 pl-5 text-sm text-slate-800 dark:text-slate-200">
          {PASSOS_DO_WEBHOOK.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ol>
        <BotaoInteracao
          onClick={conexao.inscreverApp}
          loading={ocupado === "inscrever"}
          disabled={!feitos.credenciais}
        >
          Inscrever o app na conta
        </BotaoInteracao>
      </Cartao>

      <Cartao
        id="testar"
        numero={PASSOS_NO_SISTEMA[2].numero}
        titulo={PASSOS_NO_SISTEMA[2].titulo}
        resumo="O sistema confere o token, o número, a conta e se o webhook já recebeu algo."
        concluido={feitos.testar}
      >
        <BotaoInteracao
          onClick={conexao.testar}
          loading={ocupado === "testar"}
          disabled={!feitos.credenciais}
        >
          Testar conexão
        </BotaoInteracao>
        {!feitos.credenciais ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Salve os dados no passo 6 para liberar o teste.
          </p>
        ) : null}
        <ResultadoDoTeste
          resultado={resultadoDoTeste}
          onInscrever={conexao.inscreverApp}
          inscrevendo={ocupado === "inscrever"}
        />
      </Cartao>

      <Cartao
        id="ativar"
        numero={PASSOS_NO_SISTEMA[3].numero}
        titulo={PASSOS_NO_SISTEMA[3].titulo}
        resumo="Só depois de um teste bem-sucedido. Antes disso, nada muda no seu atendimento atual."
        concluido={feitos.ativar}
      >
        <BotaoSalva
          type="button"
          onClick={conexao.ativar}
          loading={ocupado === "ativar"}
          disabled={!feitos.testar || feitos.ativar}
        >
          {feitos.ativar ? "WhatsApp oficial ativo" : "Ativar WhatsApp oficial"}
        </BotaoSalva>
      </Cartao>

      <section
        aria-labelledby="meta-problemas"
        className="rounded-2xl border border-slate-200 p-4 dark:border-slate-700"
      >
        <h2 id="meta-problemas" className="text-base font-bold text-slate-950 dark:text-slate-100">
          Deu algum erro?
        </h2>
        <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm text-slate-800 dark:text-slate-200">
          <li>
            <strong>Token inválido ou sem permissão:</strong> gere o token de novo no passo 5,
            confira se o usuário do sistema recebeu o app e a conta do WhatsApp e se as duas
            permissões estão marcadas.
          </li>
          <li>
            <strong>ID não encontrado:</strong> copie de novo os IDs na Configuração da API (passo
            4). O ID do número e o ID da conta são diferentes.
          </li>
          <li>
            <strong>O webhook não verifica:</strong> confira se copiou o endereço e o token sem
            espaços e se o servidor do CorePet está acessível pela internet.
          </li>
          <li>
            <strong>Nenhum evento chega:</strong> assine o campo messages no webhook e use
            “Inscrever o app na conta”.
          </li>
        </ul>
      </section>
    </div>
  );
}
