import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { Building2, Download, FilePlus2, Lock, Plus, RefreshCw, Trash2 } from "lucide-react";

import { baixarBlob, orcamentosGrupoApi } from "../../api/orcamentosGrupo";
import CurrencyInput from "../../components/CurrencyInput";
import { formatMoneyBRL } from "../../utils/formatters";
import {
  calcularTotalBase,
  criarItemOrcamento,
  nomeArquivoPdf,
  sortearEmpresas,
} from "./orcamentosGrupoUtils";

const inputClass =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100";

function hojeIso() {
  const hoje = new Date();
  const dataLocal = new Date(hoje.getTime() - hoje.getTimezoneOffset() * 60_000);
  return dataLocal.toISOString().slice(0, 10);
}

function mensagemErro(error, padrao) {
  const detail = error?.response?.data?.detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join("; ");
  return detail || padrao;
}

export default function OrcamentoGrupoEditor({ configuracao, empresas, onEmitido }) {
  const [titulo, setTitulo] = useState("Orçamento");
  const [destinatario, setDestinatario] = useState("");
  const [dataEmissao, setDataEmissao] = useState(hojeIso());
  const [validadeDias, setValidadeDias] = useState(configuracao.validade_dias || 15);
  const [observacoes, setObservacoes] = useState(configuracao.observacoes_padrao || "");
  const [itens, setItens] = useState([criarItemOrcamento()]);
  const [selecoes, setSelecoes] = useState([]);
  const [resultado, setResultado] = useState(null);
  const [salvando, setSalvando] = useState(false);
  const quantidadeEmpresas = Number(configuracao.quantidade_empresas || 2);
  const totalBase = useMemo(() => calcularTotalBase(itens), [itens]);

  useEffect(() => {
    setValidadeDias(configuracao.validade_dias || 15);
    setObservacoes(configuracao.observacoes_padrao || "");
  }, [configuracao]);

  useEffect(() => {
    setSelecoes((atuais) =>
      sortearEmpresas({ empresas, selecoes: atuais, quantidade: quantidadeEmpresas }),
    );
  }, [empresas, quantidadeEmpresas]);

  function atualizarItem(index, campo, valor) {
    setItens((atuais) =>
      atuais.map((item, itemIndex) => (itemIndex === index ? { ...item, [campo]: valor } : item)),
    );
  }

  function adicionarItem() {
    setItens((atuais) => [...atuais, criarItemOrcamento()]);
  }

  function removerItem(index) {
    setItens((atuais) => atuais.filter((_, itemIndex) => itemIndex !== index));
  }

  function sortearSelecoes() {
    if (empresas.length < quantidadeEmpresas) {
      toast.error(`Cadastre ao menos ${quantidadeEmpresas} empresas do grupo.`);
      return;
    }
    setSelecoes((atuais) =>
      sortearEmpresas({ empresas, selecoes: atuais, quantidade: quantidadeEmpresas }),
    );
  }

  function atualizarSelecao(index, campo, valor) {
    setSelecoes((atuais) =>
      atuais.map((selecao, selecaoIndex) =>
        selecaoIndex === index ? { ...selecao, [campo]: valor } : selecao,
      ),
    );
  }

  async function emitir(event) {
    event.preventDefault();
    if (itens.some((item) => !item.descricao.trim())) {
      toast.error("Preencha a descrição de todos os itens.");
      return;
    }
    if (selecoes.length !== quantidadeEmpresas || selecoes.some((item) => !item.empresa_id)) {
      toast.error("Selecione todas as empresas que receberão os orçamentos.");
      return;
    }
    if (new Set(selecoes.map((item) => Number(item.empresa_id))).size !== selecoes.length) {
      toast.error("Cada orçamento deve usar uma empresa diferente.");
      return;
    }

    setSalvando(true);
    try {
      const response = await orcamentosGrupoApi.criarOrcamento({
        titulo: titulo.trim(),
        destinatario: destinatario.trim() || null,
        data_emissao: dataEmissao,
        validade_dias: Number(validadeDias),
        observacoes: observacoes.trim() || null,
        itens: itens.map((item) => ({
          descricao: item.descricao.trim(),
          quantidade: Number(item.quantidade),
          unidade: item.unidade.trim() || null,
          preco_unitario_base: Number(item.preco_unitario_base),
        })),
        empresas: selecoes.map((item) => ({
          empresa_id: Number(item.empresa_id),
          fixada: Boolean(item.fixada),
        })),
      });
      setResultado(response.data);
      toast.success("Orçamentos gerados e salvos.");
      await onEmitido?.();
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível gerar os orçamentos."));
    } finally {
      setSalvando(false);
    }
  }

  async function baixarPdf(cotacaoId) {
    if (!resultado) return;
    try {
      const response = await orcamentosGrupoApi.baixarPdf(resultado.id, cotacaoId);
      baixarBlob(response.data, nomeArquivoPdf(resultado, cotacaoId));
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível baixar o PDF."));
    }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={emitir} className="space-y-6">
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <div className="flex items-center gap-2">
            <div className="rounded-lg bg-teal-50 p-2 text-teal-700 dark:bg-teal-500/10 dark:text-teal-200">
              <FilePlus2 size={18} />
            </div>
            <div>
              <h2 className="font-semibold text-slate-900 dark:text-slate-100">
                Dados do orçamento
              </h2>
              <p className="text-xs text-slate-500">A empresa principal será o tenant conectado.</p>
            </div>
          </div>
          <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <label className="text-sm text-slate-700 dark:text-slate-300">
              Título
              <input
                className={`${inputClass} mt-1`}
                value={titulo}
                onChange={(event) => setTitulo(event.target.value)}
                required
              />
            </label>
            <label className="text-sm text-slate-700 dark:text-slate-300">
              Destinatário
              <input
                className={`${inputClass} mt-1`}
                value={destinatario}
                onChange={(event) => setDestinatario(event.target.value)}
                placeholder="Nome do solicitante"
              />
            </label>
            <label className="text-sm text-slate-700 dark:text-slate-300">
              Data de emissão
              <input
                className={`${inputClass} mt-1`}
                type="date"
                value={dataEmissao}
                onChange={(event) => setDataEmissao(event.target.value)}
                required
              />
            </label>
            <label className="text-sm text-slate-700 dark:text-slate-300">
              Validade em dias
              <input
                className={`${inputClass} mt-1`}
                type="number"
                min="1"
                max="365"
                value={validadeDias}
                onChange={(event) => setValidadeDias(event.target.value)}
                required
              />
            </label>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-semibold text-slate-900 dark:text-slate-100">
                Itens e preço principal
              </h2>
              <p className="text-xs text-slate-500">
                Este é o valor do tenant. Os demais serão calculados sobre ele.
              </p>
            </div>
            <div className="rounded-lg bg-emerald-50 px-4 py-2 text-sm font-bold text-emerald-800 dark:bg-emerald-500/10 dark:text-emerald-200">
              Total: {formatMoneyBRL(totalBase)}
            </div>
          </div>

          <div className="mt-4 space-y-3">
            {itens.map((item, index) => (
              <div
                key={index}
                className="grid gap-3 rounded-xl border border-slate-200 p-3 md:grid-cols-[1fr_110px_100px_150px_42px] dark:border-slate-800"
              >
                <label className="text-xs text-slate-500">
                  Descrição
                  <input
                    className={`${inputClass} mt-1`}
                    value={item.descricao}
                    onChange={(event) => atualizarItem(index, "descricao", event.target.value)}
                    required
                  />
                </label>
                <label className="text-xs text-slate-500">
                  Quantidade
                  <input
                    className={`${inputClass} mt-1`}
                    type="number"
                    min="0.001"
                    step="0.001"
                    value={item.quantidade}
                    onChange={(event) => atualizarItem(index, "quantidade", event.target.value)}
                    required
                  />
                </label>
                <label className="text-xs text-slate-500">
                  Unidade
                  <input
                    className={`${inputClass} mt-1`}
                    value={item.unidade}
                    onChange={(event) => atualizarItem(index, "unidade", event.target.value)}
                  />
                </label>
                <label className="text-xs text-slate-500">
                  Preço unitário
                  <CurrencyInput
                    className={`${inputClass} mt-1`}
                    value={item.preco_unitario_base}
                    onChange={(value) => atualizarItem(index, "preco_unitario_base", value)}
                  />
                </label>
                <button
                  type="button"
                  onClick={() => removerItem(index)}
                  disabled={itens.length === 1}
                  className="mt-5 flex h-10 w-10 items-center justify-center rounded-lg text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-30"
                  aria-label="Remover item"
                >
                  <Trash2 size={17} />
                </button>
              </div>
            ))}
          </div>
          <button
            type="button"
            onClick={adicionarItem}
            className="mt-3 inline-flex items-center gap-2 rounded-lg border border-teal-200 px-3 py-2 text-sm font-medium text-teal-700 hover:bg-teal-50 dark:border-teal-900 dark:text-teal-200"
          >
            <Plus size={16} /> Adicionar item
          </button>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Building2 className="text-blue-600" size={19} />
              <div>
                <h2 className="font-semibold text-slate-900 dark:text-slate-100">
                  Empresas comparadas
                </h2>
                <p className="text-xs text-slate-500">
                  Fixe uma empresa para mantê-la ao sortear novamente.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={sortearSelecoes}
              className="inline-flex items-center gap-2 rounded-lg border border-blue-200 px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50 dark:border-blue-900 dark:text-blue-200"
            >
              <RefreshCw size={16} /> Sortear empresas
            </button>
          </div>

          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            {Array.from({ length: quantidadeEmpresas }, (_, index) => {
              const selecao = selecoes[index] || { empresa_id: "", fixada: false };
              const idsOutros = new Set(
                selecoes
                  .filter((_, itemIndex) => itemIndex !== index)
                  .map((item) => Number(item.empresa_id)),
              );
              return (
                <div
                  key={index}
                  className="rounded-xl border border-slate-200 p-3 dark:border-slate-800"
                >
                  <label className="text-xs font-medium text-slate-500">Empresa {index + 1}</label>
                  <select
                    className={`${inputClass} mt-1`}
                    value={selecao.empresa_id}
                    onChange={(event) =>
                      atualizarSelecao(index, "empresa_id", Number(event.target.value))
                    }
                  >
                    <option value="">Selecione</option>
                    {empresas
                      .filter(
                        (empresa) =>
                          !idsOutros.has(Number(empresa.id)) ||
                          Number(empresa.id) === Number(selecao.empresa_id),
                      )
                      .map((empresa) => (
                        <option key={empresa.id} value={empresa.id}>
                          {empresa.nome}
                        </option>
                      ))}
                  </select>
                  <label className="mt-3 flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
                    <input
                      type="checkbox"
                      checked={Boolean(selecao.fixada)}
                      onChange={(event) => atualizarSelecao(index, "fixada", event.target.checked)}
                      className="h-4 w-4 rounded border-slate-300 text-teal-600"
                    />
                    <Lock size={13} /> Manter esta empresa no próximo sorteio
                  </label>
                </div>
              );
            })}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <label className="text-sm text-slate-700 dark:text-slate-300">
            Observações que aparecerão nos documentos
            <textarea
              className={`${inputClass} mt-1 min-h-24`}
              value={observacoes}
              onChange={(event) => setObservacoes(event.target.value)}
            />
          </label>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-slate-500">
              Cada empresa receberá um percentual independente entre{" "}
              {configuracao.percentual_minimo}% e {configuracao.percentual_maximo}%.
            </p>
            <button
              type="submit"
              disabled={salvando || empresas.length < quantidadeEmpresas}
              className="inline-flex items-center gap-2 rounded-lg bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-teal-700 disabled:opacity-50"
            >
              <FilePlus2 size={17} /> {salvando ? "Gerando..." : "Gerar e salvar orçamentos"}
            </button>
          </div>
        </section>
      </form>

      {resultado ? (
        <section className="rounded-2xl border border-emerald-200 bg-emerald-50/40 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/20">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-bold text-emerald-950 dark:text-emerald-100">
                {resultado.numero}
              </h2>
              <p className="text-sm text-emerald-800 dark:text-emerald-200">
                Valores gravados. Os PDFs manterão exatamente estes preços.
              </p>
            </div>
            <button
              type="button"
              onClick={() => baixarPdf()}
              className="inline-flex items-center gap-2 rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800"
            >
              <Download size={16} /> Baixar todos os PDFs
            </button>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {resultado.cotacoes?.map((cotacao) => (
              <div
                key={cotacao.id}
                className="rounded-xl border border-emerald-200 bg-white p-4 dark:border-emerald-900 dark:bg-slate-950"
              >
                <p className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
                  {cotacao.empresa?.nome}
                </p>
                <p className="mt-1 text-lg font-bold text-emerald-700">
                  {formatMoneyBRL(cotacao.total)}
                </p>
                <button
                  type="button"
                  onClick={() => baixarPdf(cotacao.id)}
                  className="mt-3 inline-flex items-center gap-2 text-xs font-semibold text-blue-700 hover:text-blue-800 dark:text-blue-300"
                >
                  <Download size={14} /> Baixar PDF desta empresa
                </button>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
