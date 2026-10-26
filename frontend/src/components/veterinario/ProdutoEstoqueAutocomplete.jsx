import { useEffect, useMemo, useState } from "react";
import BuscaProduto from "../v2/BuscaProduto/BuscaProduto";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import { vetApi } from "../../pages/veterinario/vetApi";

export default function ProdutoEstoqueAutocomplete({
  label = "Insumo / produto",
  placeholder = "Digite nome ou código do insumo...",
  selectedProduct,
  onSelect,
  helperText = "",
  searchProducts,
  disabled = false,
}) {
  const [busca, setBusca] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [sugestoes, setSugestoes] = useState([]);

  useEffect(() => {
    let ativo = true;
    if (disabled) {
      setSugestoes([]);
      return;
    }
    if (selectedProduct?.id) return;
    const termo = busca.trim();
    if (termo.length < 1) {
      setSugestoes([]);
      return;
    }

    const timer = setTimeout(async () => {
      setCarregando(true);
      try {
        const res = searchProducts
          ? await searchProducts(termo)
          : await vetApi.listarProdutosEstoque(termo);
        const lista = Array.isArray(res.data) ? res.data : (res.data?.items ?? []);
        if (ativo) setSugestoes(lista.slice(0, 20));
      } catch {
        if (ativo) setSugestoes([]);
      } finally {
        if (ativo) setCarregando(false);
      }
    }, 250);

    return () => {
      ativo = false;
      clearTimeout(timer);
    };
  }, [busca, disabled, selectedProduct, searchProducts]);

  const estoqueLabel = useMemo(() => {
    if (!selectedProduct) return "";
    const estoque = Number(selectedProduct.estoque_atual || 0);
    return `${estoque.toLocaleString("pt-BR")} ${selectedProduct.unidade || "un"} em estoque`;
  }, [selectedProduct]);

  return (
    <div className="space-y-2">
      <label className="block text-xs font-medium text-gray-600">{label}</label>

      {selectedProduct ? (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-emerald-900">{selectedProduct.nome}</p>
              <p className="text-xs text-emerald-700">
                Código: {selectedProduct.codigo || "—"} • {estoqueLabel}
              </p>
              <p className="text-xs text-emerald-700">
                Custo un.:{" "}
                {Number(selectedProduct.preco_custo || 0).toLocaleString("pt-BR", {
                  style: "currency",
                  currency: "BRL",
                })}
              </p>
            </div>
            <BotaoInteracao
              tamanho="pequeno"
              type="button"
              onClick={() => {
                onSelect?.(null);
                setBusca("");
                setSugestoes([]);
              }}
              disabled={disabled}
              className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 bg-white px-2 py-1 text-xs text-emerald-700 hover:bg-emerald-100 disabled:opacity-50"
            >
              Trocar
            </BotaoInteracao>
          </div>
        </div>
      ) : (
        <>
          <BuscaProduto
            value={busca}
            onChange={setBusca}
            disabled={disabled}
            placeholder={placeholder}
            suggestions={sugestoes}
            showSuggestions
            loading={carregando}
            onSelect={(produto) => {
              onSelect?.(produto);
              setBusca(produto.nome || "");
              setSugestoes([]);
            }}
          />

          {helperText ? <p className="text-xs text-gray-500">{helperText}</p> : null}

          {!carregando && sugestoes.length === 0 && busca.trim().length >= 1 ? (
            <p className="text-xs text-amber-600">Nenhum insumo encontrado para essa busca.</p>
          ) : null}
        </>
      )}
    </div>
  );
}
