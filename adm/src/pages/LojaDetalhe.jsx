import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { obter, enviar } from "../api/cliente";
import { Aviso, Carregando, Confirmacao, Etiqueta, Interruptor, VazioComTexto } from "../components/ui";
import {
  descreverAlteracao,
  formatarQuando,
  formatarReaisDeCentavos,
  nomeDoModulo,
  origensEmTexto,
  podeDesligar,
  rotuloDoStatus,
  rotuloDoUltimoAcesso,
  situacaoDoUsuario,
} from "../lib/formatadores";

const ABAS = [
  { id: "modulos", rotulo: "Módulos" },
  { id: "cobranca", rotulo: "Plano e cobrança" },
  { id: "usuarios", rotulo: "Usuários" },
  { id: "historico", rotulo: "Histórico" },
];

export default function LojaDetalhe() {
  const { id } = useParams();
  const [loja, setLoja] = useState(null);
  const [catalogo, setCatalogo] = useState([]);
  const [modulosDaLoja, setModulosDaLoja] = useState([]);
  const [historico, setHistorico] = useState([]);
  const [erro, setErro] = useState("");
  const [aba, setAba] = useState("modulos");
  const [alterando, setAlterando] = useState("");
  const [pendente, setPendente] = useState(null);
  const [aviso, setAviso] = useState("");

  const carregarHistorico = useCallback(async () => {
    const resposta = await obter(`/admin/lojas/${id}/historico`);
    setHistorico(resposta.items || []);
  }, [id]);

  useEffect(() => {
    let ativo = true;
    (async () => {
      setLoja(null);
      setErro("");
      try {
        const [detalhe, lista, hist] = await Promise.all([
          obter(`/admin/lojas/${id}`),
          obter("/admin/lojas"),
          obter(`/admin/lojas/${id}/historico`),
        ]);
        if (!ativo) return;
        setCatalogo(lista.catalogo_de_modulos || []);
        setModulosDaLoja(lista.items.find((item) => item.id === id)?.modulos || []);
        setHistorico(hist.items || []);
        setLoja(detalhe);
      } catch (falha) {
        if (ativo) setErro(falha.message);
      }
    })();
    return () => {
      ativo = false;
    };
  }, [id]);

  const alternar = async (modulo, ligar) => {
    setAlterando(modulo.codigo);
    setAviso("");
    setErro("");
    try {
      const resposta = await enviar(`/admin/lojas/${id}/modulos/${modulo.codigo}/${ligar ? "ativar" : "desativar"}`);
      setModulosDaLoja(resposta.modulos);
      const nome = nomeDoModulo(modulo.codigo, catalogo);
      setAviso(
        !ligar && resposta.continua_ativo
          ? `A ativação manual de ${nome} foi removida, mas o módulo continua ativo por outra origem (plano ou assinatura).`
          : `${nome} ${ligar ? "ativado" : "desativado"}.`,
      );
      await carregarHistorico();
    } catch (falha) {
      setErro(falha.message);
    } finally {
      setAlterando("");
      setPendente(null);
    }
  };

  if (erro && !loja) {
    return (
      <div className="space-y-4">
        <Voltar />
        <Aviso tom="erro">{erro}</Aviso>
      </div>
    );
  }
  if (!loja) {
    return (
      <div className="space-y-4">
        <Voltar />
        <Carregando rotulo="Carregando loja" />
      </div>
    );
  }

  const plano = loja.plano || {};

  return (
    <div className="space-y-5">
      <Voltar />
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="text-2xl font-bold">{loja.nome}</h1>
        <Etiqueta tom={loja.status === "active" ? "ok" : "atencao"}>{rotuloDoStatus(loja.status)}</Etiqueta>
      </div>

      <div role="tablist" aria-label="Seções da loja" className="flex flex-wrap gap-1 border-b border-slate-200 dark:border-slate-800">
        {ABAS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={aba === item.id}
            onClick={() => setAba(item.id)}
            className={[
              "min-h-[44px] border-b-2 px-4 text-sm font-semibold",
              aba === item.id
                ? "border-teal-700 text-teal-800 dark:border-teal-400 dark:text-teal-300"
                : "border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100",
            ].join(" ")}
          >
            {item.rotulo}
          </button>
        ))}
      </div>

      {erro ? <Aviso tom="erro">{erro}</Aviso> : null}
      {aviso ? <Aviso tom="ok">{aviso}</Aviso> : null}

      {aba === "modulos" ? (
        <section aria-label="Módulos">
          <p className="mb-3 text-sm text-slate-600 dark:text-slate-400">
            Ligar ou desligar aqui vale na hora, sem compra, pagamento ou mudança de valor. Cada troca fica no histórico.
          </p>
          <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-900">
            {catalogo.map((item) => {
              const modulo = modulosDaLoja.find((m) => m.codigo === item.codigo) || {
                codigo: item.codigo,
                ativo: false,
                origens: [],
              };
              const bloqueado = modulo.ativo && !podeDesligar(modulo);
              return (
                <li key={item.codigo} className="flex items-center gap-4 p-4">
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold">{item.nome}</p>
                    <p className="text-sm text-slate-600 dark:text-slate-400">{item.descricao}</p>
                    {modulo.ativo && modulo.origens.length ? (
                      <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">{origensEmTexto(modulo.origens)}</p>
                    ) : null}
                    {bloqueado ? (
                      <p className="mt-1 text-xs text-amber-800 dark:text-amber-300">
                        Incluído no plano da loja: para tirar, mude o plano.
                      </p>
                    ) : null}
                  </div>
                  <span className="w-16 text-right text-sm font-medium">{modulo.ativo ? "Ativo" : "Inativo"}</span>
                  <Interruptor
                    ligado={modulo.ativo}
                    rotulo={`${item.nome}: ${modulo.ativo ? "desligar" : "ligar"}`}
                    desabilitado={bloqueado || alterando === item.codigo}
                    aoAlternar={() => (modulo.ativo ? setPendente(modulo) : alternar(modulo, true))}
                  />
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}

      {aba === "cobranca" ? (
        <section aria-label="Plano e cobrança">
          <dl className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:grid-cols-2 dark:border-slate-800 dark:bg-slate-900">
            <Dado rotulo="Plano geral" valor={plano.geral} />
            <Dado rotulo="Plano Pet" valor={plano.pet} />
            <Dado rotulo="Plano Vet" valor={plano.vet} />
            <Dado rotulo="Plano Banho e tosa" valor={plano.banho_tosa} />
            <Dado rotulo="Situação da cobrança" valor={plano.situacao_da_cobranca} />
            <Dado rotulo="Origem da assinatura" valor={plano.origem_da_assinatura} />
            <Dado rotulo="Valor cobrado" valor={formatarReaisDeCentavos(plano.valor_cobrado_centavos)} />
            <Dado rotulo="Grupo" valor={loja.grupo?.nome} />
            <Dado rotulo="Responsável" valor={loja.responsavel?.nome || loja.responsavel?.email} />
          </dl>
          {loja.lojas_do_grupo?.length ? (
            <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">
              Outras lojas do grupo: {loja.lojas_do_grupo.map((l) => l.nome).join(", ")}
            </p>
          ) : null}
        </section>
      ) : null}

      {aba === "usuarios" ? (
        <section aria-label="Usuários">
          {loja.usuarios?.length ? (
            <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-900">
              {loja.usuarios.map((u) => (
                <li key={u.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 p-4">
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold">{u.nome || u.usuario}</p>
                    <p className="truncate text-sm text-slate-600 dark:text-slate-400">
                      {u.email || u.telefone_de_login || u.usuario} · {u.perfil || "Sem perfil"}
                    </p>
                  </div>
                  <Etiqueta tom={u.ativo ? "ok" : "atencao"}>{situacaoDoUsuario(u)}</Etiqueta>
                  <span className="text-sm text-slate-600 dark:text-slate-400">{rotuloDoUltimoAcesso(u.ultimo_acesso)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <VazioComTexto titulo="Nenhum usuário nesta loja" />
          )}
        </section>
      ) : null}

      {aba === "historico" ? (
        <section aria-label="Histórico">
          {historico.length ? (
            <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-900">
              {historico.map((item) => {
                const texto = descreverAlteracao(item, catalogo);
                return (
                  <li key={item.id} className="p-4">
                    <p className="font-semibold">{texto.titulo}</p>
                    <p className="text-sm">
                      {texto.antes} → {texto.depois}
                    </p>
                    <p className="text-xs text-slate-600 dark:text-slate-400">
                      {item.quem} · {formatarQuando(item.quando)}
                    </p>
                  </li>
                );
              })}
            </ul>
          ) : (
            <VazioComTexto titulo="Nenhuma alteração registrada" descricao="As trocas de módulos feitas aqui aparecem nesta lista." />
          )}
        </section>
      ) : null}

      {pendente ? (
        <Confirmacao
          titulo={`Desligar ${nomeDoModulo(pendente.codigo, catalogo)}?`}
          rotuloConfirmar="Desligar módulo"
          perigo
          carregando={alterando === pendente.codigo}
          aoConfirmar={() => alternar(pendente, false)}
          aoCancelar={() => setPendente(null)}
        >
          A loja {loja.nome} perde o acesso a este módulo imediatamente. Você pode ligar de novo quando quiser.
        </Confirmacao>
      ) : null}
    </div>
  );
}

function Voltar() {
  return (
    <Link to="/lojas" className="inline-flex min-h-[44px] items-center gap-2 text-sm font-medium text-teal-800 dark:text-teal-300">
      <ArrowLeft className="h-4 w-4" aria-hidden="true" />
      Voltar para as lojas
    </Link>
  );
}

function Dado({ rotulo, valor }) {
  return (
    <div>
      <dt className="text-xs text-slate-600 dark:text-slate-400">{rotulo}</dt>
      <dd className="font-medium">{valor || "—"}</dd>
    </div>
  );
}
