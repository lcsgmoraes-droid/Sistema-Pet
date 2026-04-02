import { useEffect, useMemo, useRef, useState } from "react";
import { getProdutos } from "../api/produtos";

export default function useProdutosListagem({
  normalizeSearchText,
  onOcultarPaisVariacoes,
  paisExpandidos,
}) {
  const [persistirBusca, setPersistirBusca] = useState(() => {
    const salvo = localStorage.getItem("produtos_persistir_busca");
    return salvo === null ? true : salvo === "true";
  });
  const [produtosBrutos, setProdutosBrutos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selecionados, setSelecionados] = useState([]);
  const [ultimoSelecionado, setUltimoSelecionado] = useState(null);
  const [filtros, setFiltros] = useState({
    busca: (() => {
      if (!persistirBusca) return "";
      return localStorage.getItem("produtos_filtro_busca") || "";
    })(),
    ativo: "ativos",
    categoria_id: "",
    marca_id: "",
    fornecedor_id: "",
    estoque_baixo: false,
    em_promocao: false,
    mostrarPaisVariacoes: false,
  });
  const [paginaAtual, setPaginaAtual] = useState(1);
  const [itensPorPagina, setItensPorPagina] = useState(20);
  const [totalItensServidor, setTotalItensServidor] = useState(0);
  const [totalPaginasServidor, setTotalPaginasServidor] = useState(1);
  const produtosVisiveisRef = useRef([]);

  const produtosFiltrados = useMemo(() => {
    let produtosTemp = [...produtosBrutos];
    const buscaNormalizada = normalizeSearchText(filtros.busca).trim();

    if (!filtros.mostrarPaisVariacoes) {
      return produtosTemp.filter((p) => (p.tipo_produto || "SIMPLES") === "SIMPLES");
    }

    produtosTemp = produtosTemp.filter((p) => {
      if (p.tipo_produto !== "VARIACAO") {
        return true;
      }

      if (buscaNormalizada) {
        const codigo = normalizeSearchText(p.codigo || p.sku || "");
        const nome = normalizeSearchText(p.nome || "");
        return codigo.includes(buscaNormalizada) || nome.includes(buscaNormalizada);
      }

      return paisExpandidos.includes(p.produto_pai_id);
    });

    return produtosTemp;
  }, [
    filtros.busca,
    filtros.mostrarPaisVariacoes,
    normalizeSearchText,
    paisExpandidos,
    produtosBrutos,
  ]);

  const produtos = produtosFiltrados;
  const totalPaginas = Math.max(totalPaginasServidor, 1);
  const totalItens = totalItensServidor;

  useEffect(() => {
    setPaginaAtual(1);
  }, [filtros]);

  useEffect(() => {
    produtosVisiveisRef.current = produtos;
  }, [produtos]);

  const carregarDados = async (filtrosAtuais = filtros) => {
    try {
      setLoading(true);
      const filtrosLimpos = {};
      Object.keys(filtrosAtuais).forEach((key) => {
        const valor = filtrosAtuais[key];

        if (key === "mostrarPaisVariacoes") {
          return;
        }

        if (key === "ativo") {
          if (valor === "ativos") {
            filtrosLimpos[key] = true;
          } else if (valor === "inativos") {
            filtrosLimpos[key] = false;
          }
          return;
        }

        if (valor !== "" && valor !== null && valor !== undefined) {
          filtrosLimpos[key] = valor;
        }
      });

      filtrosLimpos.page = paginaAtual;
      filtrosLimpos.page_size = itensPorPagina;
      filtrosLimpos.include_variations = filtrosAtuais.mostrarPaisVariacoes;

      const response = await getProdutos(filtrosLimpos);

      let produtosData;
      let totalApi = 0;
      let pagesApi = 1;
      if (Array.isArray(response.data)) {
        produtosData = response.data;
        totalApi = response.data.length;
      } else if (response.data.itens) {
        produtosData = response.data.itens;
        totalApi = response.data.total || produtosData.length;
        pagesApi = response.data.pages || 1;
      } else if (response.data.items) {
        produtosData = response.data.items;
        totalApi = response.data.total || produtosData.length;
        pagesApi = response.data.pages || 1;
      } else if (response.data.produtos) {
        produtosData = response.data.produtos;
        totalApi = response.data.total || produtosData.length;
        pagesApi = response.data.pages || 1;
      } else if (response.data.data) {
        produtosData = response.data.data;
        totalApi = response.data.total || produtosData.length;
        pagesApi = response.data.pages || 1;
      } else {
        const arrayKeys = Object.keys(response.data).filter((key) =>
          Array.isArray(response.data[key]),
        );
        if (arrayKeys.length > 0) {
          produtosData = response.data[arrayKeys[0]];
        } else {
          produtosData = [];
        }
        totalApi = response.data.total || produtosData.length;
        pagesApi = response.data.pages || 1;
      }

      setProdutosBrutos(produtosData);
      setTotalItensServidor(totalApi);
      setTotalPaginasServidor(Math.max(pagesApi, 1));
    } catch (error) {
      console.error("Erro ao carregar produtos:", error);
      alert("Erro ao carregar produtos");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      carregarDados();
    }, filtros.busca ? 250 : 0);

    return () => clearTimeout(timer);
  }, [
    filtros.ativo,
    filtros.busca,
    filtros.categoria_id,
    filtros.em_promocao,
    filtros.estoque_baixo,
    filtros.fornecedor_id,
    filtros.marca_id,
    filtros.mostrarPaisVariacoes,
    itensPorPagina,
    paginaAtual,
  ]);

  useEffect(() => {
    localStorage.setItem("produtos_persistir_busca", String(persistirBusca));

    if (persistirBusca) {
      localStorage.setItem("produtos_filtro_busca", filtros.busca || "");
      return;
    }

    localStorage.removeItem("produtos_filtro_busca");
  }, [persistirBusca, filtros.busca]);

  const handleFiltroChange = (campo, valor) => {
    const proximoFiltro = { ...filtros, [campo]: valor };
    setFiltros(proximoFiltro);

    if (campo === "mostrarPaisVariacoes" && !valor) {
      onOcultarPaisVariacoes?.();
    }

    if (campo !== "mostrarPaisVariacoes") {
      setPaginaAtual(1);
    }
  };

  const handleSelecionar = (id, event) => {
    if (!id) {
      console.error("Erro: ID do produto Ã© undefined ou null");
      return;
    }

    if (event?.shiftKey && ultimoSelecionado !== null) {
      const indexUltimo = produtos.findIndex((p) => p.id === ultimoSelecionado);
      const indexAtual = produtos.findIndex((p) => p.id === id);

      if (indexUltimo !== -1 && indexAtual !== -1) {
        const inicio = Math.min(indexUltimo, indexAtual);
        const fim = Math.max(indexUltimo, indexAtual);
        const intervalo = produtos.slice(inicio, fim + 1).map((p) => p.id);

        setSelecionados((prev) => {
          const novo = new Set(prev);
          intervalo.forEach((prodId) => novo.add(prodId));
          return Array.from(novo);
        });
        setUltimoSelecionado(id);
        return;
      }
    }

    setSelecionados((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id],
    );
    setUltimoSelecionado(id);
  };

  const handleSelecionarTodos = () => {
    if (selecionados.length === produtos.length) {
      setSelecionados([]);
    } else {
      setSelecionados(produtos.map((p) => p.id));
    }
  };

  return {
    carregarDados,
    filtros,
    handleFiltroChange,
    handleSelecionar,
    handleSelecionarTodos,
    itensPorPagina,
    loading,
    paginaAtual,
    persistirBusca,
    produtos,
    produtosBrutos,
    produtosVisiveisRef,
    selecionados,
    setItensPorPagina,
    setPaginaAtual,
    setPersistirBusca,
    setSelecionados,
    totalItens,
    totalPaginas,
  };
}
