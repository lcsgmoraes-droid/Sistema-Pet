import { useEffect, useState } from "react";
import { AlertCircle, Loader2, Plus } from "lucide-react";
import { vetApi } from "../vetApi";
import { formatMoneyBRL, formatPercent } from "../../../utils/formatters";
import { LinhaAcoes, Modal, parseNumero } from "./shared";

const FORM_PROCEDIMENTO_INICIAL = {
  nome: "",
  descricao: "",
  categoria: "",
  duracao: "",
  preco: "",
  requer_anestesia: false,
  observacoes: "",
  insumos: [],
};

function mapProcedimentoParaForm(item) {
  return {
    nome: item?.nome || "",
    descricao: item?.descricao || "",
    categoria: item?.categoria || "",
    duracao: item?.duracao_minutos ?? item?.duracao_estimada_min ?? "",
    preco: item?.valor_padrao ?? "",
    requer_anestesia: Boolean(item?.requer_anestesia),
    observacoes: item?.observacoes || "",
    insumos: Array.isArray(item?.insumos)
      ? item.insumos.map((insumo) => ({
          produto_id: insumo.produto_id ? String(insumo.produto_id) : "",
          quantidade: insumo.quantidade ?? "1",
          baixar_estoque: insumo.baixar_estoque !== false,
        }))
      : [],
  };
}

