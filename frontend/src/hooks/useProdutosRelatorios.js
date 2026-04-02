import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { formatarData, getProdutos } from "../api/produtos";

const COLUNAS_RELATORIO_PRODUTOS = [
  { key: "nome", label: "Nome", value: (p) => p.nome || "" },
  { key: "codigo", label: "Codigo", value: (p) => p.codigo || p.sku || "" },
  { key: "codigo_barras", label: "Codigo de Barras", value: (p) => p.codigo_barras || "" },
  {
    key: "categoria",
    label: "Categoria",
    value: (p) => p.categoria_nome || p.categoria?.nome || "",
  },
  {
    key: "marca",
    label: "Marca",
    value: (p) => p.marca_nome || p.marca?.nome || "",
  },
  {
    key: "fornecedor",
    label: "Fornecedor",
    value: (p) => p.fornecedor_nome || p.fornecedor?.nome || "",
  },
  { key: "unidade", label: "Unidade", value: (p) => p.unidade || "UN" },
  {
    key: "estoque",
    label: "Estoque",
    value: (p) => obterEstoqueVisualProduto(p),
  },
  {
    key: "estoque_minimo",
    label: "Estoque Minimo",
    value: (p) => Number(p.estoque_minimo ?? 0),
  },
  {
    key: "preco_custo",
    label: "Preco Custo",
    value: (p) => Number(p.preco_custo ?? 0),
  },
  {
    key: "preco_venda",
    label: "Preco Venda",
    value: (p) => Number(p.preco_venda ?? 0),
  },
  {
    key: "margem",
    label: "Margem %",
    value: (p) => {
      const pv = Number(p.preco_venda ?? 0);
      const pc = Number(p.preco_custo ?? 0);
      if (!pv) return 0;
      return Number((((pv - pc) / pv) * 100).toFixed(2));
    },
  },
  {
    key: "ativo",
    label: "Ativo",
    value: (p) => (p.ativo === false ? "Nao" : "Sim"),
  },
  {
    key: "tipo_produto",
    label: "Tipo",
    value: (p) => p.tipo_produto || "SIMPLES",
  },
  {
    key: "atualizado_em",
    label: "Atualizado em",
    value: (p) => p.updated_at || p.data_atualizacao || p.created_at || "",
  },
];

const extrairItensDaRespostaProdutos = (payload) => {
  if (!payload) return [];
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload.itens)) return payload.itens;
  if (Array.isArray(payload.items)) return payload.items;
  if (Array.isArray(payload.produtos)) return payload.produtos;
  if (Array.isArray(payload.data)) return payload.data;
  return [];
};

const montarFiltroLimpo = (baseFiltros) => {
  const filtrosLimpos = {};
  Object.entries(baseFiltros || {}).forEach(([key, valor]) => {
    if (key === "mostrarPaisVariacoes") return;
    if (key === "ativo") {
      if (valor === "ativos") {
        filtrosLimpos[key] = true;
      } else if (valor === "inativos") {
        filtrosLimpos[key] = false;
      }
      return;
    }
    if (valor === "" || valor === null || valor === undefined) return;
    if (typeof valor === "boolean") {
      if (valor) filtrosLimpos[key] = true;
      return;
    }
    filtrosLimpos[key] = valor;
  });
  return filtrosLimpos;
};

const ordenarProdutosRelatorio = (lista, ordenacao, obterEstoqueVisualProduto) => {
  const copia = [...lista];
  const porTexto = (a, b, getter, asc = true) => {
    const va = String(getter(a) || "").toLowerCase();
    const vb = String(getter(b) || "").toLowerCase();
    return asc ? va.localeCompare(vb, "pt-BR") : vb.localeCompare(va, "pt-BR");
  };

  switch (ordenacao) {
    case "nome_desc":
      return copia.sort((a, b) => porTexto(a, b, (p) => p.nome, false));
    case "estoque_asc":
      return copia.sort(
        (a, b) => obterEstoqueVisualProduto(a) - obterEstoqueVisualProduto(b),
      );
    case "estoque_desc":
      return copia.sort(
        (a, b) => obterEstoqueVisualProduto(b) - obterEstoqueVisualProduto(a),
      );
    case "preco_asc":
      return copia.sort((a, b) => Number(a.preco_venda ?? 0) - Number(b.preco_venda ?? 0));
    case "preco_desc":
      return copia.sort((a, b) => Number(b.preco_venda ?? 0) - Number(a.preco_venda ?? 0));
    case "nome_asc":
    default:
      return copia.sort((a, b) => porTexto(a, b, (p) => p.nome, true));
  }
};

const normalizarValorCsv = (valor) => {
  if (valor === null || valor === undefined) return "";
  if (typeof valor === "number") return String(valor).replace(".", ",");
  return String(valor).replaceAll("\"", '""');
};

const baixarCsvProdutos = (nomeArquivo, colunas, dados) => {
  const cabecalho = colunas.map((coluna) => `"${coluna.label}"`).join(";");
  const linhas = dados.map((item) => {
    const valores = colunas.map((coluna) => {
      const valorBruto = coluna.value(item);
      const valorFinal = coluna.key === "atualizado_em" ? formatarData(valorBruto) : valorBruto;
      return `"${normalizarValorCsv(valorFinal)}"`;
    });
    return valores.join(";");
  });

  const csv = [cabecalho, ...linhas].join("\n");
  const blob = new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", nomeArquivo);
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
};

