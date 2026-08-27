import { CheckCircle2, PackageSearch, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import { getFornecedoresProduto, getProdutosVendaveis } from "../../api/produtos";
import CurrencyInput from "../CurrencyInput";

function nomeFornecedor(fornecedor) {
  return fornecedor?.nome_fantasia || fornecedor?.razao_social || fornecedor?.nome || "";
}

function encontrarPorNome(lista, nome, obterNome = (item) => item?.nome) {
  const normalizado = String(nome || "")
    .trim()
    .toLocaleLowerCase("pt-BR");
  if (!normalizado) return null;
  return (
    lista.find(
      (item) =>
        String(obterNome(item) || "")
          .trim()
          .toLocaleLowerCase("pt-BR") === normalizado,
    ) || null
  );
}

export default function NaoVendaItemEditor({
  item,
  marcas,
  fornecedores,
  podeRemover,
  onChange,
  onRemove,
}) {
  const [sugestoes, setSugestoes] = useState([]);
  const [buscando, setBuscando] = useState(false);

  useEffect(() => {
    const termo = String(item.produto_nome || "").trim();
    if (item.produto_id || termo.length < 2) {
      setSugestoes([]);
      return undefined;
    }

    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        setBuscando(true);
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
      } catch (error) {
        if (error?.code !== "ERR_CANCELED") setSugestoes([]);
      } finally {
        setBuscando(false);
      }
    }, 300);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [item.produto_id, item.produto_nome]);

  const selecionarProduto = async (produto) => {
    onChange({
      produto_id: produto.id,
      produto_nome: produto.nome,
      sku: produto.codigo || "",
      marca_id: produto.marca_id || produto.marca?.id || null,
      marca_nome: produto.marca?.nome || "",
      valor_unitario_estimado:
        Number(produto.preco_venda_pdv ?? produto.preco_venda_efetivo ?? produto.preco_venda) || 0,
    });
    setSugestoes([]);

    try {
      const response = await getFornecedoresProduto(produto.id);
      const vinculos = Array.isArray(response.data) ? response.data : response.data?.items || [];
      const vinculo = vinculos.find((opcao) => opcao.e_principal) || vinculos[0];
      if (vinculo) {
        onChange({
          fornecedor_id: vinculo.fornecedor_id || vinculo.fornecedor?.id || null,
          fornecedor_nome:
            vinculo.fornecedor_nome || nomeFornecedor(vinculo.fornecedor) || vinculo.nome || "",
        });
      }
    } catch {
      // O fornecedor continua opcional e pode ser informado manualmente.
    }
  };

  const alterarNomeProduto = (produto_nome) => {
    onChange({
      produto_id: null,
      produto_nome,
      sku: "",
    });
  };

  const alterarMarca = (marca_nome) => {
    const marca = encontrarPorNome(marcas, marca_nome);
    onChange({ marca_nome, marca_id: marca?.id || null });
  };

  const alterarFornecedor = (fornecedor_nome) => {
    const fornecedor = encontrarPorNome(fornecedores, fornecedor_nome, nomeFornecedor);
    onChange({ fornecedor_nome, fornecedor_id: fornecedor?.id || null });
  };

  return (
    <div className="relative rounded-xl border border-slate-200 bg-slate-50 p-3">
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <PackageSearch className="h-4 w-4 text-blue-600" />
          <span className="text-sm font-semibold text-slate-800">Produto procurado</span>
          {item.produto_id && (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
              <CheckCircle2 className="h-3 w-3" /> Cadastrado
            </span>
          )}
        </div>
        {podeRemover && (
          <button
            type="button"
            onClick={onRemove}
            className="rounded p-1 text-slate-400 hover:bg-red-50 hover:text-red-600"
            title="Remover produto deste registro"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>

      <div className="grid gap-3 md:grid-cols-12">
        <label className="relative md:col-span-6">
          <span className="mb-1 block text-xs font-medium text-slate-600">
            Produto ou descrição livre
          </span>
          <input
            value={item.produto_nome}
            onChange={(event) => alterarNomeProduto(event.target.value)}
            placeholder="Busque no catálogo ou escreva o que o cliente pediu"
            className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
          {buscando && (
            <span className="absolute right-3 top-8 text-xs text-slate-400">Buscando...</span>
          )}
          {sugestoes.length > 0 && (
            <div className="absolute z-30 mt-1 max-h-56 w-full overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-xl">
              {sugestoes.map((produto) => (
                <button
                  key={produto.id}
                  type="button"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => selecionarProduto(produto)}
                  className="block w-full border-b border-slate-100 px-3 py-2 text-left last:border-0 hover:bg-blue-50"
                >
                  <p className="text-sm font-medium text-slate-800">{produto.nome}</p>
                  <p className="text-xs text-slate-500">
                    SKU {produto.codigo || "não informado"}
                    {produto.marca?.nome ? ` • ${produto.marca.nome}` : ""}
                  </p>
                </button>
              ))}
            </div>
          )}
        </label>

        <label className="md:col-span-3">
          <span className="mb-1 block text-xs font-medium text-slate-600">Marca opcional</span>
          <input
            list={`marcas-nao-venda-${item.chave}`}
            value={item.marca_nome}
            onChange={(event) => alterarMarca(event.target.value)}
            placeholder="Marca"
            className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
          <datalist id={`marcas-nao-venda-${item.chave}`}>
            {marcas.map((marca) => (
              <option key={marca.id} value={marca.nome} />
            ))}
          </datalist>
        </label>

        <label className="md:col-span-3">
          <span className="mb-1 block text-xs font-medium text-slate-600">Fornecedor opcional</span>
          <input
            list={`fornecedores-nao-venda-${item.chave}`}
            value={item.fornecedor_nome}
            onChange={(event) => alterarFornecedor(event.target.value)}
            placeholder="Fornecedor"
            className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
          <datalist id={`fornecedores-nao-venda-${item.chave}`}>
            {fornecedores.map((fornecedor) => (
              <option key={fornecedor.id} value={nomeFornecedor(fornecedor)} />
            ))}
          </datalist>
        </label>

        <label className="md:col-span-2">
          <span className="mb-1 block text-xs font-medium text-slate-600">Quantidade</span>
          <input
            type="number"
            min="0.0001"
            step="any"
            value={item.quantidade}
            onChange={(event) =>
              onChange({ quantidade: Math.max(Number(event.target.value) || 0, 0) })
            }
            className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
        </label>

        <label className="md:col-span-3">
          <span className="mb-1 block text-xs font-medium text-slate-600">
            Valor unitário estimado
          </span>
          <CurrencyInput
            value={item.valor_unitario_estimado}
            onChange={(valor) => onChange({ valor_unitario_estimado: valor })}
            className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
        </label>

        <div className="flex items-end md:col-span-7">
          <p className="pb-2 text-xs text-slate-500">
            Se não existir no catálogo, deixe como texto livre. Isso não cria um produto no estoque.
          </p>
        </div>
      </div>
    </div>
  );
}
