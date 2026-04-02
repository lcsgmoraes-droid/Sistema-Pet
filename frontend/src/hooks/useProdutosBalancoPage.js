import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import api from "../api";
import { getMarcas, getProdutos } from "../api/produtos";
import { parseNumeroBR } from "../components/produtoBalanco/produtosBalancoUtils";

export function useProdutosBalancoPage() {
  const [produtos, setProdutos] = useState([]);
  const [marcas, setMarcas] = useState([]);
  const [fornecedores, setFornecedores] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [submetendo, setSubmetendo] = useState({});
  const [inputs, setInputs] = useState({});
  const [destacados, setDestacados] = useState({});
  const [paginaAtual, setPaginaAtual] = useState(1);
  const [totalItensServidor, setTotalItensServidor] = useState(0);
  const [totalPaginasServidor, setTotalPaginasServidor] = useState(1);
  const [filtros, setFiltros] = useState({
    busca: "",
    marca_id: "",
    fornecedor_id: "",
  });

  const itensPorPagina = 20;
  const inputRefs = useRef({});
  const produtosPaginados = produtos;
  const totalItens = totalItensServidor;
  const totalPaginas = Math.max(totalPaginasServidor, 1);
  const inicioItem = totalItens === 0 ? 0 : (paginaAtual - 1) * itensPorPagina + 1;
  const fimItem = totalItens === 0 ? 0 : Math.min(paginaAtual * itensPorPagina, totalItens);

  const carregarDadosComFiltros = async (filtrosAtuais, pagina = 1) => {
    try {
      setCarregando(true);
      const params = {
        page: pagina,
        page_size: itensPorPagina,
        include_variations: false,
      };

      if (filtrosAtuais.busca) params.busca = filtrosAtuais.busca;
      if (filtrosAtuais.marca_id) params.marca_id = filtrosAtuais.marca_id;
      if (filtrosAtuais.fornecedor_id) params.fornecedor_id = filtrosAtuais.fornecedor_id;

      const [prodRes, marcasRes, cliRes] = await Promise.all([
        getProdutos(params),
        getMarcas(),
        api.get("/clientes/", {
          params: { tipo_cadastro: "fornecedor", apenas_ativos: true, page_size: 1000 },
        }),
      ]);

      const items = prodRes.data?.items || [];
      const total = prodRes.data?.total || items.length;
      const pages = prodRes.data?.pages || 1;

      setProdutos(items);
      setTotalItensServidor(total);
      setTotalPaginasServidor(Math.max(pages, 1));
      setMarcas(marcasRes.data || []);
      setFornecedores(Array.isArray(cliRes.data) ? cliRes.data : cliRes.data?.items || []);
    } catch (error) {
      console.error("Erro ao carregar balanco:", error);
      toast.error("Erro ao carregar produtos para balanco.");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    carregarDadosComFiltros(filtros, paginaAtual);
  }, [paginaAtual]);

  const atualizarFiltro = (campo, valor) => {
    setFiltros((prev) => ({ ...prev, [campo]: valor }));
  };

  const aplicarFiltrosServidor = async () => {
    setDestacados({});
    setPaginaAtual(1);
    await carregarDadosComFiltros(filtros, 1);
  };

  const registrarDestaque = (produtoId, tipo) => {
    setDestacados((prev) => ({
      ...prev,
      [produtoId]: { tipo, timestamp: Date.now() },
    }));
  };

  const proximoProdutoId = (produtoId) => {
    const idx = produtosPaginados.findIndex((p) => p.id === produtoId);
    if (idx < 0 || idx + 1 >= produtosPaginados.length) return null;
    return produtosPaginados[idx + 1].id;
  };

  const focarProximoCampo = (produtoId, campo) => {
    const prox = proximoProdutoId(produtoId);
    if (!prox) return;
    const ref = inputRefs.current[`${prox}-${campo}`];
    if (ref) {
      ref.focus();
      ref.select();
    }
  };

  const limparLinhaInputs = (produtoId) => {
    setInputs((prev) => {
      const novo = { ...prev };
      delete novo[produtoId];
      return novo;
    });
  };

  const atualizarEstoqueLocal = (produtoId, novoEstoque) => {
    setProdutos((prev) =>
      prev.map((p) => (p.id === produtoId ? { ...p, estoque_atual: novoEstoque } : p))
    );
  };

  const registrarMovimento = async (produto, campo, valor) => {
    const qtd = parseNumeroBR(valor);
    if (!Number.isFinite(qtd) || qtd < 0) {
      toast.error("Informe um numero valido.");
      return false;
    }

    if (campo !== "balanco" && qtd === 0) {
      toast.error("A quantidade deve ser maior que zero.");
      return false;
    }

    setSubmetendo((prev) => ({ ...prev, [produto.id]: campo }));

    try {
      const estoqueAtual = Number(produto.estoque_atual || 0);
      const numeroLote = String(inputs?.[produto.id]?.lote || "").trim();
      const dataValidade = String(inputs?.[produto.id]?.validade || "").trim();

      if (campo === "entrada") {
        await api.post("/estoque/entrada", {
          produto_id: produto.id,
          quantidade: qtd,
          motivo: "balanco",
          observacao: "Lancamento rapido pela tela de Balanco",
          numero_lote: numeroLote || undefined,
          data_validade: dataValidade || undefined,
        });
        atualizarEstoqueLocal(produto.id, estoqueAtual + qtd);
      }

      if (campo === "saida") {
        if (qtd > estoqueAtual) {
          toast.error("Saida maior que o estoque atual.");
          return false;
        }
        await api.post("/estoque/saida", {
          produto_id: produto.id,
          quantidade: qtd,
          motivo: "balanco",
          observacao: "Lancamento rapido pela tela de Balanco",
        });
        atualizarEstoqueLocal(produto.id, estoqueAtual - qtd);
      }

      if (campo === "balanco") {
        const diferenca = qtd - estoqueAtual;
        if (Math.abs(diferenca) < 0.0001) {
          toast("Sem alteracao: estoque ja esta nesse valor.", { icon: "ℹ️" });
          limparLinhaInputs(produto.id);
          return true;
        }

        const endpoint = diferenca > 0 ? "/estoque/entrada" : "/estoque/saida";
        const payload = {
          produto_id: produto.id,
          quantidade: Math.abs(diferenca),
          motivo: "balanco",
          observacao: `Balanco rapido: estoque ajustado para ${qtd}`,
        };

        if (diferenca > 0) {
          payload.numero_lote = numeroLote || undefined;
          payload.data_validade = dataValidade || undefined;
        }

        await api.post(endpoint, payload);
        atualizarEstoqueLocal(produto.id, qtd);
      }

      registrarDestaque(produto.id, campo);
      limparLinhaInputs(produto.id);
      toast.success("Lancamento registrado com origem Balanco.");
      return true;
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Erro ao registrar lancamento.");
      return false;
    } finally {
      setSubmetendo((prev) => {
        const novo = { ...prev };
        delete novo[produto.id];
        return novo;
      });
    }
  };

  const onInputKeyDown = async (event, produto, campo) => {
    if (event.key !== "Enter" && event.key !== "Tab") return;
    event.preventDefault();

    const valor = inputs?.[produto.id]?.[campo] ?? "";
    if (!String(valor).trim()) {
      focarProximoCampo(produto.id, campo);
      return;
    }

    const ok = await registrarMovimento(produto, campo, valor);
    if (ok) {
      focarProximoCampo(produto.id, campo);
    }
  };

  const atualizarInput = (produtoId, campo, valor) => {
    setInputs((prev) => ({
      ...prev,
      [produtoId]: {
        ...prev[produtoId],
        [campo]: valor,
      },
    }));
  };

  return {
    atualizarFiltro,
    atualizarInput,
    aplicarFiltrosServidor,
    carregando,
    filtros,
    fimItem,
    fornecedores,
    inicioItem,
    inputRefs,
    inputs,
    itensPorPagina,
    marcas,
    onInputKeyDown,
    paginaAtual,
    produtosPaginados,
    setPaginaAtual,
    submetendo,
    destacados,
    totalItens,
    totalPaginas,
  };
}
