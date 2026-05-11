import { useEffect, useMemo, useRef, useState } from "react";
import { getProdutos } from "../api/produtos";

const PRODUTOS_PERSISTIR_KEY = "produtos_persistir_busca";
const PRODUTOS_FILTROS_KEY = "produtos_filtros_v2";
const PRODUTOS_FILTRO_BUSCA_LEGADO_KEY = "produtos_filtro_busca";

const FILTROS_PADRAO = {
  busca: "",
  ativo: "ativos",
  categoria_id: "",
  marca_id: "",
  fornecedor_id: "",
  estoque_baixo: false,
  em_promocao: false,
  mostrarPaisVariacoes: false,
};

function normalizarFiltrosSalvos(filtros = {}) {
  return {
    ...FILTROS_PADRAO,
    ...filtros,
    busca: filtros.busca || "",
    ativo: filtros.ativo || "ativos",
    categoria_id: filtros.categoria_id ? String(filtros.categoria_id) : "",
    marca_id: filtros.marca_id ? String(filtros.marca_id) : "",
    fornecedor_id: filtros.fornecedor_id ? String(filtros.fornecedor_id) : "",
    estoque_baixo: Boolean(filtros.estoque_baixo),
    em_promocao: Boolean(filtros.em_promocao),
    mostrarPaisVariacoes: Boolean(filtros.mostrarPaisVariacoes),
  };
}

function lerEstadoPersistido(persistirBusca) {
  if (!persistirBusca) {
    return {
      filtros: { ...FILTROS_PADRAO },
      paginaAtual: 1,
      itensPorPagina: 20,
    };
  }

  try {
    const raw = localStorage.getItem(PRODUTOS_FILTROS_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      return {
        filtros: normalizarFiltrosSalvos(parsed.filtros),
        paginaAtual: Number(parsed.paginaAtual) > 0 ? Number(parsed.paginaAtual) : 1,
        itensPorPagina: Number(parsed.itensPorPagina) > 0 ? Number(parsed.itensPorPagina) : 20,
      };
    }
  } catch {
    localStorage.removeItem(PRODUTOS_FILTROS_KEY);
  }

  return {
    filtros: {
      ...FILTROS_PADRAO,
      busca: localStorage.getItem(PRODUTOS_FILTRO_BUSCA_LEGADO_KEY) || "",
    },
    paginaAtual: 1,
    itensPorPagina: 20,
  };
}

const normalizeExpandId = (value) => String(value ?? "");

function ordenarProdutosAgrupados(produtos, paisExpandidos) {
  const paisExpandidosSet = new Set((paisExpandidos || []).map(normalizeExpandId));
  const produtosPorId = new Map(produtos.map((produto) => [produto.id, produto]));
  const filhosPorPai = new Map();
  const linhaPrincipal = [];
  const variacoesOrfas = [];

  produtos.forEach((produto) => {
    if (produto.tipo_produto === "VARIACAO") {
      if (produto.produto_pai_id && produtosPorId.has(produto.produto_pai_id)) {
        if (!filhosPorPai.has(produto.produto_pai_id)) {
          filhosPorPai.set(produto.produto_pai_id, []);
        }
        filhosPorPai.get(produto.produto_pai_id).push(produto);
      } else {
        variacoesOrfas.push(produto);
      }
      return;
    }

    linhaPrincipal.push(produto);
  });

  const ordenados = [];
  const adicionados = new Set();

  linhaPrincipal.forEach((produto) => {
    if (adicionados.has(produto.id)) return;

    ordenados.push(produto);
    adicionados.add(produto.id);

    const filhos = filhosPorPai.get(produto.id) || [];
    const deveExibirFilhos =
      filhos.length > 0 && paisExpandidosSet.has(normalizeExpandId(produto.id));

    if (!deveExibirFilhos) return;

    filhos.forEach((filho) => {
      if (adicionados.has(filho.id)) return;
      ordenados.push(filho);
      adicionados.add(filho.id);
    });
  });

  variacoesOrfas.forEach((produto) => {
    if (adicionados.has(produto.id)) return;
    ordenados.push(produto);
    adicionados.add(produto.id);
  });

  return ordenados;
}

