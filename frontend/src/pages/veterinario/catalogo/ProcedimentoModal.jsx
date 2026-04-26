import { formatMoneyBRL, formatPercent } from "../../../utils/formatters";
import { Modal } from "./shared";

export default function ProcedimentoModal({
  adicionarInsumo,
  atualizarInsumo,
  editando,
  form,
  onClose,
  onSave,
  produtos,
  removerInsumo,
  resumoMargem,
  salvando,
  setCampo,
}) {
  return (
    <Modal
      titulo={editando ? "Editar procedimento" : "Novo procedimento"}
      subtitulo="Monte o procedimento com duracao, preco e insumos que devem sair do estoque."
      onClose={onClose}
      onSave={onSave}
      salvando={salvando}
    >
      <div className="space-y-4">
        <DadosProcedimentoForm form={form} setCampo={setCampo} />

        <InsumosProcedimentoSection
          adicionarInsumo={adicionarInsumo}
          atualizarInsumo={atualizarInsumo}
          form={form}
          produtos={produtos}
          removerInsumo={removerInsumo}
          resumoMargem={resumoMargem}
        />
      </div>
    </Modal>
  );
}

function DadosProcedimentoForm({ form, setCampo }) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      <div className="md:col-span-2">
        <label className="mb-1 block text-xs font-medium text-gray-600">Nome *</label>
        <input
          type="text"
          value={form.nome}
          onChange={(event) => setCampo("nome", event.target.value)}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
        />
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600">Categoria</label>
        <input
          type="text"
          value={form.categoria}
          onChange={(event) => setCampo("categoria", event.target.value)}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
          placeholder="Consulta, coleta, curativo..."
        />
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600">Duracao (min)</label>
        <input
          type="number"
          value={form.duracao}
          onChange={(event) => setCampo("duracao", event.target.value)}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
        />
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600">Preco sugerido (R$)</label>
        <input
          type="text"
          value={form.preco}
          onChange={(event) => setCampo("preco", event.target.value)}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
          placeholder="0,00"
        />
      </div>
      <label className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm">
        <input
          type="checkbox"
          checked={form.requer_anestesia}
          onChange={(event) => setCampo("requer_anestesia", event.target.checked)}
        />
        Requer anestesia
      </label>
      <div className="md:col-span-2">
        <label className="mb-1 block text-xs font-medium text-gray-600">Descricao</label>
        <textarea
          value={form.descricao}
          onChange={(event) => setCampo("descricao", event.target.value)}
          className="min-h-[72px] w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
        />
      </div>
      <div className="md:col-span-2">
        <label className="mb-1 block text-xs font-medium text-gray-600">Observacoes internas</label>
        <textarea
          value={form.observacoes}
          onChange={(event) => setCampo("observacoes", event.target.value)}
          className="min-h-[72px] w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
        />
      </div>
    </div>
  );
}

function InsumosProcedimentoSection({
  adicionarInsumo,
  atualizarInsumo,
  form,
  produtos,
  removerInsumo,
  resumoMargem,
}) {
  return (
    <div className="space-y-3 rounded-xl border border-gray-200 bg-gray-50 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-gray-800">Insumos com baixa automatica</p>
          <p className="text-xs text-gray-500">
            Escolha os itens do estoque que saem automaticamente quando o procedimento for usado.
          </p>
        </div>
        <button
          type="button"
          onClick={adicionarInsumo}
          className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium hover:bg-gray-100"
        >
          + Adicionar insumo
        </button>
      </div>

      {form.insumos.length === 0 ? (
        <p className="text-xs text-gray-500">Nenhum insumo vinculado.</p>
      ) : (
        form.insumos.map((item, index) => (
          <InsumoProcedimentoRow
            key={`insumo_${index}`}
            index={index}
            item={item}
            produtos={produtos}
            removerInsumo={removerInsumo}
            atualizarInsumo={atualizarInsumo}
          />
        ))
      )}

      <ResumoMargemProcedimento resumoMargem={resumoMargem} />
    </div>
  );
}

function InsumoProcedimentoRow({ atualizarInsumo, index, item, produtos, removerInsumo }) {
  return (
    <div className="grid gap-2 md:grid-cols-12">
      <select
        value={item.produto_id}
        onChange={(event) => atualizarInsumo(index, "produto_id", event.target.value)}
        className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm md:col-span-7"
      >
        <option value="">Selecione um produto</option>
        {produtos.map((produto) => (
          <option key={produto.id} value={produto.id}>
            {produto.nome} - estoque {produto.estoque_atual} {produto.unidade || "UN"}
          </option>
        ))}
      </select>
      <input
        type="number"
        min="0"
        step="0.01"
        value={item.quantidade}
        onChange={(event) => atualizarInsumo(index, "quantidade", event.target.value)}
        className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm md:col-span-2"
        placeholder="Qtd."
      />
      <label className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs md:col-span-2">
        <input
          type="checkbox"
          checked={item.baixar_estoque !== false}
          onChange={(event) => atualizarInsumo(index, "baixar_estoque", event.target.checked)}
        />
        Baixar
      </label>
      <button
        type="button"
        onClick={() => removerInsumo(index)}
        className="rounded-lg border border-red-200 px-3 py-2 text-xs font-medium text-red-600 hover:bg-red-50 md:col-span-1"
      >
        X
      </button>
    </div>
  );
}

function ResumoMargemProcedimento({ resumoMargem }) {
  const { custoEstimadoForm, margemEstimadaForm, margemPercentualForm, precoSugeridoForm } = resumoMargem;

  return (
    <div className="grid gap-3 border-t border-gray-200 pt-3 md:grid-cols-3">
      <div className="rounded-lg border border-gray-200 bg-white px-3 py-2">
        <p className="text-[11px] uppercase tracking-wide text-gray-400">Preco</p>
        <p className="text-sm font-semibold text-gray-800">{formatMoneyBRL(precoSugeridoForm)}</p>
      </div>
      <div className="rounded-lg border border-gray-200 bg-white px-3 py-2">
        <p className="text-[11px] uppercase tracking-wide text-gray-400">Custo estimado</p>
        <p className="text-sm font-semibold text-amber-700">{formatMoneyBRL(custoEstimadoForm)}</p>
      </div>
      <div className="rounded-lg border border-gray-200 bg-white px-3 py-2">
        <p className="text-[11px] uppercase tracking-wide text-gray-400">Margem estimada</p>
        <p className={`text-sm font-semibold ${margemEstimadaForm < 0 ? "text-red-600" : "text-emerald-700"}`}>
          {formatMoneyBRL(margemEstimadaForm)}
        </p>
        <p className="text-[11px] text-gray-400">{formatPercent(margemPercentualForm)}</p>
      </div>
    </div>
  );
}
