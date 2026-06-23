/**
 * FormulÃ¡rio de Cadastro/EdiÃ§Ã£o de Produtos - Layout em Abas
 */
import { useState, useEffect } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import ProdutosNovoMainContent from "../components/produto/ProdutosNovoMainContent";
import ProdutosNovoModalsLayer from "../components/produto/ProdutosNovoModalsLayer";
import useProdutosNovoCarregamento from "../hooks/useProdutosNovoCarregamento";
import useProdutosNovoCodigos from "../hooks/useProdutosNovoCodigos";
import useProdutosNovoFornecedores from "../hooks/useProdutosNovoFornecedores";
import useProdutosNovoImagens from "../hooks/useProdutosNovoImagens";
import useProdutosNovoKit from "../hooks/useProdutosNovoKit";
import useProdutosNovoLotes from "../hooks/useProdutosNovoLotes";
import useProdutosNovoPredecessor from "../hooks/useProdutosNovoPredecessor";
import useProdutosNovoRacao from "../hooks/useProdutosNovoRacao";
import useProdutosNovoRecorrencia from "../hooks/useProdutosNovoRecorrencia";
import useProdutosNovoSubmit from "../hooks/useProdutosNovoSubmit";
import useProdutosNovoTributacao from "../hooks/useProdutosNovoTributacao";
import useProdutosNovoVariacoes from "../hooks/useProdutosNovoVariacoes";
import useProdutosNovoPageComposition from "../hooks/useProdutosNovoPageComposition";
import api from "../api";
import { calcularPrecoVenda, calcularMarkup, formatarMoeda, formatarData } from "../api/produtos";

// Função auxiliar para converter valores sem retornar NaN
const parseNumber = (valor) => {
  if (valor === "" || valor === null || valor === undefined) return 0;
  // Permite tanto vírgula quanto ponto como separador decimal
  const limpo = valor.toString().replace(/[^\d.,]/g, "");
  // Normaliza vírgula para ponto
  const normalizado = limpo.replace(",", ".");
  const numero = parseFloat(normalizado);
  return isNaN(numero) ? 0 : numero;
};