export default function useProdutosRelatorios({
  filtros,
  obterEstoqueVisualProduto,
}) {
  const [menuRelatoriosAberto, setMenuRelatoriosAberto] = useState(false);
  const [modalRelatorioPersonalizado, setModalRelatorioPersonalizado] =
    useState(false);
  const [colunasRelatorio, setColunasRelatorio] = useState([
    "nome",
    "codigo",
    "categoria",
    "estoque",
    "preco_custo",
    "preco_venda",
    "margem",
    "ativo",
  ]);
  const [ordenacaoRelatorio, setOrdenacaoRelatorio] = useState("nome_asc");
  const menuRelatoriosRef = useRef(null);

  useEffect(() => {
    const handleClickFora = (event) => {
      if (
        menuRelatoriosRef.current &&
        !menuRelatoriosRef.current.contains(event.target)
      ) {
        setMenuRelatoriosAberto(false);
      }
    };

    document.addEventListener("mousedown", handleClickFora);
    return () => document.removeEventListener("mousedown", handleClickFora);
  }, []);

  const carregarProdutosRelatorio = async (escopo) => {
    const filtrosBase =
      escopo === "geral"
        ? { ativo: "todos", mostrarPaisVariacoes: filtros.mostrarPaisVariacoes }
        : { ...filtros };
    const filtrosLimpos = montarFiltroLimpo(filtrosBase);
    filtrosLimpos.include_variations = Boolean(filtrosBase.mostrarPaisVariacoes);

    const acumulado = [];
    let pagina = 1;
    let continuar = true;

    while (continuar && pagina <= 40) {
      const resposta = await getProdutos({
        ...filtrosLimpos,
        page: pagina,
        page_size: 300,
      });
      const itens = extrairItensDaRespostaProdutos(resposta?.data);
      if (itens.length === 0) {
        continuar = false;
      } else {
        acumulado.push(...itens);
        if (itens.length < 300) {
          continuar = false;
        }
        pagina += 1;
      }
    }

    return acumulado;
  };

  const gerarRelatorioProdutos = async ({ escopo }) => {
    try {
      toast.loading("Gerando relatorio...", { id: "relatorio-produtos" });
      const dados = await carregarProdutosRelatorio(escopo);

      if (!dados.length) {
        toast.error("Nenhum produto encontrado para este relatorio.", {
          id: "relatorio-produtos",
        });
        return;
      }

      const ordenados = ordenarProdutosRelatorio(
        dados,
        ordenacaoRelatorio,
        obterEstoqueVisualProduto,
      );
      const colunasSelecionadas = new Set(colunasRelatorio.filter(Boolean));
      const colunas = COLUNAS_RELATORIO_PRODUTOS.filter((coluna) =>
        colunasSelecionadas.has(coluna.key),
      );

      if (!colunas.length) {
        toast.error("Selecione pelo menos uma coluna para gerar o relatorio.", {
          id: "relatorio-produtos",
        });
        return;
      }

      const sufixo = escopo === "geral" ? "geral" : "filtrado";
      const dataArquivo = new Date().toISOString().slice(0, 10);
      baixarCsvProdutos(`produtos_${sufixo}_${dataArquivo}.csv`, colunas, ordenados);

      toast.success(`Relatorio gerado com ${ordenados.length} produto(s).`, {
        id: "relatorio-produtos",
      });
    } catch (error) {
      console.error("Erro ao gerar relatorio de produtos:", error);
      toast.error("Nao foi possivel gerar o relatorio de produtos.", {
        id: "relatorio-produtos",
      });
    }
  };

  const toggleColunaRelatorio = (key) => {
    setColunasRelatorio((prev) =>
      prev.includes(key) ? prev.filter((item) => item !== key) : [...prev, key],
    );
  };

  return {
    colunasRelatorio,
    colunasRelatorioProdutos: COLUNAS_RELATORIO_PRODUTOS,
    menuRelatoriosAberto,
    menuRelatoriosRef,
    modalRelatorioPersonalizado,
    onCloseModalRelatorio: () => setModalRelatorioPersonalizado(false),
    onGerarRelatorioFiltrado: () => {
      setMenuRelatoriosAberto(false);
      void gerarRelatorioProdutos({ escopo: "filtrado" });
    },
    onGerarRelatorioGeral: () => {
      setMenuRelatoriosAberto(false);
      void gerarRelatorioProdutos({ escopo: "geral" });
    },
    onGerarRelatorioPersonalizado: async () => {
      await gerarRelatorioProdutos({ escopo: "filtrado" });
      setModalRelatorioPersonalizado(false);
    },
    onOpenModalRelatorio: () => {
      setMenuRelatoriosAberto(false);
      setModalRelatorioPersonalizado(true);
    },
    onToggleColunaRelatorio: toggleColunaRelatorio,
    onToggleMenuRelatorios: () => setMenuRelatoriosAberto((prev) => !prev),
    ordenacaoRelatorio,
    setOrdenacaoRelatorio,
  };
}
