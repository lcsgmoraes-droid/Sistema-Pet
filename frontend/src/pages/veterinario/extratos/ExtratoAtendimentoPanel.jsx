import { useEffect, useMemo, useState } from "react";
import { FileSpreadsheet, FileText, RefreshCw } from "lucide-react";

import { formatMoneyBRL, formatPercent } from "../../../utils/formatters";
import { vetApi } from "../vetApi";
import {
  EXTRATO_COLUNAS,
  EXTRATO_COLUNAS_DEFAULT,
  buildExtratoDownloadName,
  buildExtratoParams,
  downloadBlob,
  normalizarColunasSelecionadas,
  resumirLinhasExtrato,
} from "./extratoUtils";

const checkboxClass = "h-4 w-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500";

export default function ExtratoAtendimentoPanel({
  contexto,
  titulo = "Extrato do atendimento",
}) {
  const [extrato, setExtrato] = useState(null);
  const [colunasSelecionadas, setColunasSelecionadas] = useState(EXTRATO_COLUNAS_DEFAULT);
  const [carregando, setCarregando] = useState(false);
  const [exportando, setExportando] = useState(null);
  const [erro, setErro] = useState(null);

  const podeCarregar = Boolean(contexto?.consultaId || contexto?.internacaoId);
  const chaveContexto = `${contexto?.consultaId || ""}:${contexto?.internacaoId || ""}`;

  async function carregarExtrato() {
    if (!podeCarregar) return;
    setCarregando(true);
    setErro(null);
    try {
      const response = await vetApi.obterExtratoAtendimento(buildExtratoParams(contexto, colunasSelecionadas));
      setExtrato(response.data || null);
      if (Array.isArray(response.data?.colunas)) {
        setColunasSelecionadas(normalizarColunasSelecionadas(response.data.colunas));
      }
    } catch (error) {
      setErro(error?.response?.data?.detail || "Nao foi possivel carregar o extrato.");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregarExtrato();
  }, [chaveContexto]);

  const totais = extrato?.totais || {};
  const linhas = Array.isArray(extrato?.linhas) ? extrato.linhas : [];
  const resumoLinhas = useMemo(() => resumirLinhasExtrato(linhas), [linhas]);

  function toggleColuna(chave) {
    setColunasSelecionadas((prev) => {
      const atual = normalizarColunasSelecionadas(prev);
      if (atual.includes(chave)) {
        const semColuna = atual.filter((item) => item !== chave);
        return semColuna.length ? semColuna : atual;
      }
      return [...atual, chave];
    });
  }

  async function exportar(formato) {
    if (!podeCarregar) return;
    setExportando(formato);
    setErro(null);
    try {
      const params = buildExtratoParams(contexto, colunasSelecionadas);
      const response = formato === "pdf"
        ? await vetApi.exportarExtratoAtendimentoPdf(params)
        : await vetApi.exportarExtratoAtendimentoExcel(params);
      downloadBlob(response.data, buildExtratoDownloadName(contexto, formato === "pdf" ? "pdf" : "xlsx"));
    } catch (error) {
      setErro(error?.response?.data?.detail || "Nao foi possivel exportar o extrato.");
    } finally {
      setExportando(null);
    }
  }

  if (!podeCarregar) return null;

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold text-gray-800">{titulo}</h2>
          <p className="mt-1 text-xs text-gray-500">
            Custo {formatMoneyBRL(totais.custo_total || 0)} · Venda {formatMoneyBRL(totais.preco_total || 0)} · Margem {formatMoneyBRL(totais.margem_valor || 0)} ({formatPercent(totais.margem_percentual || 0)})
          </p>
          <p className="mt-1 text-xs text-gray-400">
            {resumoLinhas.contabilizadas} linha(s) no total · {resumoLinhas.detalhes} detalhe(s)
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={carregarExtrato}
            disabled={carregando}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw size={15} />
            {carregando ? "Atualizando..." : "Atualizar"}
          </button>
          <button
            type="button"
            onClick={() => exportar("pdf")}
            disabled={exportando || carregando}
            className="inline-flex items-center gap-2 rounded-lg border border-emerald-200 px-3 py-2 text-sm font-medium text-emerald-700 hover:bg-emerald-50 disabled:opacity-50"
          >
            <FileText size={15} />
            PDF
          </button>
          <button
            type="button"
            onClick={() => exportar("xlsx")}
            disabled={exportando || carregando}
            className="inline-flex items-center gap-2 rounded-lg border border-emerald-200 px-3 py-2 text-sm font-medium text-emerald-700 hover:bg-emerald-50 disabled:opacity-50"
          >
            <FileSpreadsheet size={15} />
            Excel
          </button>
        </div>
      </div>

      {erro && (
        <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">{erro}</p>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        {EXTRATO_COLUNAS.map((coluna) => (
          <label key={coluna.chave} className="inline-flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-xs text-gray-600">
            <input
              type="checkbox"
              checked={colunasSelecionadas.includes(coluna.chave)}
              onChange={() => toggleColuna(coluna.chave)}
              className={checkboxClass}
            />
            {coluna.titulo}
          </label>
        ))}
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-xs uppercase text-gray-400">
              <th className="py-2 pr-4 font-medium">Origem</th>
              <th className="py-2 pr-4 font-medium">Descricao</th>
              <th className="py-2 pr-4 text-right font-medium">Qtd.</th>
              <th className="py-2 pr-4 text-right font-medium">Custo</th>
              <th className="py-2 pr-4 text-right font-medium">Venda</th>
              <th className="py-2 pr-4 text-right font-medium">Margem</th>
              <th className="py-2 pr-4 font-medium">Total</th>
            </tr>
          </thead>
          <tbody>
            {linhas.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-4 text-xs text-gray-400">
                  Nenhum item realizado encontrado para o extrato.
                </td>
              </tr>
            ) : (
              linhas.map((linha, index) => (
                <tr key={`${linha.referencia || "linha"}_${index}`} className="border-b border-gray-50">
                  <td className="py-2 pr-4 text-xs text-gray-500">{linha.origem_label}</td>
                  <td className="py-2 pr-4">
                    <p className="font-medium text-gray-800">{linha.nome}</p>
                    {linha.parent_referencia && <p className="text-xs text-gray-400">Detalhe de {linha.parent_referencia}</p>}
                  </td>
                  <td className="py-2 pr-4 text-right text-gray-600">{Number(linha.quantidade || 0).toLocaleString("pt-BR")} {linha.unidade || ""}</td>
                  <td className="py-2 pr-4 text-right text-amber-700">{formatMoneyBRL(linha.custo_total || 0)}</td>
                  <td className="py-2 pr-4 text-right text-gray-800">{formatMoneyBRL(linha.preco_total || 0)}</td>
                  <td className="py-2 pr-4 text-right text-emerald-700">{formatMoneyBRL(linha.margem_valor || 0)}</td>
                  <td className="py-2 pr-4 text-xs text-gray-500">{linha.contabilizar_label}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
