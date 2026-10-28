import { normalizeMarkdownContent } from "../../utils/safeMarkdown.js";
import { dataHoraIfoodParaFormulario } from "../produto/ifoodProdutoDates.js";

const texto = (value) => String(value ?? "").trim();
const numero = (value) => (value === "" || value == null ? null : Number(value));

// Compara o cadastro em edição com uma consulta salva, nunca com o primeiro
// render da seção (a seção pode montar depois de o usuário já ter editado).
export function assinaturaCadastroIfood(produto, { formulario = false, imagens } = {}) {
  if (!produto) return null;
  const data = (value) => (formulario ? texto(value) : dataHoraIfoodParaFormulario(value));
  const imagem = imagens
    ? imagens.find((item) => item.principal || item.e_principal)?.url ||
      imagens[0]?.url ||
      produto.imagem_principal
    : produto.imagem_principal;
  return JSON.stringify({
    codigo: texto(produto.codigo || produto.sku),
    nome: texto(produto.nome),
    codigo_barras: texto(produto.codigo_barras),
    gtin_ean: texto(produto.gtin_ean),
    descricao: normalizeMarkdownContent(formulario ? produto.descricao : produto.descricao_curta),
    descricao_completa: texto(produto.descricao_completa),
    imagem: texto(imagem),
    unidade: texto(produto.unidade || "UN"),
    categoria: numero(produto.categoria_id),
    departamento: numero(produto.departamento_id),
    marca: numero(produto.marca_id),
    subcategoria: texto(produto.subcategoria),
    tipo: texto(produto.tipo || "produto"),
    tipo_produto: texto(produto.tipo_produto || "SIMPLES"),
    tipo_kit: texto(produto.tipo_kit),
    e_kit_fisico: Boolean(produto.e_kit_fisico),
    e_granel: Boolean(produto.e_granel),
    composicao: (produto.composicao_kit || []).map((item) => ({
      produto: numero(item.produto_componente_id || item.produto_id),
      quantidade: numero(item.quantidade),
      opcional: Boolean(item.opcional),
    })),
    ativo: produto.ativo !== false,
    situacao: produto.situacao !== false,
    selecionado: Boolean(produto.anunciar_ifood),
    pausado: Boolean(produto.ifood_pausado),
    custo: numero(produto.preco_custo) ?? 0,
    preco: numero(produto.preco_venda),
    preco_ifood: numero(produto.preco_ifood),
    promocao: numero(produto.preco_ifood_promo),
    inicio: data(produto.preco_ifood_promo_inicio),
    fim: data(produto.preco_ifood_promo_fim),
  });
}

export function cadastroIfoodAlterado(rascunho, salvo, imagens) {
  if (!rascunho) return false;
  if (!salvo) return true;
  return (
    assinaturaCadastroIfood(rascunho, { formulario: true, imagens }) !==
    assinaturaCadastroIfood(salvo)
  );
}

export function valorConferidoPortal(value, decimals) {
  if (value === null || value === undefined || String(value).trim() === "")
    return { valid: true, value: null };
  const text = String(value).trim().replace(",", ".");
  const valid =
    new RegExp(`^\\d+(?:\\.\\d{1,${decimals}})?$`).test(text) && Number.isFinite(Number(text));
  return { valid, value: valid ? (typeof value === "number" ? value : text) : null };
}