export default function CatProcedimentos() {
  const [lista, setLista] = useState([]);
  const [produtos, setProdutos] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [modalAberto, setModalAberto] = useState(false);
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState(FORM_PROCEDIMENTO_INICIAL);
  const [salvando, setSalvando] = useState(false);
  const [removendoId, setRemovendoId] = useState(null);
  const [erro, setErro] = useState("");

  async function carregar() {
    setCarregando(true);
    setErro("");
    try {
      const [procedimentosResponse, produtosResponse] = await Promise.all([
        vetApi.listarCatalogoProcedimentos(),
        vetApi.listarProdutosEstoque(),
      ]);
      setLista(
        Array.isArray(procedimentosResponse.data)
          ? procedimentosResponse.data
          : procedimentosResponse.data?.items ?? []
      );
      setProdutos(Array.isArray(produtosResponse.data) ? produtosResponse.data : produtosResponse.data?.items ?? []);
    } catch (err) {
      setErro(err?.response?.data?.detail || "Erro ao carregar procedimentos.");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregar();
  }, []);

  function setCampo(campo, valor) {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  }

  function abrirNovo() {
    setEditando(null);
    setForm(FORM_PROCEDIMENTO_INICIAL);
    setModalAberto(true);
    setErro("");
  }

  function abrirEdicao(item) {
    setEditando(item);
    setForm(mapProcedimentoParaForm(item));
    setModalAberto(true);
    setErro("");
  }

  function atualizarInsumo(index, campo, valor) {
    setForm((prev) => {
      const insumos = [...prev.insumos];
      insumos[index] = { ...insumos[index], [campo]: valor };
      return { ...prev, insumos };
    });
  }

  function adicionarInsumo() {
    setForm((prev) => ({
      ...prev,
      insumos: [...prev.insumos, { produto_id: "", quantidade: "1", baixar_estoque: true }],
    }));
  }

  function removerInsumo(index) {
    setForm((prev) => ({
      ...prev,
      insumos: prev.insumos.filter((_, currentIndex) => currentIndex !== index),
    }));
  }

  const custoEstimadoForm = form.insumos.reduce((total, item) => {
    const produto = produtos.find((produtoAtual) => String(produtoAtual.id) === String(item.produto_id));
    return total + (Number(produto?.preco_custo || 0) * (parseNumero(item.quantidade) || 0));
  }, 0);
  const precoSugeridoForm = parseNumero(form.preco) || 0;
  const margemEstimadaForm = precoSugeridoForm - custoEstimadoForm;
  const margemPercentualForm = precoSugeridoForm > 0 ? (margemEstimadaForm / precoSugeridoForm) * 100 : 0;

  async function salvar() {
    if (!form.nome.trim()) return;
    setSalvando(true);
    setErro("");
    try {
      const payload = {
        nome: form.nome.trim(),
        descricao: form.descricao.trim() || undefined,
        categoria: form.categoria.trim() || undefined,
        valor_padrao: parseNumero(form.preco),
        duracao_minutos: form.duracao ? parseInt(form.duracao, 10) : undefined,
        requer_anestesia: Boolean(form.requer_anestesia),
        observacoes: form.observacoes.trim() || undefined,
        insumos: form.insumos
          .map((item) => ({
            produto_id: item.produto_id ? Number(item.produto_id) : null,
            quantidade: parseNumero(item.quantidade),
            baixar_estoque: item.baixar_estoque !== false,
          }))
          .filter((item) => item.produto_id && item.quantidade > 0),
      };

      if (editando?.id) {
        await vetApi.atualizarCatalogoProcedimento(editando.id, payload);
      } else {
        await vetApi.criarCatalogoProcedimento(payload);
      }
      setModalAberto(false);
      setEditando(null);
      setForm(FORM_PROCEDIMENTO_INICIAL);
      await carregar();
    } catch (err) {
      setErro(err?.response?.data?.detail || "Erro ao salvar procedimento.");
    } finally {
      setSalvando(false);
    }
  }

  async function excluir(item) {
    if (!window.confirm(`Deseja excluir o procedimento "${item.nome}"?`)) return;
    setRemovendoId(item.id);
    setErro("");
    try {
      await vetApi.removerCatalogoProcedimento(item.id);
      await carregar();
    } catch (err) {
      setErro(err?.response?.data?.detail || "Erro ao excluir procedimento.");
    } finally {
      setRemovendoId(null);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <button
          type="button"
          onClick={abrirNovo}
          className="inline-flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700"
        >
          <Plus size={14} />
          Adicionar
        </button>
      </div>

      {erro && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          <AlertCircle size={16} />
          <span>{erro}</span>
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
        {carregando ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-teal-500" />
          </div>
        ) : lista.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-400">Nenhum procedimento cadastrado.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-gray-100 bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Procedimento</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Insumos</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Duracao</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Preco sugerido</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Margem estimada</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Acoes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {lista.map((item) => (
                <tr key={item.id} className="hover:bg-teal-50">
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-800">{item.nome}</p>
                    <p className="text-xs text-gray-500">
                      {item.categoria || item.descricao || (item.requer_anestesia ? "Requer anestesia" : "-")}
                    </p>
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {Array.isArray(item.insumos) && item.insumos.length > 0 ? `${item.insumos.length} item(ns)` : "-"}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {item.duracao_minutos || item.duracao_estimada_min
                      ? `${item.duracao_minutos || item.duracao_estimada_min} min`
                      : "-"}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{formatMoneyBRL(item.valor_padrao || 0)}</td>
                  <td className="px-4 py-3">
                    <p className={`font-medium ${(item.margem_estimada || 0) < 0 ? "text-red-600" : "text-emerald-700"}`}>
                      {formatMoneyBRL(item.margem_estimada || 0)}
                    </p>
                    <p className="text-xs text-gray-400">{formatPercent(item.margem_percentual_estimada || 0)}</p>
                  </td>
                  <td className="px-4 py-3">
                    <LinhaAcoes
                      onEditar={() => abrirEdicao(item)}
                      onExcluir={() => excluir(item)}
                      removendo={removendoId === item.id}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {modalAberto && (
        <Modal
          titulo={editando ? "Editar procedimento" : "Novo procedimento"}
          subtitulo="Monte o procedimento com duracao, preco e insumos que devem sair do estoque."
          onClose={() => setModalAberto(false)}
          onSave={salvar}
          salvando={salvando}
        >
          <div className="space-y-4">
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
                  <div key={`insumo_${index}`} className="grid gap-2 md:grid-cols-12">
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
                ))
              )}

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
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
