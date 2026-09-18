import { useEffect, useRef, useState } from "react";
import { Trash2 } from "lucide-react";

import { getProdutosVendaveis } from "../../api/produtos";
import CurrencyInput from "../../components/CurrencyInput";
import ProdutoSelector from "../../components/produtos/ProdutoSelector";
import { formatMoneyBRL } from "../../utils/formatters";
import { preencherItemComProduto } from "./orcamentosGrupoUtils";

const inputClass =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100";

function estoqueProduto(produto) {
  if (produto?.controlar_estoque === false || produto?.tipo === "servico") return "Serviço";
  const estoque =
    produto?.tipo_produto === "KIT" && produto?.tipo_kit === "VIRTUAL"
      ? produto?.estoque_virtual
      : produto?.estoque_atual;
  return `Estoque: ${Number(estoque || 0).toLocaleString("pt-BR")} ${produto?.unidade || "un"}`;
}

export default function OrcamentoGrupoItemRow({ item, podeRemover, onAtualizar, onRemover }) {
  const [sugestoes, setSugestoes] = useState([]);
  const [mostrarSugestoes, setMostrarSugestoes] = useState(false);
  const [carregando, setCarregando] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    const termo = String(item.descricao || "").trim();
    if (item.produto_id || termo.length < 2) {
      setSugestoes([]);
      setCarregando(false);
      return undefined;
    }

    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setCarregando(true);
      try {
        const response = await getProdutosVendaveis(
          {
            busca: termo,
            page_size: 8,
            contar_total: false,
            incluir_imagens: false,
          },
          { signal: controller.signal },
        );
        setSugestoes(response.data?.items || []);
        setMostrarSugestoes(true);
      } catch (error) {
        if (error?.code !== "ERR_CANCELED" && error?.name !== "CanceledError") {
          setSugestoes([]);
        }
      } finally {
        if (!controller.signal.aborted) setCarregando(false);
      }
    }, 300);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [item.descricao, item.produto_id]);

  useEffect(() => {
    function fecharAoClicarFora(event) {
      if (!containerRef.current?.contains(event.target)) setMostrarSugestoes(false);
    }
    document.addEventListener("mousedown", fecharAoClicarFora);
    return () => document.removeEventListener("mousedown", fecharAoClicarFora);
  }, []);

  function alterarDescricao(valor) {
    onAtualizar({ descricao: valor, produto_id: null });
    setMostrarSugestoes(String(valor || "").trim().length >= 2);
  }

  function selecionarProduto(produto) {
    onAtualizar(preencherItemComProduto(item, produto));
    setSugestoes([]);
    setMostrarSugestoes(false);
  }

  return (
    <div className="grid gap-3 rounded-xl border border-slate-200 p-3 md:grid-cols-[minmax(260px,1fr)_110px_100px_150px_42px] dark:border-slate-800">
      <div className="min-w-0 text-xs text-slate-500">
        <span>Descrição</span>
        <ProdutoSelector
          className="mt-1"
          containerRef={containerRef}
          inputClassName="h-10 border-slate-300 bg-white text-slate-900 focus:border-teal-500 focus:ring-teal-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
          minChars={2}
          onChange={alterarDescricao}
          onFocus={() => setMostrarSugestoes(sugestoes.length > 0)}
          onSelect={selecionarProduto}
          placeholder="Digite nome, SKU ou código de barras..."
          renderSuggestion={(produto) => (
            <button
              key={produto.id}
              type="button"
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => selecionarProduto(produto)}
              className="flex w-full items-center justify-between gap-3 border-b border-slate-100 px-4 py-3 text-left last:border-b-0 hover:bg-teal-50 dark:border-slate-800 dark:hover:bg-slate-800"
            >
              <span className="min-w-0">
                <span className="block truncate font-medium text-slate-900 dark:text-slate-100">
                  {produto.nome}
                </span>
                <span className="block text-xs text-slate-500">
                  {produto.codigo ? `Cód: ${produto.codigo} · ` : ""}
                  {estoqueProduto(produto)}
                </span>
              </span>
              <span className="shrink-0 font-semibold text-emerald-700 dark:text-emerald-300">
                {formatMoneyBRL(
                  produto.preco_venda_pdv ?? produto.preco_venda_efetivo ?? produto.preco_venda,
                )}
              </span>
            </button>
          )}
          showSuggestions={mostrarSugestoes}
          suggestions={sugestoes}
          value={item.descricao}
        />
        {carregando ? (
          <span className="mt-1 block text-slate-400">Buscando produtos...</span>
        ) : null}
        {item.produto_id ? (
          <span className="mt-1 block text-teal-700 dark:text-teal-300">
            Produto do estoque selecionado. Você ainda pode ajustar os campos.
          </span>
        ) : null}
      </div>
      <label className="text-xs text-slate-500">
        Quantidade
        <input
          className={`${inputClass} mt-1`}
          type="number"
          min="0.001"
          step="0.001"
          value={item.quantidade}
          onChange={(event) => onAtualizar({ quantidade: event.target.value })}
          required
        />
      </label>
      <label className="text-xs text-slate-500">
        Unidade
        <input
          className={`${inputClass} mt-1`}
          value={item.unidade}
          onChange={(event) => onAtualizar({ unidade: event.target.value })}
        />
      </label>
      <label className="text-xs text-slate-500">
        Preço unitário
        <CurrencyInput
          className={`${inputClass} mt-1`}
          value={item.preco_unitario_base}
          onChange={(value) => onAtualizar({ preco_unitario_base: value })}
        />
      </label>
      <button
        type="button"
        onClick={onRemover}
        disabled={!podeRemover}
        className="mt-5 flex h-10 w-10 items-center justify-center rounded-lg text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-30"
        aria-label="Remover item"
      >
        <Trash2 size={17} />
      </button>
    </div>
  );
}