export default function useProdutosListagem({
  normalizeSearchText,
  onOcultarPaisVariacoes,
  paisExpandidos,
}) {
  const [persistirBusca, setPersistirBusca] = useState(() => {
    const salvo = localStorage.getItem(PRODUTOS_PERSISTIR_KEY);
    return salvo === null ? true : salvo === "true";
  });
  const estadoPersistidoInicial = useMemo(
    () => lerEstadoPersistido(persistirBusca),
    [],
  );
  const [produtosBrutos, setProdutosBrutos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selecionados, setSelecionados] = useState([]);
  const [ultimoSelecionado, setUltimoSelecionado] = useState(null);
  const [filtros, setFiltros] = useState(estadoPersistidoInicial.filtros);
  const [paginaAtual, setPaginaAtual] = useState(estadoPersistidoInicial.paginaAtual);
  const [itensPorPagina, setItensPorPagina] = useState(
    estadoPersistidoInicial.itensPorPagina,
  );
  const [totalItensServidor, setTotalItensServidor] = useState(0);
  const [totalPaginasServidor, setTotalPaginasServidor] = useState(1);
  const produtosVisiveisRef = useRef([]);
  const filtrosMontadosRef = useRef(false);

  const produtosFiltrados = useMemo(() => {
    let produtosTemp = [...produtosBrutos];
    const buscaNormalizada = normalizeSearchText(filtros.busca).trim();
    const termosBusca = buscaNormalizada.split(/\s+/).filter(Boolean);
    const buscaAtiva = Boolean(buscaNormalizada);
    const produtoCorrespondeBusca = (produto) => {
      const campos = [
        produto.codigo,
        produto.sku,
        produto.codigo_barras,
        produto.nome,
      ].map((value) => normalizeSearchText(value || ""));
      const camposDigitos = [produto.codigo, produto.sku, produto.codigo_barras].map(
        (value) => normalizeSearchText(value || "").replace(/\D/g, ""),
      );

      return termosBusca.every((termo) => {
        const termoDigitos = termo.replace(/\D/g, "");
        const correspondeTexto = campos.some((campo) => campo.includes(termo));

        if (correspondeTexto || !termoDigitos) {
          return correspondeTexto;
        }

        return camposDigitos.some((campo) => campo.includes(termoDigitos));
      });
    };

    if (!filtros.mostrarPaisVariacoes) {
      return produtosTemp.filter((p) => (p.tipo_produto || "SIMPLES") === "SIMPLES");
    }

    if (!buscaAtiva) {
      return ordenarProdutosAgrupados(produtosTemp, paisExpandidos);
    }

    const paisVisiveisPorBusca = new Set();
    const paisExpandidosSet = new Set((paisExpandidos || []).map(normalizeExpandId));

    produtosTemp.forEach((produto) => {
      if (!produtoCorrespondeBusca(produto)) return;

      if (produto.tipo_produto === "PAI") {
        paisVisiveisPorBusca.add(normalizeExpandId(produto.id));
        return;
      }

      if (produto.tipo_produto === "VARIACAO" && produto.produto_pai_id) {
        paisVisiveisPorBusca.add(normalizeExpandId(produto.produto_pai_id));
      }
    });

    produtosTemp = produtosTemp.filter((p) => {
      if (p.tipo_produto === "PAI") {
        return paisVisiveisPorBusca.has(normalizeExpandId(p.id)) || produtoCorrespondeBusca(p);
      }

      if (p.tipo_produto !== "VARIACAO") {
        return produtoCorrespondeBusca(p);
      }

      if (!p.produto_pai_id || !paisVisiveisPorBusca.has(normalizeExpandId(p.produto_pai_id))) {
        return produtoCorrespondeBusca(p);
      }

      return (
        produtoCorrespondeBusca(p) ||
        paisExpandidosSet.has(normalizeExpandId(p.produto_pai_id))
      );
    });

    return ordenarProdutosAgrupados(produtosTemp, paisExpandidos);
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
    if (!filtrosMontadosRef.current) {
      filtrosMontadosRef.current = true;
      return;
    }

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
    localStorage.setItem(PRODUTOS_PERSISTIR_KEY, String(persistirBusca));

    if (persistirBusca) {
      localStorage.setItem(
        PRODUTOS_FILTROS_KEY,
        JSON.stringify({
          filtros,
          itensPorPagina,
          paginaAtual,
        }),
      );
      localStorage.setItem(PRODUTOS_FILTRO_BUSCA_LEGADO_KEY, filtros.busca || "");
      return;
    }

    localStorage.removeItem(PRODUTOS_FILTROS_KEY);
    localStorage.removeItem(PRODUTOS_FILTRO_BUSCA_LEGADO_KEY);
  }, [persistirBusca, filtros, itensPorPagina, paginaAtual]);

  const handleFiltroChange = (campo, valor) => {
    const proximoFiltro = { ...filtros, [campo]: valor };
    setFiltros(proximoFiltro);
    setPaginaAtual(1);

    if (campo === "mostrarPaisVariacoes" && !valor) {
      onOcultarPaisVariacoes?.();
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
