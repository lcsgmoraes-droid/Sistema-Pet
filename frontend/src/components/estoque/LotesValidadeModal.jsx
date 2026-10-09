import { useEffect, useState } from "react";
import { X } from "lucide-react";
import toast from "react-hot-toast";
import api from "../../api";
import { getLotes } from "../../api/produtos";
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
const formatarData = (valor) =>
  valor ? valor.split("T")[0].split("-").reverse().join("/") : "Sem validade";

export default function LotesValidadeModal({ produto, estoqueAtual, onClose, onSaved }) {
  const [lotes, setLotes] = useState([]);
  const [form, setForm] = useState(FORM_INICIAL);
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [erroCarga, setErroCarga] = useState("");

  useEffect(() => {
    let ativo = true;
    getLotes(produto.id)
      .then(({ data }) => {
        if (ativo) setLotes(data || []);
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

  const editarLote = (lote) =>
    setForm({
      lote_id: lote.id,
      nome_lote: lote.nome_lote,
      quantidade: String(lote.quantidade_disponivel),
      data_validade: lote.data_validade?.split("T")[0] || "",
      data_fabricacao: lote.data_fabricacao?.split("T")[0] || "",
    });
  const alterar = (campo, valor) => setForm((atual) => ({ ...atual, [campo]: valor }));
  const quantidadeIdentificada = lotes.reduce(
    (total, lote) => total + Number(lote.quantidade_disponivel || 0),
    0,
  );

  const salvar = async (event) => {
    event.preventDefault();
    try {
      setSalvando(true);
      await api.put(`/produtos/${produto.id}/lotes-validade`, {
        ...form,
        nome_lote: form.nome_lote.trim(),
        quantidade: Number(form.quantidade),
        data_fabricacao: form.data_fabricacao || null,
      });
      toast.success("Lote e validade salvos. O saldo do estoque foi mantido.");
      setForm(FORM_INICIAL);
      const { data } = await getLotes(produto.id);
      setLotes(data || []);
      await onSaved();
    } catch (error) {
      toast.error(
        extrairMensagemErroApiMovimentacao(error, "Não foi possível salvar o lote e a validade."),
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
        className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white shadow-xl"
      >
        <div className="flex items-start justify-between border-b p-5">
          <div>
            <h2 id="titulo-lotes-validade" className="text-xl font-bold text-slate-900">
              Lotes e validade
            </h2>
            <p className="mt-1 text-sm text-slate-600">{produto.nome}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={salvando}
            aria-label="Fechar lotes e validade"
            className="rounded-lg p-2 hover:bg-slate-100"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="space-y-5 p-5">
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">
            Informe quantas unidades do estoque atual pertencem a cada lote. Este cadastro não soma
            nem subtrai produtos do estoque.
            <div className="mt-2 flex flex-wrap gap-4 font-semibold">
              <span>
                Estoque atual: {formatarQuantidadeMovimentacao(estoqueAtual)}{" "}
                {produto.unidade || "UN"}
              </span>
              <span>
                Identificado em lotes: {formatarQuantidadeMovimentacao(quantidadeIdentificada)}
              </span>
            </div>
          </div>
          {loading ? (
            <p className="text-sm text-slate-500">Carregando lotes...</p>
          ) : erroCarga ? (
            <p role="alert" className="text-sm text-red-700">
              {erroCarga}
            </p>
          ) : (
            <>
              <div className="overflow-x-auto rounded-lg border">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-left">
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
                        <td colSpan={4} className="p-4 text-center text-slate-500">
                          Nenhum lote identificado.
                        </td>
                      </tr>
                    ) : (
                      lotes.map((lote) => (
                        <tr key={lote.id} className="border-t">
                          <td className="p-3">
                            {lote.nome_lote}
                            <span className="block text-xs text-slate-500">
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
                            <button
                              type="button"
                              disabled={salvando}
                              onClick={() => editarLote(lote)}
                              className="font-medium text-blue-700 hover:underline"
                            >
                              Corrigir identificação
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
              <form onSubmit={salvar} className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-slate-900">
                    {form.lote_id ? "Corrigir lote e validade" : "Informar lote e validade"}
                  </h3>
                  {form.lote_id && (
                    <button
                      type="button"
                      disabled={salvando}
                      onClick={() => setForm(FORM_INICIAL)}
                      className="text-sm text-blue-700"
                    >
                      Informar outro lote
                    </button>
                  )}
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="text-sm font-medium text-slate-700">
                    Número do lote *
                    <input
                      type="text"
                      required
                      maxLength={50}
                      value={form.nome_lote}
                      onChange={(event) => alterar("nome_lote", event.target.value)}
                      className="mt-1 w-full rounded-lg border p-2"
                    />
                  </label>
                  <label className="text-sm font-medium text-slate-700">
                    Quantidade atual deste lote *
                    <input
                      type="number"
                      required
                      min={form.lote_id ? 0 : "0.0001"}
                      step="any"
                      value={form.quantidade}
                      onChange={(event) => alterar("quantidade", event.target.value)}
                      className="mt-1 w-full rounded-lg border p-2"
                    />
                  </label>
                  <label className="text-sm font-medium text-slate-700">
                    Validade *
                    <input
                      type="date"
                      required
                      value={form.data_validade}
                      onChange={(event) => alterar("data_validade", event.target.value)}
                      className="mt-1 w-full rounded-lg border p-2"
                    />
                  </label>
                  <label className="text-sm font-medium text-slate-700">
                    Fabricação
                    <input
                      type="date"
                      value={form.data_fabricacao}
                      onChange={(event) => alterar("data_fabricacao", event.target.value)}
                      className="mt-1 w-full rounded-lg border p-2"
                    />
                  </label>
                </div>
                <p className="text-xs text-slate-500">
                  A quantidade informada substitui a identificação atual do lote. Para retirar a
                  identificação de um lote existente, informe zero. Entradas e saídas continuam em
                  “Incluir lançamento”.
                </p>
                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={salvando}
                    className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    {salvando ? "Salvando..." : "Salvar identificação"}
                  </button>
                </div>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
