import { useCallback, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { getAnaliseProdutos, getRelatorioProdutoVendas } from "../../api/produtos";
import useProdutosCatalogos from "../../hooks/useProdutosCatalogos";
import {
  criarFiltrosAnalise,
  criarPeriodo,
  criarPeriodoAnoAtual,
  gerarCsvProdutos,
  normalizarAnalise,
} from "./analiseProdutosUtils";

export default function useAnaliseProdutos() {
  const filtrosIniciais = useMemo(criarFiltrosAnalise, []);
  const [periodoAtivo, setPeriodoAtivo] = useState("30dias");
  const [filtrosForm, setFiltrosForm] = useState(filtrosIniciais);
  const [filtrosAplicados, setFiltrosAplicados] = useState(filtrosIniciais);
  const [dados, setDados] = useState(() => normalizarAnalise());
  const [carregando, setCarregando] = useState(true);
  const [produtoSelecionado, setProdutoSelecionado] = useState(null);
  const [dadosProduto, setDadosProduto] = useState(null);
  const [carregandoProduto, setCarregandoProduto] = useState(false);
  const [paginaProduto, setPaginaProduto] = useState(1);
  const catalogos = useProdutosCatalogos();

  useEffect(() => {
    let ativo = true;
    const carregar = async () => {
      try {
        setCarregando(true);
        const response = await getAnaliseProdutos(filtrosAplicados);
        if (ativo) setDados(normalizarAnalise(response?.data));
      } catch (error) {
        console.error("Erro ao carregar análise de produtos:", error);
        if (ativo) {
          setDados(normalizarAnalise());
          toast.error(error?.response?.data?.detail || "Não foi possível carregar a análise.");
        }
      } finally {
        if (ativo) setCarregando(false);
      }
    };
    void carregar();
    return () => {
      ativo = false;
    };
  }, [filtrosAplicados]);

  useEffect(() => {
    if (!produtoSelecionado?.id) {
      setDadosProduto(null);
      return undefined;
    }
    let ativo = true;
    const carregar = async () => {
      try {
        setCarregandoProduto(true);
        const response = await getRelatorioProdutoVendas({
          produto_id: produtoSelecionado.id,
          data_inicio: filtrosAplicados.data_inicio,
          data_fim: filtrosAplicados.data_fim,
          page: paginaProduto,
          page_size: 10,
        });
        if (ativo) setDadosProduto(response?.data || null);
      } catch (error) {
        console.error("Erro ao carregar produto específico:", error);
        if (ativo) toast.error("Não foi possível carregar o histórico desse produto.");
      } finally {
        if (ativo) setCarregandoProduto(false);
      }
    };
    void carregar();
    return () => {
      ativo = false;
    };
  }, [filtrosAplicados.data_fim, filtrosAplicados.data_inicio, paginaProduto, produtoSelecionado]);

  const atualizarFiltro = useCallback((campo, valor) => {
    setFiltrosForm((anterior) => ({ ...anterior, [campo]: valor }));
    if (campo === "data_inicio" || campo === "data_fim") setPeriodoAtivo("personalizado");
  }, []);

  const escolherPeriodo = useCallback((periodo) => {
    setPeriodoAtivo(periodo.id);
    if (periodo.id === "personalizado") return;
    const datas = periodo.id === "ano" ? criarPeriodoAnoAtual() : criarPeriodo(periodo.dias);
    setFiltrosForm((anterior) => ({ ...anterior, ...datas }));
    setFiltrosAplicados((anterior) => ({ ...anterior, ...datas }));
    setPaginaProduto(1);
  }, []);

  const aplicarFiltros = useCallback(
    (event) => {
      event?.preventDefault();
      if (filtrosForm.data_inicio > filtrosForm.data_fim) {
        toast.error("A data inicial deve ser anterior à data final.");
        return;
      }
      setFiltrosAplicados({ ...filtrosForm });
      setPaginaProduto(1);
    },
    [filtrosForm],
  );

  const limparFiltros = useCallback(() => {
    const limpos = criarFiltrosAnalise();
    setPeriodoAtivo("30dias");
    setFiltrosForm(limpos);
    setFiltrosAplicados(limpos);
    setPaginaProduto(1);
  }, []);

  const selecionarProduto = useCallback((produto) => {
    setProdutoSelecionado(produto);
    setPaginaProduto(1);
  }, []);

  const exportarCsv = useCallback(() => {
    if (!dados.produtos.length) {
      toast("Não há produtos no filtro atual para exportar.");
      return;
    }
    const blob = new Blob(["\uFEFF", gerarCsvProdutos(dados.produtos)], {
      type: "text/csv;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `analise_produtos_${filtrosAplicados.data_inicio}_${filtrosAplicados.data_fim}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }, [dados.produtos, filtrosAplicados.data_fim, filtrosAplicados.data_inicio]);

  return {
    catalogos,
    periodoAtivo,
    filtrosForm,
    filtrosAplicados,
    dados,
    carregando,
    produtoSelecionado,
    dadosProduto,
    carregandoProduto,
    paginaProduto,
    atualizarFiltro,
    escolherPeriodo,
    aplicarFiltros,
    limparFiltros,
    selecionarProduto,
    limparProduto: () => {
      setProdutoSelecionado(null);
      setDadosProduto(null);
    },
    setPaginaProduto,
    exportarCsv,
  };
}
