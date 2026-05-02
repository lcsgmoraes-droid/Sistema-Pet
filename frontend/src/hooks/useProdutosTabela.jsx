import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { formatarData } from "../api/produtos";
import { obterEstoqueVisualProduto } from "../components/produtos/produtosUtils";

const normalizeExpandId = (value) => String(value ?? "");
const PRODUTOS_COLUNAS_STORAGE_KEY = "produtos_colunas_visiveis";
const PRODUTOS_COLUNAS_VERSION_KEY = "produtos_colunas_visiveis_version";
const PRODUTOS_COLUNAS_VERSION = 2;
const COLUNAS_PADRAO_MIGRACAO = ["margem", "canais"];

function carregarColunasVisiveisSalvas(colunasTabela) {
  const salvo = localStorage.getItem(PRODUTOS_COLUNAS_STORAGE_KEY);
  if (!salvo) return null;

  try {
    const parsed = JSON.parse(salvo);
    if (!Array.isArray(parsed)) return null;

    const colunasConhecidas = new Set(colunasTabela.map((coluna) => coluna.key));
    const normalizadas = parsed.filter((key) => colunasConhecidas.has(key));
    const versaoSalva = Number(
      localStorage.getItem(PRODUTOS_COLUNAS_VERSION_KEY) || 1,
    );

    if (versaoSalva < PRODUTOS_COLUNAS_VERSION) {
      COLUNAS_PADRAO_MIGRACAO.forEach((key) => {
        const coluna = colunasTabela.find((item) => item.key === key);
        if (coluna?.visible === true && !normalizadas.includes(key)) {
          normalizadas.push(key);
        }
      });
    }

    return normalizadas.length > 0 ? normalizadas : null;
  } catch {
    return null;
  }
}

