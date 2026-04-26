import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import ProdutoEstoqueAutocomplete from "../../../components/veterinario/ProdutoEstoqueAutocomplete";
import { banhoTosaApi } from "../banhoTosaApi";
import { formatCurrency, getApiErrorMessage, toApiDecimal } from "../banhoTosaUtils";
import BanhoTosaInsumoAcoes from "./BanhoTosaInsumoAcoes";

const initialForm = {
  quantidade_usada: "1",
  quantidade_desperdicio: "0",
  responsavel_id: "",
  baixar_estoque: false,
};

export default function BanhoTosaInsumosPanel({
  atendimentoId,
  funcionarios,
  onChanged,
}) {
  const [insumos, setInsumos] = useState([]);
  const [produtoSelecionado, setProdutoSelecionado] = useState(null);
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [removingId, setRemovingId] = useState(null);
  const [estornandoId, setEstornandoId] = useState(null);

  async function carregarInsumos() {
    if (!atendimentoId) return;
    setLoading(true);
    try {
      const response = await banhoTosaApi.listarInsumosAtendimento(atendimentoId);
      setInsumos(Array.isArray(response.data) ? response.data : []);
    } catch {
      setInsumos([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    carregarInsumos();
  }, [atendimentoId]);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function salvarInsumo(event) {
    event.preventDefault();
    if (!produtoSelecionado?.id) {
      toast.error("Selecione um insumo/produto.");
      return;
    }

    setSaving(true);
    try {
      await banhoTosaApi.registrarInsumoAtendimento(atendimentoId, {
        produto_id: produtoSelecionado.id,
        quantidade_usada: toApiDecimal(form.quantidade_usada),
        quantidade_desperdicio: toApiDecimal(form.quantidade_desperdicio),
        responsavel_id: form.responsavel_id ? Number(form.responsavel_id) : null,
        baixar_estoque: Boolean(form.baixar_estoque),
      });
      toast.success("Insumo registrado.");
      setProdutoSelecionado(null);
      setForm(initialForm);
      await carregarInsumos();
      await onChanged?.();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel registrar insumo."));
    } finally {
      setSaving(false);
    }
  }

  async function removerInsumo(insumo) {
    setRemovingId(insumo.id);
    try {
      await banhoTosaApi.removerInsumoAtendimento(atendimentoId, insumo.id);
      toast.success("Insumo removido.");
      await carregarInsumos();
      await onChanged?.();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel remover insumo."));
    } finally {
      setRemovingId(null);
    }
  }

  async function estornarEstoque(insumo) {
    setEstornandoId(insumo.id);
    try {
      await banhoTosaApi.estornarEstoqueInsumo(atendimentoId, insumo.id);
      toast.success("Estoque estornado.");
      await carregarInsumos();
      await onChanged?.();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel estornar o estoque."));
    } finally {
      setEstornandoId(null);
    }
  }

  return (
    <div className="mt-6 rounded-3xl border border-slate-200 bg-slate-50 p-5">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
          Insumos reais
        </p>
        <h3 className="mt-2 text-lg font-black text-slate-900">
          Produtos consumidos no atendimento
        </h3>
        <p className="mt-1 text-sm text-slate-500">
          Registre shampoo, condicionador, laços, toalhas extras ou perdas para fechar a margem.
        </p>
      </div>

      <form onSubmit={salvarInsumo} className="mt-5 grid gap-4 lg:grid-cols-[1.4fr_0.55fr_0.55fr_0.8fr_auto]">
        <ProdutoEstoqueAutocomplete
          label="Insumo"
          selectedProduct={produtoSelecionado}
          onSelect={setProdutoSelecionado}
          searchProducts={banhoTosaApi.listarProdutosEstoque}
          helperText="Pesquise pelo nome ou codigo do produto consumido."
        />
        <NumberField
          label="Usado"
          value={form.quantidade_usada}
          onChange={(value) => updateField("quantidade_usada", value)}
        />
        <NumberField
          label="Desperdicio"
          value={form.quantidade_desperdicio}
          onChange={(value) => updateField("quantidade_desperdicio", value)}
        />
        <label className="block">
          <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
            Responsavel
          </span>
          <select
            value={form.responsavel_id}
            onChange={(event) => updateField("responsavel_id", event.target.value)}
            className="mt-1 w-full rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100"
          >
            <option value="">Nao informado</option>
            {funcionarios.map((pessoa) => (
              <option key={pessoa.id} value={pessoa.id}>{pessoa.nome}</option>
            ))}
          </select>
          <label className="mt-2 flex items-center gap-2 text-xs font-bold text-slate-500">
            <input
              type="checkbox"
              checked={form.baixar_estoque}
              onChange={(event) => updateField("baixar_estoque", event.target.checked)}
            />
            Baixar estoque agora
          </label>
        </label>
        <button
          type="submit"
          disabled={saving}
          className="self-end rounded-2xl bg-orange-500 px-5 py-3 text-sm font-bold text-white transition hover:bg-orange-600 disabled:opacity-60"
        >
          {saving ? "Salvando..." : "Adicionar"}
        </button>
      </form>

      <div className="mt-5 space-y-2">
        {loading ? (
          <p className="text-sm font-semibold text-slate-500">Carregando insumos...</p>
        ) : insumos.length === 0 ? (
          <p className="rounded-2xl border border-dashed border-slate-300 bg-white p-4 text-sm text-slate-500">
            Nenhum insumo registrado ainda.
          </p>
        ) : (
          insumos.map((insumo) => (
            <div key={insumo.id} className="flex flex-col gap-3 rounded-2xl bg-white p-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-black text-slate-900">{insumo.produto_nome || `Produto #${insumo.produto_id}`}</p>
                <p className="text-sm text-slate-500">
                  Usado: {insumo.quantidade_usada} | Desperdicio: {insumo.quantidade_desperdicio} {insumo.unidade || ""}
                </p>
                {insumo.responsavel_nome && (
                  <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">
                    Resp.: {insumo.responsavel_nome}
                  </p>
                )}
              </div>
              <div className="text-left sm:text-right">
                <p className="text-sm font-black text-slate-900">
                  {formatCurrency(insumo.custo_total)}
                </p>
                <BanhoTosaInsumoAcoes
                  insumo={insumo}
                  removing={removingId === insumo.id}
                  estornando={estornandoId === insumo.id}
                  onEstornar={estornarEstoque}
                  onRemover={removerInsumo}
                />
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function NumberField({ label, value, onChange }) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
        {label}
      </span>
      <input
        type="number"
        min="0"
        step="0.01"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100"
      />
    </label>
  );
}
