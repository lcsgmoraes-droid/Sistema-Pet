import { useEffect, useRef, useState } from "react";
import { Pencil, Plus, X } from "lucide-react";
import toast from "react-hot-toast";
import api from "../../api";
import { getLotes } from "../../api/produtos";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import BotaoSalva from "../v2/BotaoSalva/BotaoSalva";
import InputData from "../v2/InputData/InputData";
import InputTexto from "../v2/InputTexto/InputTexto";
import {
  formatarQuantidadeMovimentacao,
  extrairMensagemErroApiMovimentacao,
} from "./movimentacoesProdutoUtils";

const FORM_INICIAL = {
  lote_id: null,
  nome_lote: "",
  quantidade: "",
  data_validade: "",
  data_fabricacao: "",
};
const TOLERANCIA = 1e-6;
const formatarData = (valor) =>
  valor ? valor.split("T")[0].split("-").reverse().join("/") : "Sem validade";
const saldoLote = (lote) => Math.max(0, Number(lote?.quantidade_disponivel || 0));

export default function LotesValidadeModal({ produto, estoqueAtual, onClose, onSaved }) {
  const [lotes, setLotes] = useState([]);
  const [form, setForm] = useState(FORM_INICIAL);
  const [modo, setModo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [erroCarga, setErroCarga] = useState("");
  const [erroSalvar, setErroSalvar] = useState("");
  const [tentouSalvar, setTentouSalvar] = useState(false);
  const [avisoAtualizacao, setAvisoAtualizacao] = useState("");
  const numeroRef = useRef(null);

  useEffect(() => {
    let ativo = true;
    setLoading(true);
    setErroCarga("");
    setModo(null);
    setForm(FORM_INICIAL);
    setErroSalvar("");
    setTentouSalvar(false);
    setAvisoAtualizacao("");
    getLotes(produto.id)
      .then(({ data }) => {
        if (!ativo) return;
        setLotes(data || []);
        setModo(data?.length ? null : "novo");
      })
      .catch((error) => {
        if (ativo)
          setErroCarga(
            extrairMensagemErroApiMovimentacao(error, "Não foi possível carregar os lotes."),
          );
      })
      .finally(() => {
        if (ativo) setLoading(false);
      });
    return () => {
      ativo = false;
    };
  }, [produto.id]);

  useEffect(() => {
    if (modo) numeroRef.current?.focus();
  }, [modo, form.lote_id]);

  const limparFormulario = (novoModo = null) => {
    setForm(FORM_INICIAL);
    setModo(novoModo);
    setTentouSalvar(false);
    setErroSalvar("");
  };
  const editarLote = (lote) => {
    setForm({
      lote_id: lote.id,
      nome_lote: lote.nome_lote,
      quantidade: String(lote.quantidade_disponivel).replace(".", ","),
      data_validade: lote.data_validade?.split("T")[0] || "",
      data_fabricacao: lote.data_fabricacao?.split("T")[0] || "",
    });
    setModo("corrigir");
    setTentouSalvar(false);
    setErroSalvar("");
  };
  const alterar = (campo, valor) => {
    setForm((atual) => ({ ...atual, [campo]: valor }));
    setErroSalvar("");
  };

  const corrigindo = modo === "corrigir";
  const loteOriginal = lotes.find((lote) => lote.id === form.lote_id);
  const quantidadeIdentificada = lotes.reduce((total, lote) => total + saldoLote(lote), 0);
  const estoqueExibido = Number(estoqueAtual || 0);
  const estoque = Math.max(0, estoqueExibido);
  const semLote = Math.max(0, estoque - quantidadeIdentificada);
  const quantidadeOutros = quantidadeIdentificada - saldoLote(loteOriginal);
  const quantidadeTexto = form.quantidade.trim();
  const normalizada = quantidadeTexto.includes(",")
    ? quantidadeTexto.replace(/\./g, "").replace(",", ".")
    : quantidadeTexto;
  const quantidade = Number(normalizada);
  const quantidadeValida = /^\d+(?:\.\d+)?$/.test(normalizada) && Number.isFinite(quantidade);
  const totalApos = quantidadeOutros + quantidade;
  const loteMesmoNome = lotes.find(
    (lote) => lote.nome_lote === form.nome_lote.trim() && lote.id !== form.lote_id,
  );
  const erros = {};
  if (!form.nome_lote.trim()) erros.nome_lote = "Informe o número do lote.";
  else if (loteMesmoNome)
    erros.nome_lote = "Este número já está cadastrado. Use Corrigir lote na linha correspondente.";
  if (!quantidadeValida || (!corrigindo && quantidade <= 0))
    erros.quantidade = corrigindo
      ? "Informe uma quantidade válida, igual ou maior que zero."
      : "Informe uma quantidade maior que zero.";
  else if (quantidade < Number(loteOriginal?.quantidade_reservada || 0))
    erros.quantidade = "A quantidade não pode ser menor que a reserva deste lote.";
  // Mesma proteção da API: permite manter ou reduzir uma divergência antiga.
  else if (totalApos > estoque + TOLERANCIA && totalApos > quantidadeIdentificada + TOLERANCIA)
    erros.quantidade = corrigindo
      ? `Os outros lotes têm ${formatarQuantidadeMovimentacao(quantidadeOutros)}. Com esta quantidade, o total seria ${formatarQuantidadeMovimentacao(totalApos)}, acima do estoque de ${formatarQuantidadeMovimentacao(estoque)}.`
      : `Este seria um lote adicional: ${formatarQuantidadeMovimentacao(quantidadeIdentificada)} já identificados + ${formatarQuantidadeMovimentacao(quantidade)} = ${formatarQuantidadeMovimentacao(totalApos)}. Restam ${formatarQuantidadeMovimentacao(semLote)} para outro lote. Para alterar um existente, use Corrigir lote.`;
  if (!form.data_validade) erros.data_validade = "Informe uma validade completa e válida.";
  if (form.data_fabricacao && form.data_validade && form.data_fabricacao > form.data_validade)
    erros.data_fabricacao = "A fabricação não pode ser posterior à validade.";

  const salvar = async (event) => {
    event.preventDefault();
    if (salvando) return;
    setTentouSalvar(true);
    // InputData emite ISO vazio tanto ao limpar quanto ao digitar uma data inválida.
    const fabricacaoDigitada = String(
      new FormData(event.currentTarget).get("lote-fabricacao") || "",
    ).trim();
    if (fabricacaoDigitada && !form.data_fabricacao) {
      setErroSalvar("Informe uma data de fabricação completa e válida ou limpe o campo.");
      return;
    }
    if (Object.keys(erros).length) return;
    setSalvando(true);
    setErroSalvar("");
    setAvisoAtualizacao("");
    let salvo;
    try {
      const { data } = await api.put(`/produtos/${produto.id}/lotes-validade`, {
        ...form,
        nome_lote: form.nome_lote.trim(),
        quantidade,
        data_fabricacao: form.data_fabricacao || null,
      });
      salvo = data;
    } catch (error) {
      setErroSalvar(
        extrairMensagemErroApiMovimentacao(error, "Não foi possível salvar o lote e a validade."),
      );
      setSalvando(false);
      return;
    }
    setLotes((atuais) => [...atuais.filter((lote) => lote.id !== salvo.id), salvo]);
    limparFormulario();
    toast.success(
      corrigindo
        ? "Correção salva. O estoque foi mantido."
        : "Lote cadastrado no estoque existente.",
    );
    try {
      const { data } = await getLotes(produto.id);
      setLotes(data || []);
      await onSaved();
    } catch (_error) {
      setAvisoAtualizacao(
        "O lote foi salvo, mas não foi possível atualizar todos os dados da tela. Feche e abra novamente para conferir.",
      );
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-lotes-validade"
        className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white shadow-xl dark:bg-slate-900"
      >
        <div className="flex items-start justify-between gap-3 border-b border-slate-200 p-5 dark:border-slate-700">
          <div>
            <h2
              id="titulo-lotes-validade"
              className="text-xl font-bold text-slate-900 dark:text-slate-100"
            >
              Lotes e validade
            </h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{produto.nome}</p>
          </div>
          <BotaoInteracao
            icon={X}
            onClick={onClose}
            disabled={salvando}
            aria-label="Fechar lotes e validade"
          />
        </div>
        <div className="space-y-5 p-5">
          {loading ? (
            <p role="status" className="text-sm text-slate-500 dark:text-slate-400">
              Carregando lotes...
            </p>
          ) : erroCarga ? (
            <p role="alert" className="text-sm text-red-700 dark:text-red-400">
              {erroCarga}
            </p>
          ) : (
            <>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                Identifique os lotes das unidades que já estão no estoque. Para registrar entrada ou
                saída de produtos, use “Incluir lançamento”.
              </p>
              <dl className="grid gap-3 sm:grid-cols-3">
                {[
                  ["Estoque atual", estoqueExibido],
                  ["Já identificado em lotes", quantidadeIdentificada],
                  ["Disponível para outro lote", semLote],
                ].map(([rotulo, valor]) => (
                  <div
                    key={rotulo}
                    className="rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800"
                  >
                    <dt className="text-xs text-slate-600 dark:text-slate-400">{rotulo}</dt>
                    <dd className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">
                      {formatarQuantidadeMovimentacao(valor)}{" "}
                      <span className="text-xs">{produto.unidade || "UN"}</span>
                    </dd>
                  </div>
                ))}
              </dl>
              {avisoAtualizacao && (
                <p role="alert" className="text-sm text-amber-800 dark:text-amber-300">
                  {avisoAtualizacao}
                </p>
              )}
              <section aria-labelledby="lotes-cadastrados" className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h3
                    id="lotes-cadastrados"
                    className="font-semibold text-slate-900 dark:text-slate-100"
                  >
                    Lotes já cadastrados
                  </h3>
                  <BotaoInteracao
                    icon={Plus}
                    disabled={salvando || modo === "novo"}
                    onClick={() => limparFormulario("novo")}
                  >
                    Cadastrar outro lote
                  </BotaoInteracao>
                </div>
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  Para trocar o número ou preencher a validade de um lote desta lista, escolha
                  “Corrigir lote”.
                </p>
                {lotes.length > 0 && semLote <= TOLERANCIA && (
                  <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
                    <p className="font-semibold">Todo o estoque já está identificado em lotes.</p>
                    <p className="mt-1">
                      Se está informando o número real e a validade de um lote da nota fiscal,
                      clique em “Corrigir lote” na linha dele.
                    </p>
                  </div>
                )}
                <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
                  <table className="w-full text-sm text-slate-700 dark:text-slate-300">
                    <thead className="bg-slate-50 text-left dark:bg-slate-800">
                      <tr>
                        <th className="p-3">Lote</th>
                        <th className="p-3">Quantidade atual</th>
                        <th className="p-3">Validade</th>
                        <th className="p-3">Ações</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lotes.length === 0 ? (
                        <tr>
                          <td
                            colSpan={4}
                            className="p-4 text-center text-slate-500 dark:text-slate-400"
                          >
                            Nenhum lote identificado. Cadastre o primeiro abaixo.
                          </td>
                        </tr>
                      ) : (
                        lotes.map((lote) => (
                          <tr
                            key={lote.id}
                            className={`border-t border-slate-200 dark:border-slate-700 ${lote.id === form.lote_id ? "bg-blue-50 dark:bg-blue-950/40" : ""}`}
                          >
                            <td className="p-3">
                              <span className="font-medium">{lote.nome_lote}</span>
                              {lote.id === form.lote_id && (
                                <span className="ml-2 text-xs font-semibold text-blue-700 dark:text-blue-300">
                                  Em edição
                                </span>
                              )}
                              <span className="block text-xs text-slate-500 dark:text-slate-400">
                                {lote.apenas_identificacao
                                  ? "Identificação do estoque"
                                  : "Entrada de estoque"}{" "}
                                · {lote.status}
                              </span>
                            </td>
                            <td className="p-3">
                              {formatarQuantidadeMovimentacao(lote.quantidade_disponivel)}
                            </td>
                            <td className="p-3">{formatarData(lote.data_validade)}</td>
                            <td className="p-3">
                              <BotaoInteracao
                                icon={Pencil}
                                tamanho="pequeno"
                                disabled={salvando || lote.id === form.lote_id}
                                onClick={() => editarLote(lote)}
                              >
                                Corrigir lote
                              </BotaoInteracao>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </section>
              {modo && (
                <form
                  key={form.lote_id ?? "novo"}
                  onSubmit={salvar}
                  noValidate
                  className="space-y-4 rounded-xl border border-blue-200 p-4 dark:border-blue-900"
                >
                  <div
                    className="rounded-lg bg-blue-50 p-3 text-sm text-blue-900 dark:bg-blue-950/40 dark:text-blue-200"
                    aria-live="polite"
                  >
                    <h3 className="font-semibold">
                      {corrigindo ? "Corrigir lote existente" : "Cadastrar outro lote"}
                    </h3>
                    <p className="mt-1">
                      {corrigindo ? (
                        <>
                          Você está corrigindo o lote <strong>{loteOriginal?.nome_lote}</strong>,
                          com {formatarQuantidadeMovimentacao(saldoLote(loteOriginal))}{" "}
                          {produto.unidade || "UN"}. Alterar o número ou a validade atualiza esse
                          mesmo lote.
                        </>
                      ) : (
                        <>
                          Este cadastro cria um lote separado dos que já aparecem na lista. Há{" "}
                          <strong>
                            {formatarQuantidadeMovimentacao(semLote)} {produto.unidade || "UN"}
                          </strong>{" "}
                          do estoque disponíveis para ele.
                        </>
                      )}
                    </p>
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <InputTexto
                      ref={numeroRef}
                      id="lote-numero"
                      label="Número do lote"
                      required
                      maxLength={50}
                      disabled={salvando}
                      value={form.nome_lote}
                      onChange={(valor) => alterar("nome_lote", valor)}
                      error={tentouSalvar || form.nome_lote ? erros.nome_lote : ""}
                    />
                    <InputTexto
                      id="lote-quantidade"
                      label="Quantidade atual deste lote"
                      required
                      inputMode="decimal"
                      disabled={salvando}
                      value={form.quantidade}
                      onChange={(valor) => alterar("quantidade", valor)}
                      error={tentouSalvar || form.quantidade ? erros.quantidade : ""}
                      help={
                        corrigindo
                          ? "Substitui a quantidade deste lote. Zero retira a identificação."
                          : "Use somente unidades que ainda não estão identificadas em outro lote."
                      }
                    />
                    <InputData
                      id="lote-validade"
                      label="Validade"
                      required
                      disabled={salvando}
                      value={form.data_validade}
                      onChange={(valor) => alterar("data_validade", valor)}
                      error={tentouSalvar ? erros.data_validade : ""}
                    />
                    <InputData
                      id="lote-fabricacao"
                      label="Fabricação"
                      disabled={salvando}
                      value={form.data_fabricacao}
                      onChange={(valor) => alterar("data_fabricacao", valor)}
                      error={erros.data_fabricacao}
                    />
                  </div>
                  {loteMesmoNome && (
                    <BotaoInteracao
                      icon={Pencil}
                      disabled={salvando}
                      onClick={() => editarLote(loteMesmoNome)}
                    >
                      Corrigir este lote
                    </BotaoInteracao>
                  )}
                  {quantidadeValida && !erros.quantidade && (
                    <p className="text-sm text-slate-600 dark:text-slate-300" aria-live="polite">
                      Total identificado após salvar:{" "}
                      <strong>
                        {formatarQuantidadeMovimentacao(totalApos)} {produto.unidade || "UN"}
                      </strong>{" "}
                      (antes: {formatarQuantidadeMovimentacao(quantidadeIdentificada)}). O estoque
                      permanece em {formatarQuantidadeMovimentacao(estoqueExibido)}{" "}
                      {produto.unidade || "UN"}.
                    </p>
                  )}
                  {erroSalvar && (
                    <p role="alert" className="text-sm text-red-700 dark:text-red-400">
                      {erroSalvar}
                    </p>
                  )}
                  <div className="flex flex-wrap justify-end gap-3">
                    <BotaoCancelar disabled={salvando} onClick={() => limparFormulario()}>
                      Cancelar
                    </BotaoCancelar>
                    <BotaoSalva
                      loading={salvando}
                      disabled={
                        Boolean(erros.nome_lote && form.nome_lote) ||
                        Boolean(erros.quantidade && form.quantidade)
                      }
                    >
                      {salvando ? "Salvando..." : corrigindo ? "Salvar correção" : "Cadastrar lote"}
                    </BotaoSalva>
                  </div>
                </form>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