export default function ProdutosNovo() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const isEdicao = !!id;
  const cloneId = searchParams.get("clone") || searchParams.get("clone_id");
  const isClone = !isEdicao && !!cloneId;

  // Estado das abas
  const [abaAtiva, setAbaAtiva] = useState(1);

  // Estado do formulÃ¡rio
  const [formData, setFormData] = useState({
    // Aba 1: Características
    codigo: "",
    sku: "",
    nome: "",
    codigo_barras: "",
    gtin_ean: "",
    gtin_ean_tributario: "",
    codigos_barras_alternativos: "",
    categoria_id: "",
    marca_id: "",
    departamento_id: "",
    tipo: "produto",
    unidade: "UN",
    descricao: "",
    preco_custo: "",
    preco_venda: "",
    preco_promocional: "",
    data_inicio_promocao: "",
    data_fim_promocao: "",
    preco_ecommerce: "",
    preco_ecommerce_promo: "",
    preco_ecommerce_promo_inicio: "",
    preco_ecommerce_promo_fim: "",
    preco_app: "",
    preco_app_promo: "",
    preco_app_promo_inicio: "",
    preco_app_promo_fim: "",
    anunciar_ecommerce: true,
    anunciar_app: true,
    ativo: true,
    situacao: true,
    markup: "",

    // Sprint 2: Produtos com variação
    tipo_produto: "SIMPLES", // SIMPLES, PAI (variação), KIT (composição), VARIACAO
    produto_pai_id: null,

    // Composição do Kit (VARIACAO também pode ser KIT)
    tipo_kit: null, // 'VIRTUAL' ou 'FISICO' (quando é kit)
    e_kit_fisico: false, // Se false, estoque é virtual (calculado)
    composicao_kit: [], // Array de {produto_id, produto_nome, quantidade}

    // Sistema Predecessor/Sucessor
    produto_predecessor_id: null,
    motivo_descontinuacao: "",

    // Aba 3: Estoque
    controle_lote: true,
    estoque_minimo: "",
    estoque_maximo: "",
    participa_sugestao_compra: true,

    // Aba 5: Tributação (Fiscal V2)
    tributacao: {
      origem: null, // 'empresa_legado', 'produto_legado', 'produto_fiscal_v2', 'kit_fiscal_v2'
      herdado_da_empresa: false,
      origem_mercadoria: "0",
      ncm: "",
      cest: "",
      cfop: "",
      cst_icms: "",
      icms_aliquota: "",
      icms_st: false,
      pis_aliquota: "",
      cofins_aliquota: "",
    },
    // Campos legados (mantidos para fallback)
    origem: "0",
    ncm: "",
    cest: "",
    cfop: "",
    aliquota_icms: "",
    aliquota_pis: "",
    aliquota_cofins: "",

    // Aba 6: Recorrência (Fase 1)
    tem_recorrencia: false,
    tipo_recorrencia: "monthly",
    intervalo_dias: "",
    numero_doses: "",
    observacoes_recorrencia: "",
    especie_compativel: "both",

    // Aba 7: Ração - Calculadora (Fase 2)
    eh_racao: false,
    e_granel: false,
    classificacao_racao: "",
    peso_embalagem: "",
    tabela_nutricional: "",
    tabela_consumo: "",
    categoria_racao: "",
    especies_indicadas: "both",

    // Opções de Ração - Sistema Dinâmico
    linha_racao_id: "",
    porte_animal_id: "",
    fase_publico_id: "",
    tipo_tratamento_id: "",
    sabor_proteina_id: "",
    apresentacao_peso_id: "",
  });

  // Dados auxiliares
  const [, setCategorias] = useState([]);
  const [categoriasHierarquicas, setCategoriasHierarquicas] = useState([]);
  const [marcas, setMarcas] = useState([]);
  const [departamentos, setDepartamentos] = useState([]);
  const [imagens, setImagens] = useState([]);
  const [clientes, setClientes] = useState([]);

  // Opções de Ração - Dados dinâmicos das APIs
  const [opcoesLinhas, setOpcoesLinhas] = useState([]);
  const [opcoesPortes, setOpcoesPortes] = useState([]);
  const [opcoesFases, setOpcoesFases] = useState([]);
  const [opcoesTratamentos, setOpcoesTratamentos] = useState([]);
  const [opcoesSabores, setOpcoesSabores] = useState([]);
  const [opcoesApresentacoes, setOpcoesApresentacoes] = useState([]);

  const [loading, setLoading] = useState(false);
  const [salvando, setSalvando] = useState(false);

  // Estados para controlar edição de campos monetários
  const [camposEmEdicao, setCamposEmEdicao] = useState({
    preco_custo: false,
    markup: false,
    preco_venda: false,
    preco_promocional: false,
  });

  const handleChange = (campo, valor) => {
    setFormData((prev) => {
      const novosDados = { ...prev, [campo]: valor };

      if (campo === "sku" || campo === "codigo") {
        const skuNormalizado = (valor || "").toString().toUpperCase();
        novosDados.sku = skuNormalizado;
        novosDados.codigo = skuNormalizado;
      }

      // Calcular markup automaticamente quando mudar preço
      if (campo === "preco_custo" || campo === "preco_venda") {
        const custo = parseNumber(campo === "preco_custo" ? valor : prev.preco_custo);
        const venda = parseNumber(campo === "preco_venda" ? valor : prev.preco_venda);

        if (custo && venda && custo > 0) {
          const markup = calcularMarkup(custo, venda);
          novosDados.markup = markup.toFixed(2);
        }
      }

      // Calcular preço de venda pelo markup
      if (campo === "markup") {
        const custo = parseNumber(prev.preco_custo);
        const markupVal = parseNumber(valor);

        if (custo && custo > 0 && markupVal >= 0) {
          const venda = calcularPrecoVenda(custo, markupVal);
          novosDados.preco_venda = venda.toFixed(2);
        }
      }

      return novosDados;
    });
  };

  const {
    mostrarBuscaPredecessor,
    produtosBusca,
    buscaPredecessor,
    predecessorSelecionado,
    predecessorInfo,
    sucessorInfo,
    setPredecessorInfo,
    setSucessorInfo,
    handleToggleBuscaPredecessor,
    handleBuscaPredecessorChange,
    handleSelecionarPredecessor,
    handleRemoverPredecessor,
  } = useProdutosNovoPredecessor({
    handleChange,
  });

  const {
    lotes,
    setLotes,
    modalEntrada,
    setModalEntrada,
    entradaData,
    setEntradaData,
    modalEdicaoLote,
    setModalEdicaoLote,
    loteEmEdicao,
    setLoteEmEdicao,
    handleEntradaEstoque,
    handleEditarLote,
    handleSalvarEdicaoLote,
    handleExcluirLote,
  } = useProdutosNovoLotes({ id });

  const {
    fornecedores,
    setFornecedores,
    modalFornecedor,
    setModalFornecedor,
    fornecedorEdit,
    fornecedorData,
    setFornecedorData,
    handleAddFornecedor,
    handleEditFornecedor,
    handleSaveFornecedor,
    handleDeleteFornecedor,
  } = useProdutosNovoFornecedores({ id });

  const { salvarFiscal } = useProdutosNovoCarregamento({
    cloneId,
    id,
    isEdicao,
    formData,
    setCategorias,
    setCategoriasHierarquicas,
    setMarcas,
    setDepartamentos,
    setClientes,
    setOpcoesLinhas,
    setOpcoesPortes,
    setOpcoesFases,
    setOpcoesTratamentos,
    setOpcoesSabores,
    setOpcoesApresentacoes,
    setLoading,
    setFormData,
    setPredecessorInfo,
    setSucessorInfo,
    setImagens,
    setLotes,
    setFornecedores,
  });

  const { handleChangeTributacao, handlePersonalizarFiscal } = useProdutosNovoTributacao({
    setFormData,
  });

  const { uploadingImage, handleUploadImagem, handleDeleteImagem, handleSetPrincipal } =
    useProdutosNovoImagens({
      id,
      setImagens,
    });

  const {
    produtosDisponiveis,
    produtoKitSelecionado,
    setProdutoKitSelecionado,
    quantidadeKit,
    setQuantidadeKit,
    estoqueVirtualKit,
    buscaComponente,
    setBuscaComponente,
    dropdownComponenteVisivel,
    setDropdownComponenteVisivel,
    adicionarProdutoKit,
    removerProdutoKit,
  } = useProdutosNovoKit({
    abaAtiva,
    formData,
    setFormData,
  });

  const {
    variacoes,
    novaVariacao,
    setNovaVariacao,
    mostrarFormVariacao,
    handleToggleFormVariacao,
    handleCancelarVariacao,
    handleSalvarVariacao,
    handleExcluirVariacao,
  } = useProdutosNovoVariacoes({
    id,
    isEdicao,
    abaAtiva,
    formData,
    navigate,
  });

  const { handleTipoRecorrenciaChange } = useProdutosNovoRecorrencia({
    handleChange,
  });

  const { handleClassificacaoRacaoChange, handleFasePublicoChange, handleApresentacaoPesoChange } =
    useProdutosNovoRacao({
      opcoesApresentacoes,
      opcoesFases,
      setFormData,
    });

  const { handleSubmit } = useProdutosNovoSubmit({
    id,
    isClone,
    isEdicao,
    formData,
    navigate,
    salvarFiscal,
    setSalvando,
  });

  const { handleGerarSKU, handleGerarCodigoBarras } = useProdutosNovoCodigos({
    formData,
    setFormData,
  });

  const handleVoltar = () => {
    if (formData.tipo_produto === "VARIACAO" && formData.produto_pai_id) {
      navigate(`/produtos/${formData.produto_pai_id}/editar?aba=8`);
      return;
    }

    navigate("/produtos");
  };

  const handleClonarProduto = () => {
    if (!id) return;
    navigate(`/produtos/novo?clone=${id}`);
  };

  const handleCriarOpcaoRacao = async (tipo, dados) => {
    const configs = {
      linha: {
        endpoint: "/opcoes-racao/linhas",
        setter: setOpcoesLinhas,
        field: "linha_racao_id",
        afterSelect: (item) => handleChange("classificacao_racao", item.nome || ""),
      },
      porte: {
        endpoint: "/opcoes-racao/portes",
        setter: setOpcoesPortes,
        field: "porte_animal_id",
      },
      fase: {
        endpoint: "/opcoes-racao/fases",
        setter: setOpcoesFases,
        field: "fase_publico_id",
        afterSelect: (item) => handleChange("categoria_racao", item.nome || ""),
      },
      tratamento: {
        endpoint: "/opcoes-racao/tratamentos",
        setter: setOpcoesTratamentos,
        field: "tipo_tratamento_id",
      },
      sabor: {
        endpoint: "/opcoes-racao/sabores",
        setter: setOpcoesSabores,
        field: "sabor_proteina_id",
      },
      apresentacao: {
        endpoint: "/opcoes-racao/apresentacoes",
        setter: setOpcoesApresentacoes,
        field: "apresentacao_peso_id",
        afterSelect: (item) => handleChange("peso_embalagem", item.peso_kg || ""),
      },
    };
    const config = configs[tipo];
    if (!config) {
      throw new Error("Tipo de opcao de racao invalido.");
    }

    const pesoKg = Number(dados.peso_kg);
    const pesoLabel = Number.isInteger(pesoKg) ? `${pesoKg}kg` : `${pesoKg.toString()}kg`;
    const payload =
      tipo === "apresentacao"
        ? {
            peso_kg: pesoKg,
            descricao: dados.descricao || pesoLabel,
            ordem: 999,
            ativo: true,
          }
        : {
            nome: (dados.nome || "").trim(),
            descricao: dados.descricao || null,
            ordem: 999,
            ativo: true,
          };

    const ordenarOpcoes = (items) =>
      items.sort((a, b) => {
        const ordemA = Number(a.ordem ?? 999);
        const ordemB = Number(b.ordem ?? 999);
        if (ordemA !== ordemB) return ordemA - ordemB;
        return String(a.nome || a.descricao || a.peso_kg).localeCompare(
          String(b.nome || b.descricao || b.peso_kg),
        );
      });

    const response = await api.post(config.endpoint, payload);
    const item = response.data;
    try {
      const listaResponse = await api.get(config.endpoint, { params: { apenas_ativos: true } });
      const lista = Array.isArray(listaResponse.data) ? listaResponse.data : [];
      const incluiCriado = lista.some((opcao) => String(opcao.id) === String(item.id));
      config.setter(ordenarOpcoes(incluiCriado ? lista : [...lista, item]));
    } catch (error) {
      console.error("Erro ao recarregar opcoes de racao apos cadastro rapido:", error);
      config.setter((prev) => {
        const semDuplicado = prev.filter((opcao) => String(opcao.id) !== String(item.id));
        return ordenarOpcoes([...semDuplicado, item]);
      });
    }
    handleChange(config.field, item.id);
    config.afterSelect?.(item);
    return item;
  };

  const { mainContentProps, modalsLayerProps } = useProdutosNovoPageComposition({
    pageState: {
      abaAtiva,
      camposEmEdicao,
      formData,
      isClone,
      isEdicao,
      loading,
      salvando,
      setCamposEmEdicao,
      setFormData,
    },
    catalogos: {
      categoriasHierarquicas,
      clientes,
      departamentos,
      marcas,
    },
    predecessorState: {
      buscaPredecessor,
      handleBuscaPredecessorChange,
      handleRemoverPredecessor,
      handleSelecionarPredecessor,
      handleToggleBuscaPredecessor,
      mostrarBuscaPredecessor,
      predecessorInfo,
      predecessorSelecionado,
      produtosBusca,
      sucessorInfo,
    },
    imagensState: {
      handleDeleteImagem,
      handleSetPrincipal,
      handleUploadImagem,
      imagens,
      uploadingImage,
    },
    lotesState: {
      entradaData,
      handleEditarLote,
      handleEntradaEstoque,
      handleExcluirLote,
      handleSalvarEdicaoLote,
      loteEmEdicao,
      lotes,
      modalEdicaoLote,
      modalEntrada,
      setEntradaData,
      setLoteEmEdicao,
      setModalEdicaoLote,
      setModalEntrada,
    },
    fornecedoresState: {
      fornecedores,
      fornecedorData,
      fornecedorEdit,
      handleAddFornecedor,
      handleDeleteFornecedor,
      handleEditFornecedor,
      handleSaveFornecedor,
      modalFornecedor,
      setFornecedorData,
      setModalFornecedor,
    },
    tributacaoState: {
      handleChangeTributacao,
      handlePersonalizarFiscal,
    },
    recorrenciaState: {
      handleTipoRecorrenciaChange,
    },
    racaoState: {
      handleCriarOpcaoRacao,
      handleApresentacaoPesoChange,
      handleClassificacaoRacaoChange,
      handleFasePublicoChange,
      opcoesApresentacoes,
      opcoesFases,
      opcoesLinhas,
      opcoesPortes,
      opcoesSabores,
      opcoesTratamentos,
    },
    variacoesState: {
      handleCancelarVariacao,
      handleExcluirVariacao,
      handleSalvarVariacao,
      handleToggleFormVariacao,
      mostrarFormVariacao,
      novaVariacao,
      setNovaVariacao,
      variacoes,
    },
    kitState: {
      adicionarProdutoKit,
      buscaComponente,
      dropdownComponenteVisivel,
      estoqueVirtualKit,
      produtoKitSelecionado,
      produtosDisponiveis,
      quantidadeKit,
      removerProdutoKit,
      setBuscaComponente,
      setDropdownComponenteVisivel,
      setProdutoKitSelecionado,
      setQuantidadeKit,
    },
    navigationState: {
      handleClonarProduto,
      handleVoltar,
      navigate,
      setAbaAtiva,
    },
    utilsState: {
      formatarData,
      formatarMoeda,
      handleChange,
      handleGerarCodigoBarras,
      handleGerarSKU,
      parseNumber,
    },
  });

  // Auto-detectar "ração" no nome do produto
  useEffect(() => {
    if (!isEdicao && formData.nome) {
      const nomeMinusculo = formData.nome.toLowerCase();
      const isRacao = nomeMinusculo.includes("racao") || nomeMinusculo.includes("ração");

      if (isRacao && !formData.eh_racao) {
        setFormData((prev) => ({
          ...prev,
          eh_racao: true,
        }));
      }
    }
  }, [formData.nome, isEdicao, formData.eh_racao]);

  // Detectar parâmetro de aba na URL (após carregar o produto)
  useEffect(() => {
    if (!loading && isEdicao) {
      const abaParam = searchParams.get("aba");
      if (abaParam) {
        setAbaAtiva(parseInt(abaParam, 10));
      }
    }
  }, [loading, searchParams, isEdicao]);

  // 🛡️ PROTEÇÃO: Se for VARIACAO e estiver na aba 8, voltar para aba 1
  useEffect(() => {
    if (isEdicao && formData.tipo_produto === "VARIACAO" && abaAtiva === 8) {
      setAbaAtiva(1);
    }
  }, [formData.tipo_produto, abaAtiva, isEdicao]);

  if (loading) {
    return (
      <div className="p-6 flex justify-center items-center h-96">
        <div className="text-gray-600">
          {isClone ? "Preparando clone do produto..." : "Carregando produto..."}
        </div>
      </div>
    );
  }

  // Proteção: Se é edição mas o formData ainda não foi carregado
  if ((isEdicao || isClone) && !formData.nome) {
    return (
      <div className="p-6 flex justify-center items-center h-96">
        <div className="text-gray-600">
          {isClone ? "Preparando dados para clonar..." : "Carregando dados..."}
        </div>
      </div>
    );
  }

  return (
    <>
      <ProdutosNovoMainContent handleSubmit={handleSubmit} {...mainContentProps} />

      <ProdutosNovoModalsLayer {...modalsLayerProps} />
    </>
  );
}
