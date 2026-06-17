import { X } from "lucide-react";

import AutocompleteSelect from "../../../components/ui/AutocompleteSelect";
import { formatMoneyBRL, formatPercent } from "../../../utils/formatters";
import { css, obterResumoProcedimentoSelecionado } from "./consultaFormUtils";

export default function ProcedimentosRealizadosSection({
  modoSomenteLeitura,
  form,
  procedimentosCatalogo,
  consultaIdAtual,
  adicionarProcedimento,
  removerProcedimento,
  setProcedimentoItem,
  selecionarProcedimentoCatalogo,
  abrirModalInsumoRapido,
}) {
  return (
    <fieldset
      disabled={modoSomenteLeitura}
      className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-3 disabled:opacity-100"
    >
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-gray-700">Procedimentos realizados</h2>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={adicionarProcedimento}
            className="text-xs text-blue-600 hover:text-blue-800 underline"
          >
            + Adicionar procedimento
          </button>
          <button
            type="button"
            onClick={abrirModalInsumoRapido}
            disabled={!consultaIdAtual}
            className="text-xs text-emerald-600 hover:text-emerald-800 underline disabled:opacity-50"
          >
            {" + Lan\u00e7ar insumo r\u00e1pido"}
          </button>
        </div>
      </div>
      {form.procedimentos_realizados.length === 0 && (
        <p className="text-xs text-gray-400">{"Nenhum procedimento lan\u00e7ado ainda."}</p>
      )}
      {form.procedimentos_realizados.map((item, idx) => {
        const resumo = obterResumoProcedimentoSelecionado(item, procedimentosCatalogo);

        return (
          <div
            key={`procedimento_${idx}`}
            className="border border-gray-100 rounded-lg p-3 space-y-2 relative"
          >
            <button
              type="button"
              onClick={() => removerProcedimento(idx)}
              className="absolute top-2 right-2 text-gray-300 hover:text-red-400"
            >
              <X size={14} />
            </button>
            <div className="grid grid-cols-2 gap-2">
              <AutocompleteSelect
                value={item.catalogo_id || ""}
                onChange={(procedimentoId) => selecionarProcedimentoCatalogo(idx, procedimentoId)}
                options={procedimentosCatalogo}
                getOptionLabel={(procedimento) => procedimento.nome}
                getOptionMeta={(procedimento) => procedimento.descricao}
                placeholder="Digite para buscar procedimento..."
                emptyLabel="Nenhum procedimento encontrado"
                showLabel={false}
              />
              <input
                type="text"
                placeholder="Nome do procedimento"
                value={item.nome}
                onChange={(e) => setProcedimentoItem(idx, "nome", e.target.value)}
                className={css.input}
              />
              <input
                type="text"
                placeholder={"Descri\u00e7\u00e3o"}
                value={item.descricao}
                onChange={(e) => setProcedimentoItem(idx, "descricao", e.target.value)}
                className={css.input}
              />
              <input
                type="text"
                placeholder="Valor"
                value={item.valor}
                onChange={(e) => setProcedimentoItem(idx, "valor", e.target.value)}
                className={css.input}
              />
            </div>
            <input
              type="text"
              placeholder={"Observa\u00e7\u00f5es"}
              value={item.observacoes}
              onChange={(e) => setProcedimentoItem(idx, "observacoes", e.target.value)}
              className={css.input}
            />
            {resumo.possuiCatalogo && (
              <div className="grid grid-cols-3 gap-2 rounded-lg bg-gray-50 border border-gray-200 px-3 py-2">
                <div>
                  <p className="text-[11px] uppercase tracking-wide text-gray-400">Cobrado</p>
                  <p className="text-sm font-semibold text-gray-800">
                    {formatMoneyBRL(resumo.valorCobrado)}
                  </p>
                </div>
                <div>
                  <p className="text-[11px] uppercase tracking-wide text-gray-400">Custo est.</p>
                  <p className="text-sm font-semibold text-amber-700">
                    {formatMoneyBRL(resumo.custoTotal)}
                  </p>
                </div>
                <div>
                  <p className="text-[11px] uppercase tracking-wide text-gray-400">Margem est.</p>
                  <p
                    className={`text-sm font-semibold ${resumo.margemValor < 0 ? "text-red-600" : "text-emerald-700"}`}
                  >
                    {formatMoneyBRL(resumo.margemValor)}
                  </p>
                  <p className="text-[11px] text-gray-400">
                    {formatPercent(resumo.margemPercentual)}
                  </p>
                </div>
              </div>
            )}
            <label className="flex items-center gap-2 text-xs text-gray-600">
              <input
                type="checkbox"
                checked={item.baixar_estoque !== false}
                onChange={(e) => setProcedimentoItem(idx, "baixar_estoque", e.target.checked)}
              />
              {"Baixar estoque autom\u00e1tico dos insumos vinculados"}
            </label>
          </div>
        );
      })}
    </fieldset>
  );
}
