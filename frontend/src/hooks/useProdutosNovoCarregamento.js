import { useEffect, useRef } from "react";
import api from "../api";
import { normalizeMarkdownContent } from "../utils/safeMarkdown";
import {
  getCategorias,
  getDepartamentos,
  getFornecedoresProduto,
  getLotes,
  getMarcas,
  getProduto,
} from "../api/produtos";
import { calcularMargemSobreVenda } from "../utils/produtoMargem";
import {
  montarEstadoProdutoClonado,
  normalizarCodigosBarrasAlternativosCampo,
} from "../pages/produtosFormUtils";

const construirListaHierarquica = (categorias, parentId = null, nivel = 0) => {
  let resultado = [];

  const filhos = categorias.filter((categoria) => categoria.categoria_pai_id === parentId);

  filhos.forEach((categoria) => {
    const indentacao = "\u00a0\u00a0\u00a0\u00a0".repeat(nivel);
    const seta = nivel > 0 ? "→ " : "";

    resultado.push({
      ...categoria,
      nomeFormatado: indentacao + seta + categoria.nome,
      nivel,
    });

    resultado = resultado.concat(construirListaHierarquica(categorias, categoria.id, nivel + 1));
  });

  return resultado;
};

export default function useProdutosNovoCarregamento({
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
  setErroCarregamento,
  setFormData,
  setPredecessorInfo,
  setSucessorInfo,
  setImagens,
  setLotes,
  setFornecedores,
}) {
  const produtoRequestRef = useRef(0);

  const carregarOpcoesRacao = async () => {
    try {
      const { data } = await api.get("/opcoes-racao/resumo", {
        params: { apenas_ativos: true },
      });

      setOpcoesLinhas(Array.isArray(data?.linhas) ? data.linhas : []);
      setOpcoesPortes(Array.isArray(data?.portes) ? data.portes : []);
      setOpcoesFases(Array.isArray(data?.fases) ? data.fases : []);
      setOpcoesTratamentos(Array.isArray(data?.tratamentos) ? data.tratamentos : []);
      setOpcoesSabores(Array.isArray(data?.sabores) ? data.sabores : []);
      setOpcoesApresentacoes(Array.isArray(data?.apresentacoes) ? data.apresentacoes : []);
    } catch (error) {
      console.error("Erro ao carregar opções de ração:", error);
    }
  };

  const carregarDadosAuxiliares = async () => {
    const [categoriasResult, marcasResult, departamentosResult, clientesResult] =
      await Promise.allSettled([
        getCategorias(),
        getMarcas(),
        getDepartamentos(),
        api.get("/clientes/", {
          params: { tipo_cadastro: "fornecedor", apenas_ativos: true },
        }),
        carregarOpcoesRacao(),
      ]);

    if (categoriasResult.status === "fulfilled") {
      const categoriasCarregadas = categoriasResult.value.data || [];
      setCategorias(categoriasCarregadas);
      setCategoriasHierarquicas(construirListaHierarquica(categoriasCarregadas));
    } else {
      console.error("Erro ao carregar categorias:", categoriasResult.reason);
    }

    if (marcasResult.status === "fulfilled") {
      setMarcas(marcasResult.value.data || []);
    } else {
      console.error("Erro ao carregar marcas:", marcasResult.reason);
    }

    if (departamentosResult.status === "fulfilled") {
      setDepartamentos(departamentosResult.value.data || []);
    } else {
      console.error("Erro ao carregar departamentos:", departamentosResult.reason);
    }

    if (clientesResult.status === "fulfilled") {
      const clientesData = clientesResult.value.data;
      setClientes(Array.isArray(clientesData) ? clientesData : clientesData?.items || []);
    } else {
      console.error("Erro ao carregar fornecedores:", clientesResult.reason);
    }
  };

  const carregarFiscal = async (produto, requestAindaAtiva = () => true) => {
    try {
      const isKit = produto.tipo_produto === "KIT";
      const { data } = isKit
        ? await api.get(`/produtos/${produto.id}/kit/fiscal`)
        : await api.get(`/produtos/${produto.id}/fiscal`);

      if (requestAindaAtiva()) {
        setFormData((prev) => ({
          ...prev,
          tributacao: {
            origem: data.origem,
            herdado_da_empresa: data.herdado_da_empresa,
            origem_mercadoria: data.origem_mercadoria ?? "0",
            ncm: data.ncm ?? "",
            cest: data.cest ?? "",
            cfop: data.cfop ?? "",
            cst_icms: data.cst_icms ?? "",
            icms_aliquota: data.icms_aliquota ?? "",
            icms_st: data.icms_st ?? false,
            pis_aliquota: data.pis_aliquota ?? "",
            cofins_aliquota: data.cofins_aliquota ?? "",
          },
        }));
      }
    } catch (error) {
      console.error("Erro ao carregar fiscal:", error);
    }
  };

  const carregarProduto = async () => {
    const requestId = ++produtoRequestRef.current;
    const requestAindaAtiva = () => produtoRequestRef.current === requestId;

    try {
      setLoading(true);
      setErroCarregamento(null);
      setPredecessorInfo(null);
      setSucessorInfo(null);
      setImagens([]);
      setLotes([]);
      setFornecedores([]);

      const response = await getProduto(id);
      if (!requestAindaAtiva()) return;
      const produto = response.data;

      let margem = "";
      if (produto.preco_custo && produto.preco_venda && produto.preco_custo > 0) {
        const margemCalculada = calcularMargemSobreVenda(produto.preco_custo, produto.preco_venda);
        margem = margemCalculada === null ? "" : margemCalculada.toFixed(2);
      }

      setFormData({
        ...produto,
        sku: produto.codigo || "",
        codigo: produto.codigo || "",
        nome: produto.nome || "",
        codigo_barras: produto.codigo_barras || "",
        gtin_ean: produto.gtin_ean || "",
        gtin_ean_tributario: produto.gtin_ean_tributario || "",
        codigos_barras_alternativos: normalizarCodigosBarrasAlternativosCampo(
          produto.codigos_barras_alternativos,
        ),
        categoria_id: produto.categoria_id || "",
        marca_id: produto.marca_id || "",
        departamento_id: produto.departamento_id || "",
        unidade: produto.unidade || "UN",
        descricao: normalizeMarkdownContent(produto.descricao_curta || ""),
        tipo: produto.tipo || "produto",
        preco_custo: produto.preco_custo || "",
        preco_venda: produto.preco_venda || "",
        preco_promocional: produto.preco_promocional || "",
        data_inicio_promocao: produto.promocao_inicio || "",
        data_fim_promocao: produto.promocao_fim || "",
        preco_ecommerce: produto.preco_ecommerce ?? "",
        preco_ecommerce_promo: produto.preco_ecommerce_promo ?? "",
        preco_ecommerce_promo_inicio: produto.preco_ecommerce_promo_inicio ?? "",
        preco_ecommerce_promo_fim: produto.preco_ecommerce_promo_fim ?? "",
        preco_app: produto.preco_app ?? "",
        preco_app_promo: produto.preco_app_promo ?? "",
        preco_app_promo_inicio: produto.preco_app_promo_inicio ?? "",
        preco_app_promo_fim: produto.preco_app_promo_fim ?? "",
        anunciar_ecommerce: produto.anunciar_ecommerce ?? true,
        anunciar_app: produto.anunciar_app ?? true,
        ativo: produto.ativo ?? true,
        situacao: produto.situacao ?? true,
        estoque_minimo: produto.estoque_minimo || "",
        estoque_maximo: produto.estoque_maximo || "",
        participa_sugestao_compra: produto.participa_sugestao_compra ?? true,
        controle_lote: produto.controle_lote ?? true,
        margem,
        tipo_produto:
          Boolean(produto.e_granel) || (produto.nome || "").toLowerCase().includes("granel")
            ? "SIMPLES"
            : produto.tipo_produto || "SIMPLES",
        produto_pai_id: produto.produto_pai_id || null,
        tipo_kit:
          Boolean(produto.e_granel) || (produto.nome || "").toLowerCase().includes("granel")
            ? null
            : produto.tipo_kit || null,
        e_kit_fisico:
          Boolean(produto.e_granel) || (produto.nome || "").toLowerCase().includes("granel")
            ? false
            : produto.e_kit_fisico || false,
        composicao_kit: produto.composicao_kit || [],
        origem: produto.origem || "0",
        ncm: produto.ncm || "",
        cest: produto.cest || "",
        cfop: produto.cfop || "",
        aliquota_icms: produto.aliquota_icms || "",
        aliquota_pis: produto.aliquota_pis || "",
        aliquota_cofins: produto.aliquota_cofins || "",
        tem_recorrencia: produto.tem_recorrencia || false,
        tipo_recorrencia: produto.tipo_recorrencia || "monthly",
        intervalo_dias: produto.intervalo_dias || "",
        numero_doses: produto.numero_doses || "",
        especie_compativel: produto.especie_compativel || "both",
        observacoes_recorrencia: produto.observacoes_recorrencia || "",
        eh_racao:
          typeof produto.eh_racao === "boolean"
            ? produto.eh_racao
            : produto.tipo === "ração" ||
              produto.tipo === "racao" ||
              Boolean(produto.linha_racao_id) ||
              Boolean(produto.classificacao_racao && produto.classificacao_racao !== "nao"),
        e_granel:
          Boolean(produto.e_granel) || (produto.nome || "").toLowerCase().includes("granel"),
        classificacao_racao:
          produto.classificacao_racao && produto.classificacao_racao !== "sim"
            ? produto.classificacao_racao
            : "",
        peso_embalagem: produto.peso_embalagem || "",
        tabela_nutricional: produto.tabela_nutricional || "",
        tabela_consumo: produto.tabela_consumo || "",
        categoria_racao: produto.categoria_racao || "",
        especies_indicadas: produto.especies_indicadas || "both",
        linha_racao_id: produto.linha_racao_id || "",
        porte_animal_id: produto.porte_animal_id || "",
        fase_publico_id: produto.fase_publico_id || "",
        tipo_tratamento_id: produto.tipo_tratamento_id || "",
        sabor_proteina_id: produto.sabor_proteina_id || "",
        apresentacao_peso_id: produto.apresentacao_peso_id || "",
      });
      setLoading(false);

      const carregarPredecessor = async () => {
        if (!produto.produto_predecessor_id) return;
        const predecessorRes = await getProduto(produto.produto_predecessor_id);
        if (!requestAindaAtiva()) return;
        setPredecessorInfo({
          id: predecessorRes.data.id,
          codigo: predecessorRes.data.codigo,
          nome: predecessorRes.data.nome,
          motivo_descontinuacao: produto.motivo_descontinuacao,
          data_descontinuacao: produto.predecessor?.data_descontinuacao,
        });
      };

      const carregarSucessor = async () => {
        if (!produto.data_descontinuacao) return;
        const sucessoresResponse = await api.get("/produtos/", {
          params: { produto_predecessor_id: produto.id, ativo: null },
        });
        if (!requestAindaAtiva()) return;
        const sucessores = Array.isArray(sucessoresResponse.data)
          ? sucessoresResponse.data
          : sucessoresResponse.data.items || [];
        if (sucessores.length > 0) {
          const sucessor = sucessores[0];
          setSucessorInfo({
            id: sucessor.id,
            codigo: sucessor.codigo,
            nome: sucessor.nome,
            motivo_descontinuacao: produto.motivo_descontinuacao,
            data_descontinuacao: produto.data_descontinuacao,
          });
        }
      };

      const carregarImagens = async () => {
        const imagensRes = await api.get(`/produtos/${id}/imagens`);
        if (requestAindaAtiva()) setImagens(imagensRes.data || []);
      };

      const carregarLotesProduto = async () => {
        const lotesRes = await getLotes(id);
        if (!requestAindaAtiva()) return;
        const lotesCarregados = lotesRes.data || [];
        setLotes(lotesCarregados);
        if (lotesCarregados.length > 0 && !produto.controle_lote) {
          setFormData((prev) => ({ ...prev, controle_lote: true }));
        }
      };

      const carregarFornecedoresProduto = async () => {
        const fornecedoresResponse = await getFornecedoresProduto(id);
        if (requestAindaAtiva()) setFornecedores(fornecedoresResponse.data || []);
      };

      const resultadosComplementares = await Promise.allSettled([
        carregarPredecessor(),
        carregarSucessor(),
        carregarImagens(),
        carregarLotesProduto(),
        carregarFornecedoresProduto(),
        carregarFiscal(produto, requestAindaAtiva),
      ]);

      resultadosComplementares.forEach((resultado, indice) => {
        if (resultado.status === "rejected") {
          console.error(`Erro ao carregar complemento ${indice + 1} do produto:`, resultado.reason);
        }
      });
    } catch (error) {
      if (!requestAindaAtiva()) return;
      console.error("❌ Erro ao carregar produto:", error);
      setErroCarregamento(
        error.response?.data?.detail || error.message || "Produto não encontrado.",
      );
    } finally {
      if (requestAindaAtiva()) setLoading(false);
    }
  };

  const carregarProdutoParaClone = async () => {
    try {
      setLoading(true);
      setErroCarregamento(null);
      setPredecessorInfo(null);
      setSucessorInfo(null);
      setImagens([]);
      setLotes([]);
      setFornecedores([]);

      const response = await getProduto(cloneId);
      const produto = response.data;
      const clone = montarEstadoProdutoClonado(produto);

      let margem = "";
      if (clone.preco_custo && clone.preco_venda && Number(clone.preco_custo) > 0) {
        const margemCalculada = calcularMargemSobreVenda(
          Number(clone.preco_custo),
          Number(clone.preco_venda),
        );
        margem = margemCalculada === null ? "" : margemCalculada.toFixed(2);
      }

      setFormData((prev) => ({
        ...prev,
        ...clone,
        margem,
      }));
    } catch (error) {
      console.error("Erro ao carregar produto para clone:", error);
      setErroCarregamento(
        error.response?.data?.detail || error.message || "Produto não encontrado.",
      );
    } finally {
      setLoading(false);
    }
  };

  const salvarFiscal = async (produto) => {
    const payload = {
      origem_mercadoria: formData.tributacao.origem_mercadoria,
      ncm: formData.tributacao.ncm,
      cest: formData.tributacao.cest,
      cfop: formData.tributacao.cfop,
      cst_icms: formData.tributacao.cst_icms,
      icms_aliquota: formData.tributacao.icms_aliquota,
      icms_st: formData.tributacao.icms_st,
      pis_aliquota: formData.tributacao.pis_aliquota,
      cofins_aliquota: formData.tributacao.cofins_aliquota,
    };

    if (produto.tipo_produto === "KIT") {
      await api.put(`/produtos/${produto.id}/kit/fiscal`, payload);
    } else {
      await api.put(`/produtos/${produto.id}/fiscal`, payload);
    }
  };

  useEffect(() => {
    carregarDadosAuxiliares();
  }, []);

  useEffect(() => {
    if (isEdicao) {
      carregarProduto();
    } else if (cloneId) {
      carregarProdutoParaClone();
    }

    return () => {
      produtoRequestRef.current += 1;
    };
  }, [id, isEdicao, cloneId]);

  return {
    carregarDadosAuxiliares,
    carregarProdutoParaClone,
    carregarProduto,
    salvarFiscal,
  };
}
