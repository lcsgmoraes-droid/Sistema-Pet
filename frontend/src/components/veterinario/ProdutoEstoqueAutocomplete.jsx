import { useEffect, useMemo, useState } from "react";
import { PackageSearch, X } from "lucide-react";
import { vetApi } from "../../pages/veterinario/vetApi";

export default function ProdutoEstoqueAutocomplete({
  label = "Insumo / produto",
  placeholder = "Digite nome ou código do insumo...",
  selectedProduct,
  onSelect,
  helperText = "",
}) {
  const [busca, setBusca] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [sugestoes, setSugestoes] = useState([]);

  useEffect(() => {
    if (selectedProduct?.id) return;
    const termo = busca.trim();
    if (termo.length < 2) {
      setSugestoes([]);
      return;
    }

    const timer = setTimeout(async () => {
      setCarregando(true);
      try {
        const res = await vetApi.listarProdutosEstoque(termo);
        const lista = Array.isArray(res.data) ? res.data : (res.data?.items ?? []);
        setSugestoes(lista.slice(0, 8));
      } catch {
        setSugestoes([]);
      } finally {
        setCarregando(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [busca, selectedProduct]);

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
                Custo un.: {(Number(selectedProduct.preco_custo || 0)).toLocaleString("pt-BR", {
                  style: "currency",
                  currency: "BRL",
                })}
              </p>
            </div>
            <button
              type="button"
              onClick={() => {
                onSelect?.(null);
                setBusca("");
                setSugestoes([]);
              }}
              className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 bg-white px-2 py-1 text-xs text-emerald-700 hover:bg-emerald-100"
            >
              <X size={12} />
              Trocar
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="relative">
            <PackageSearch size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder={placeholder}
              className="w-full rounded-lg border border-gray-200 px-10 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-300"
            />
          </div>

          {helperText ? <p className="text-xs text-gray-500">{helperText}</p> : null}

          {carregando ? (
            <p className="text-xs text-gray-400">Buscando insumos...</p>
          ) : sugestoes.length > 0 ? (
            <div className="max-h-52 space-y-2 overflow-auto rounded-xl border border-gray-200 bg-white p-2">
              {sugestoes.map((produto) => (
                <button
                  key={produto.id}
                  type="button"
                  onClick={() => {
                    onSelect?.(produto);
                    setBusca(produto.nome || "");
                    setSugestoes([]);
                  }}
                  className="w-full rounded-lg border border-gray-100 px-3 py-2 text-left hover:bg-emerald-50"
                >
                  <p className="text-sm font-medium text-gray-800">{produto.nome}</p>
                  <p className="text-xs text-gray-500">
                    Código: {produto.codigo || "—"} • Estoque: {Number(produto.estoque_atual || 0).toLocaleString("pt-BR")} {produto.unidade || "un"}
                  </p>
                </button>
              ))}
            </div>
          ) : busca.trim().length >= 2 ? (
            <p className="text-xs text-amber-600">Nenhum insumo encontrado para essa busca.</p>
          ) : null}
        </>
      )}
    </div>
  );
}