export default function useProdutosTabela({
  colunasTabela,
  paisExpandidos: paisExpandidosExterno,
  produtosVisiveisRef,
  setPaisExpandidos: setPaisExpandidosExterno,
}) {
  const linhaProdutoRefs = useRef({});
  const [kitsExpandidos, setKitsExpandidos] = useState([]);
  const [paisExpandidosInterno, setPaisExpandidosInterno] = useState([]);
  const [colunasVisiveis, setColunasVisiveis] = useState(() => {
    return carregarColunasVisiveisSalvas(colunasTabela);
  });
  const [modalColunas, setModalColunas] = useState(false);
  const [colunasTemporarias, setColunasTemporarias] = useState([]);
  const paisExpandidos = paisExpandidosExterno ?? paisExpandidosInterno;
  const setPaisExpandidos = setPaisExpandidosExterno ?? setPaisExpandidosInterno;

  useEffect(() => {
    const versaoSalva = Number(
      localStorage.getItem(PRODUTOS_COLUNAS_VERSION_KEY) || 0,
    );

    if (versaoSalva >= PRODUTOS_COLUNAS_VERSION) return;

    if (colunasVisiveis) {
      localStorage.setItem(
        PRODUTOS_COLUNAS_STORAGE_KEY,
        JSON.stringify(colunasVisiveis),
      );
    }
    localStorage.setItem(
      PRODUTOS_COLUNAS_VERSION_KEY,
      String(PRODUTOS_COLUNAS_VERSION),
    );
  }, [colunasVisiveis]);

  const getCorEstoque = (produto) => {
    if (!produto.controlar_estoque) return "text-gray-500";

    const estoque = obterEstoqueVisualProduto(produto);
    const minimo = produto.estoque_minimo || 0;

    if (estoque <= 0) return "text-red-600 font-semibold";
    if (estoque <= minimo) return "text-yellow-600 font-medium";
    return "text-gray-700";
  };

  const getValidadeMaisProxima = (produto) => {
    if (!produto.lotes || produto.lotes.length === 0) return "-";

    const lotes = produto.lotes
      .filter((lote) => lote.data_validade)
      .sort((a, b) => new Date(a.data_validade) - new Date(b.data_validade));

    if (lotes.length === 0) return "-";

    const proximaValidade = lotes[0].data_validade;
    const dias = Math.floor(
      (new Date(proximaValidade) - new Date()) / (1000 * 60 * 60 * 24),
    );

    let cor = "text-gray-700";
    if (dias < 0) cor = "text-red-600 font-bold";
    else if (dias <= 30) cor = "text-orange-600 font-semibold";
    else if (dias <= 90) cor = "text-yellow-600";

    return <span className={cor}>{formatarData(proximaValidade)}</span>;
  };

  const garantirLinhaVisivel = (produtoId) => {
    const linha = linhaProdutoRefs.current[produtoId];
    if (!linha) return;

    linha.scrollIntoView({
      behavior: "smooth",
      block: "center",
      inline: "nearest",
    });
  };

  const garantirGrupoPaiVisivel = (produtoId) => {
    const produtosVisiveis = produtosVisiveisRef?.current || [];
    const variacoesVisiveis = produtosVisiveis.filter(
      (produto) =>
        produto.tipo_produto === "VARIACAO" && produto.produto_pai_id === produtoId,
    );

    const ultimoProdutoVisivel =
      variacoesVisiveis[variacoesVisiveis.length - 1] ||
      produtosVisiveis.find((produto) => produto.id === produtoId);

    if (!ultimoProdutoVisivel) {
      garantirLinhaVisivel(produtoId);
      return;
    }

    const linha = linhaProdutoRefs.current[ultimoProdutoVisivel.id];
    if (!linha) {
      garantirLinhaVisivel(produtoId);
      return;
    }

    linha.scrollIntoView({
      behavior: "smooth",
      block: variacoesVisiveis.length > 0 ? "end" : "center",
      inline: "nearest",
    });
  };

  const toggleKitExpandido = (produtoId) => {
    const produtoIdNormalizado = normalizeExpandId(produtoId);
    const vaiExpandir = !kitsExpandidos.includes(produtoIdNormalizado);
    setKitsExpandidos((prev) =>
      prev.includes(produtoIdNormalizado)
        ? prev.filter((id) => id !== produtoIdNormalizado)
        : [...prev, produtoIdNormalizado],
    );

    if (vaiExpandir) {
      setTimeout(() => garantirLinhaVisivel(produtoId), 80);
    }
  };

  const togglePaiExpandido = (produtoId) => {
    const produtoIdNormalizado = normalizeExpandId(produtoId);
    const vaiExpandir = !paisExpandidos.includes(produtoIdNormalizado);
    setPaisExpandidos((prev) =>
      prev.includes(produtoIdNormalizado)
        ? prev.filter((id) => id !== produtoIdNormalizado)
        : [...prev, produtoIdNormalizado],
    );

    if (vaiExpandir) {
      setTimeout(() => garantirGrupoPaiVisivel(produtoId), 120);
    }
  };

  const abrirModalColunas = () => {
    const keys = colunasVisiveis || colunasTabela.map((coluna) => coluna.key);
    setColunasTemporarias(keys);
    setModalColunas(true);
  };

  const toggleColuna = (key) => {
    setColunasTemporarias((prev) =>
      prev.includes(key) ? prev.filter((currentKey) => currentKey !== key) : [...prev, key],
    );
  };

  const salvarColunas = () => {
    localStorage.setItem(
      PRODUTOS_COLUNAS_STORAGE_KEY,
      JSON.stringify(colunasTemporarias),
    );
    localStorage.setItem(
      PRODUTOS_COLUNAS_VERSION_KEY,
      String(PRODUTOS_COLUNAS_VERSION),
    );
    setColunasVisiveis(colunasTemporarias);
    setModalColunas(false);
    toast.success("Preferencias de colunas salvas!");
  };

  const restaurarColunasPadrao = () => {
    localStorage.removeItem(PRODUTOS_COLUNAS_STORAGE_KEY);
    localStorage.setItem(
      PRODUTOS_COLUNAS_VERSION_KEY,
      String(PRODUTOS_COLUNAS_VERSION),
    );
    setColunasVisiveis(null);
    setColunasTemporarias(colunasTabela.map((coluna) => coluna.key));
    toast.success("Colunas restauradas para o padrao!");
  };

  const filtrarColunas = (coluna) => {
    if (!colunasVisiveis) return true;
    return colunasVisiveis.includes(coluna.key);
  };

  const resetPaisExpandidos = () => setPaisExpandidos([]);

  return {
    abrirModalColunas,
    colunasTemporarias,
    colunasVisiveis,
    filtrarColunas,
    getCorEstoque,
    getValidadeMaisProxima,
    kitsExpandidos,
    linhaProdutoRefs,
    modalColunas,
    onCloseModalColunas: () => setModalColunas(false),
    paisExpandidos,
    resetPaisExpandidos,
    restaurarColunasPadrao,
    salvarColunas,
    toggleColuna,
    toggleKitExpandido,
    togglePaiExpandido,
  };
}
