import { buscarProdutoPorBarcode, listarProdutos } from "./shop.service";
import { Produto } from "../types";

export async function buscarProdutosFuncionario(busca: string): Promise<Produto[]> {
  const termo = busca.trim();
  if (termo.length > 0 && termo.length < 2) return [];

  const { produtos } = await listarProdutos({
    busca: termo || undefined,
    somenteComEstoque: false,
    ordenacao: "nome",
    cacheBust: Date.now(),
  });

  return produtos;
}

export async function buscarProdutoPorBarcodeFuncionario(barcode: string): Promise<Produto | null> {
  return buscarProdutoPorBarcode(barcode);
}
