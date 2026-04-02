import { useRef, useState } from "react";
import toast from "react-hot-toast";
import { formatarData } from "../api/produtos";
import { obterEstoqueVisualProduto } from "../components/produtos/produtosUtils";

export default function useProdutosTabela({ colunasTabela, produtosVisiveisRef }) {
  const linhaProdutoRefs = useRef({});
  const [kitsExpandidos, setKitsExpandidos] = useState([]);
  const [paisExpandidos, setPaisExpandidos] = useState([]);
  const [colunasVisiveis, setColunasVisiveis] = useState(() => {
    const salvo = localStorage.getItem("produtos_colunas_visiveis");
    return salvo ? JSON.parse(salvo) : null;
  });
  const [modalColunas, setModalColunas] = useState(false);
  const [colunasTemporarias, setColunasTemporarias] = useState([]);

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
    const vaiExpandir = !kitsExpandidos.includes(produtoId);
    setKitsExpandidos((prev) =>
      prev.includes(produtoId)
        ? prev.filter((id) => id !== produtoId)
        : [...prev, produtoId],
    );

    if (vaiExpandir) {
      setTimeout(() => garantirLinhaVisivel(produtoId), 80);
    }
  };

  const togglePaiExpandido = (produtoId) => {
    const vaiExpandir = !paisExpandidos.includes(produtoId);
    setPaisExpandidos((prev) =>
      prev.includes(produtoId)
        ? prev.filter((id) => id !== produtoId)
        : [...prev, produtoId],
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
      "produtos_colunas_visiveis",
      JSON.stringify(colunasTemporarias),
    );
    setColunasVisiveis(colunasTemporarias);
    setModalColunas(false);
    toast.success("Preferencias de colunas salvas!");
  };

  const restaurarColunasPadrao = () => {
    localStorage.removeItem("produtos_colunas_visiveis");
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
