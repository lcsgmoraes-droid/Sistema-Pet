import { useEffect, useMemo, useState } from "react";
import { Calculator, Plus, Save, Trash2 } from "lucide-react";

import ProdutoEstoqueAutocomplete from "../../../components/veterinario/ProdutoEstoqueAutocomplete";
import { formatMoneyBRL, formatPercent } from "../../../utils/formatters";
import { vetApi } from "../vetApi";
import {
  calcularTotaisOrcamento,
  criarItemCatalogoOrcamento,
  criarItemDiariaOrcamento,
  criarItemProdutoOrcamento,
  recalcularItemOrcamento,
  toNumber,
} from "./orcamentoUtils";

const inputClass =
  "w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-300";
const selectClass = `${inputClass} bg-white`;

export default function OrcamentoMvpPanel({
  contexto,
  procedimentosCatalogo = [],
  modoSomenteLeitura = false,
  titulo = "Orçamento",
}) {
  const [orcamentoId, setOrcamentoId] = useState(null);
  const [itens, setItens] = useState([]);
  const [catalogoId, setCatalogoId] = useState("");
  const [quantidadeCatalogo, setQuantidadeCatalogo] = useState("1");
  const [produtoSelecionado, setProdutoSelecionado] = useState(null);
  const [quantidadeProduto, setQuantidadeProduto] = useState("1");
  const [diasInternacao, setDiasInternacao] = useState(String(contexto?.previsaoDias || 1));
  const [diariaCusto, setDiariaCusto] = useState("");
  const [diariaPreco, setDiariaPreco] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const chaveContexto = `${contexto?.consultaId || ""}:${contexto?.internacaoId || ""}:${contexto?.petId || ""}`;

  useEffect(() => {
    if (!contexto?.consultaId && !contexto?.internacaoId) {
      setOrcamentoId(null);
      setItens([]);
      return;
    }

    let ativo = true;
    async function carregarOrcamento() {
      setCarregando(true);
      setFeedback(null);
      try {
        const params = contexto?.consultaId
          ? { consulta_id: contexto.consultaId }
          : { internacao_id: contexto.internacaoId };
        const response = await vetApi.listarOrcamentos(params);
        const lista = Array.isArray(response.data) ? response.data : [];
        const atual = lista.find((item) => item.status === "rascunho") || lista[0];
        if (!ativo) return;
        setOrcamentoId(atual?.id ?? null);
        setItens(Array.isArray(atual?.itens) ? atual.itens : []);
        if (atual?.previsao_dias_internacao) {
          setDiasInternacao(String(atual.previsao_dias_internacao));
        }
      } catch {
        if (ativo) setFeedback({ tipo: "erro", texto: "Não foi possível carregar o orçamento." });
      } finally {
        if (ativo) setCarregando(false);
      }
    }

    carregarOrcamento();
    return () => {
      ativo = false;
    };
  }, [chaveContexto, contexto?.consultaId, contexto?.internacaoId]);

  const totais = useMemo(() => calcularTotaisOrcamento(itens), [itens]);
  const catalogoSelecionado = procedimentosCatalogo.find(
    (item) => String(item.id) === String(catalogoId),
  );
  const podeSalvar =
    !modoSomenteLeitura && (contexto?.consultaId || contexto?.internacaoId || contexto?.petId);

  const adicionarCatalogo = () => {
    if (!catalogoSelecionado) return;
    setItens((prev) => [
      ...prev,
      criarItemCatalogoOrcamento(catalogoSelecionado, quantidadeCatalogo),
    ]);
    setCatalogoId("");
    setQuantidadeCatalogo("1");
  };

  const adicionarProduto = () => {
    if (!produtoSelecionado) return;
    setItens((prev) => [...prev, criarItemProdutoOrcamento(produtoSelecionado, quantidadeProduto)]);
    setProdutoSelecionado(null);
    setQuantidadeProduto("1");
  };

  const adicionarDiaria = () => {
    if (!toNumber(diariaPreco) && !toNumber(diariaCusto)) return;
    setItens((prev) => [
      ...prev,
      criarItemDiariaOrcamento({
        nome: "Internação",
        custo_unitario_estimado: diariaCusto,
        preco_unitario: diariaPreco,
        dias: diasInternacao,
      }),
    ]);
  };

  const atualizarPrecoItem = (index, precoUnitario) => {
    setItens((prev) =>
      prev.map((item, idx) =>
        idx === index ? recalcularItemOrcamento(item, { preco_unitario: precoUnitario }) : item,
      ),
    );
  };

  const removerItem = (index) => {
    setItens((prev) => prev.filter((_, idx) => idx !== index));
  };

  const salvarOrcamento = async () => {
    if (!podeSalvar) return;
    setSalvando(true);
    setFeedback(null);
    const payload = {
      consulta_id: contexto?.consultaId || null,
      internacao_id: contexto?.internacaoId || null,
      pet_id: contexto?.petId || null,
      cliente_id: contexto?.clienteId || null,
      veterinario_id: contexto?.veterinarioId || null,
      titulo,
      status: "rascunho",
      previsao_dias_internacao: contexto?.internacaoId
        ? Math.max(Math.round(toNumber(diasInternacao)), 1)
        : null,
      itens,
    };

    try {
      const response = orcamentoId
        ? await vetApi.atualizarOrcamento(orcamentoId, payload)
        : await vetApi.criarOrcamento(payload);
      setOrcamentoId(response.data?.id ?? orcamentoId);
      setItens(Array.isArray(response.data?.itens) ? response.data.itens : itens);
      setFeedback({ tipo: "sucesso", texto: "Orçamento salvo." });
    } catch (error) {
      setFeedback({
        tipo: "erro",
        texto: error?.response?.data?.detail || "Erro ao salvar orçamento.",
      });
    } finally {
      setSalvando(false);
    }
  };

  return (
    <section className="rounded-xl border border-emerald-100 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-emerald-700">
            <Calculator size={18} />
            <h2 className="font-semibold text-gray-800">{titulo}</h2>
          </div>
          <p className="mt-1 text-xs text-gray-500">
            Custo {formatMoneyBRL(totais.custo_total_estimado)} · Venda{" "}
            {formatMoneyBRL(totais.preco_total)} · Margem {formatMoneyBRL(totais.margem_valor)} (
            {formatPercent(totais.margem_percentual)})
          </p>
        </div>
        <button
          type="button"
          onClick={salvarOrcamento}
          disabled={!podeSalvar || salvando || carregando}
          className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
        >
          <Save size={15} />
          {salvando ? "Salvando..." : "Salvar"}
        </button>
      </div>

      {feedback && (
        <p
          className={`mt-3 rounded-lg px-3 py-2 text-xs ${feedback.tipo === "erro" ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700"}`}
        >
          {feedback.texto}
        </p>
      )}

      <div className="mt-4 grid gap-3 md:grid-cols-[1.2fr_120px_auto]">
        <select
          value={catalogoId}
          onChange={(event) => setCatalogoId(event.target.value)}
          disabled={modoSomenteLeitura}
          className={selectClass}
        >
          <option value="">Procedimento do catálogo</option>
          {procedimentosCatalogo.map((item) => (
            <option key={item.id} value={item.id}>
              {item.nome}
            </option>
          ))}
        </select>
        <input
          type="number"
          min="0.01"
          step="0.01"
          value={quantidadeCatalogo}
          onChange={(event) => setQuantidadeCatalogo(event.target.value)}
          disabled={modoSomenteLeitura}
          className={inputClass}
        />
        <button
          type="button"
          onClick={adicionarCatalogo}
          disabled={!catalogoSelecionado || modoSomenteLeitura}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-emerald-200 px-3 py-2 text-sm font-medium text-emerald-700 hover:bg-emerald-50 disabled:opacity-50"
        >
          <Plus size={15} />
          Procedimento
        </button>
      </div>

      <div className="mt-3 grid gap-3 md:grid-cols-[1.2fr_120px_auto]">
        <ProdutoEstoqueAutocomplete
          selectedProduct={produtoSelecionado}
          onSelect={setProdutoSelecionado}
          helperText=""
        />
        <input
          type="number"
          min="0.01"
          step="0.01"
          value={quantidadeProduto}
          onChange={(event) => setQuantidadeProduto(event.target.value)}
          disabled={modoSomenteLeitura}
          className={`${inputClass} self-end`}
        />
        <button
          type="button"
          onClick={adicionarProduto}
          disabled={!produtoSelecionado || modoSomenteLeitura}
          className="inline-flex items-center justify-center gap-2 self-end rounded-lg border border-emerald-200 px-3 py-2 text-sm font-medium text-emerald-700 hover:bg-emerald-50 disabled:opacity-50"
        >
          <Plus size={15} />
          Produto
        </button>
      </div>

      {contexto?.internacaoId && (
        <div className="mt-3 grid gap-3 md:grid-cols-[120px_1fr_1fr_auto]">
          <input
            type="number"
            min="1"
            step="1"
            value={diasInternacao}
            onChange={(event) => setDiasInternacao(event.target.value)}
            disabled={modoSomenteLeitura}
            className={inputClass}
            aria-label="Dias previstos"
          />
          <input
            type="text"
            value={diariaCusto}
            onChange={(event) => setDiariaCusto(event.target.value)}
            disabled={modoSomenteLeitura}
            className={inputClass}
            placeholder="Custo da diária"
          />
          <input
            type="text"
            value={diariaPreco}
            onChange={(event) => setDiariaPreco(event.target.value)}
            disabled={modoSomenteLeitura}
            className={inputClass}
            placeholder="Preço da diária"
          />
          <button
            type="button"
            onClick={adicionarDiaria}
            disabled={modoSomenteLeitura}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-emerald-200 px-3 py-2 text-sm font-medium text-emerald-700 hover:bg-emerald-50 disabled:opacity-50"
          >
            <Plus size={15} />
            Diária
          </button>
        </div>
      )}

      <div className="mt-4 space-y-2">
        {itens.length === 0 ? (
          <p className="text-xs text-gray-400">Nenhum item no orçamento.</p>
        ) : (
          itens.map((item, index) => (
            <div
              key={`${item.origem}_${item.catalogo_id || item.produto_id || index}`}
              className="grid gap-2 rounded-lg border border-gray-100 bg-gray-50 p-3 md:grid-cols-[1fr_110px_110px_44px]"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-gray-800">{item.nome}</p>
                <p className="text-xs text-gray-500">
                  Qtd. {Number(item.quantidade || 0).toLocaleString("pt-BR")} {item.unidade || ""} ·
                  Custo {formatMoneyBRL(item.custo_total_estimado)} · Margem{" "}
                  {formatMoneyBRL(item.margem_valor)}
                </p>
              </div>
              <p className="self-center text-sm font-semibold text-gray-700">
                {formatMoneyBRL(item.preco_total)}
              </p>
              <input
                type="text"
                value={item.preco_unitario}
                onChange={(event) => atualizarPrecoItem(index, event.target.value)}
                disabled={modoSomenteLeitura}
                className={inputClass}
                aria-label={`Preço unitário de ${item.nome}`}
              />
              <button
                type="button"
                onClick={() => removerItem(index)}
                disabled={modoSomenteLeitura}
                className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-gray-200 text-gray-500 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                aria-label={`Remover ${item.nome}`}
              >
                <Trash2 size={15} />
              </button>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
