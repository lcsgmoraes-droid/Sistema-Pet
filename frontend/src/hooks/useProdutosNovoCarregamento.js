import { useEffect } from 'react';
import api from '../api';
import {
  calcularMarkup,
  getCategorias,
  getDepartamentos,
  getFornecedoresProduto,
  getLotes,
  getMarcas,
  getProduto,
} from '../api/produtos';

const construirListaHierarquica = (categorias, parentId = null, nivel = 0) => {
  let resultado = [];

  const filhos = categorias.filter((categoria) => categoria.categoria_pai_id === parentId);

  filhos.forEach((categoria) => {
    const indentacao = '\u00a0\u00a0\u00a0\u00a0'.repeat(nivel);
    const seta = nivel > 0 ? '→ ' : '';

    resultado.push({
      ...categoria,
      nomeFormatado: indentacao + seta + categoria.nome,
      nivel,
    });

    resultado = resultado.concat(
      construirListaHierarquica(categorias, categoria.id, nivel + 1),
    );
  });

  return resultado;
};

export default function useProdutosNovoCarregamento({
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
}) {
  const carregarOpcoesRacao = async () => {
    try {
      const [linhas, portes, fases, tratamentos, sabores, apresentacoes] = await Promise.all([
        api.get('/opcoes-racao/linhas', { params: { apenas_ativos: true } }),
        api.get('/opcoes-racao/portes', { params: { apenas_ativos: true } }),
        api.get('/opcoes-racao/fases', { params: { apenas_ativos: true } }),
        api.get('/opcoes-racao/tratamentos', { params: { apenas_ativos: true } }),
        api.get('/opcoes-racao/sabores', { params: { apenas_ativos: true } }),
        api.get('/opcoes-racao/apresentacoes', { params: { apenas_ativos: true } }),
      ]);

      setOpcoesLinhas(linhas.data);
      setOpcoesPortes(portes.data);
      setOpcoesFases(fases.data);
      setOpcoesTratamentos(tratamentos.data);
      setOpcoesSabores(sabores.data);
      setOpcoesApresentacoes(apresentacoes.data);
    } catch (error) {
      console.error('Erro ao carregar opções de ração:', error);
    }
  };

  const carregarDadosAuxiliares = async () => {
    try {
      const [categoriasResponse, marcasResponse, departamentosResponse, clientesResponse] =
        await Promise.all([
          getCategorias(),
          getMarcas(),
          getDepartamentos(),
          api.get('/clientes/', {
            params: { tipo_cadastro: 'fornecedor', apenas_ativos: true },
          }),
        ]);

      setCategorias(categoriasResponse.data);
      setCategoriasHierarquicas(construirListaHierarquica(categoriasResponse.data));
      setMarcas(marcasResponse.data);
      setDepartamentos(departamentosResponse.data);
      setClientes(
        Array.isArray(clientesResponse.data)
          ? clientesResponse.data
          : (clientesResponse.data.items || []),
      );

      await carregarOpcoesRacao();
    } catch (error) {
      console.error('Erro ao carregar dados auxiliares:', error);
    }
  };

  const carregarFiscal = async (produto) => {
    try {
      const isKit = produto.tipo_produto === 'KIT';
      const { data } = isKit
        ? await api.get(`/produtos/${produto.id}/kit/fiscal`)
        : await api.get(`/produtos/${produto.id}/fiscal`);

      setFormData((prev) => ({
        ...prev,
        tributacao: {
          origem: data.origem,
          herdado_da_empresa: data.herdado_da_empresa,
          origem_mercadoria: data.origem_mercadoria ?? '0',
          ncm: data.ncm ?? '',
          cest: data.cest ?? '',
          cfop: data.cfop ?? '',
          cst_icms: data.cst_icms ?? '',
          icms_aliquota: data.icms_aliquota ?? '',
          icms_st: data.icms_st ?? false,
          pis_aliquota: data.pis_aliquota ?? '',
          cofins_aliquota: data.cofins_aliquota ?? '',
        },
      }));
    } catch (error) {
      console.error('Erro ao carregar fiscal:', error);
    }
  };

  const carregarProduto = async () => {
    try {
      setLoading(true);
      setPredecessorInfo(null);
      setSucessorInfo(null);

      const response = await getProduto(id);
      const produto = response.data;

      let markup = '';
      if (produto.preco_custo && produto.preco_venda && produto.preco_custo > 0) {
        markup = calcularMarkup(produto.preco_custo, produto.preco_venda).toFixed(2);
      }

      setFormData({
        ...produto,
        sku: produto.codigo || '',
        codigo: produto.codigo || '',
        nome: produto.nome || '',
        codigo_barras: produto.codigo_barras || '',
        categoria_id: produto.categoria_id || '',
        marca_id: produto.marca_id || '',
        departamento_id: produto.departamento_id || '',
        unidade: produto.unidade || 'UN',
        descricao: produto.descricao_curta || '',
        tipo: produto.tipo || 'produto',
        preco_custo: produto.preco_custo || '',
        preco_venda: produto.preco_venda || '',
        preco_promocional: produto.preco_promocional || '',
        data_inicio_promocao: produto.promocao_inicio || '',
        data_fim_promocao: produto.promocao_fim || '',
        preco_ecommerce: produto.preco_ecommerce ?? '',
        preco_ecommerce_promo: produto.preco_ecommerce_promo ?? '',
        preco_ecommerce_promo_inicio: produto.preco_ecommerce_promo_inicio ?? '',
        preco_ecommerce_promo_fim: produto.preco_ecommerce_promo_fim ?? '',
        preco_app: produto.preco_app ?? '',
        preco_app_promo: produto.preco_app_promo ?? '',
        preco_app_promo_inicio: produto.preco_app_promo_inicio ?? '',
        preco_app_promo_fim: produto.preco_app_promo_fim ?? '',
        anunciar_ecommerce: produto.anunciar_ecommerce ?? true,
        anunciar_app: produto.anunciar_app ?? true,
        ativo: produto.ativo ?? true,
        situacao: produto.situacao ?? true,
        estoque_minimo: produto.estoque_minimo || '',
        estoque_maximo: produto.estoque_maximo || '',
        controle_lote: produto.controle_lote ?? true,
        markup,
        tipo_produto: produto.tipo_produto || 'SIMPLES',
        produto_pai_id: produto.produto_pai_id || null,
        tipo_kit: produto.tipo_kit || null,
        e_kit_fisico: produto.e_kit_fisico || false,
        composicao_kit: produto.composicao_kit || [],
        origem: produto.origem || '0',
        ncm: produto.ncm || '',
        cest: produto.cest || '',
        cfop: produto.cfop || '',
        aliquota_icms: produto.aliquota_icms || '',
        aliquota_pis: produto.aliquota_pis || '',
        aliquota_cofins: produto.aliquota_cofins || '',
        tem_recorrencia: produto.tem_recorrencia || false,
        tipo_recorrencia: produto.tipo_recorrencia || 'monthly',
        intervalo_dias: produto.intervalo_dias || '',
        numero_doses: produto.numero_doses || '',
        especie_compativel: produto.especie_compativel || 'both',
        observacoes_recorrencia: produto.observacoes_recorrencia || '',
        eh_racao:
          typeof produto.eh_racao === 'boolean'
            ? produto.eh_racao
            : produto.tipo === 'ração' ||
              produto.tipo === 'racao' ||
              Boolean(produto.linha_racao_id) ||
              Boolean(produto.classificacao_racao && produto.classificacao_racao !== 'nao'),
        classificacao_racao:
          produto.classificacao_racao && produto.classificacao_racao !== 'sim'
            ? produto.classificacao_racao
            : '',
        peso_embalagem: produto.peso_embalagem || '',
        tabela_nutricional: produto.tabela_nutricional || '',
        tabela_consumo: produto.tabela_consumo || '',
        categoria_racao: produto.categoria_racao || '',
        especies_indicadas: produto.especies_indicadas || 'both',
        linha_racao_id: produto.linha_racao_id || '',
        porte_animal_id: produto.porte_animal_id || '',
        fase_publico_id: produto.fase_publico_id || '',
        tipo_tratamento_id: produto.tipo_tratamento_id || '',
        sabor_proteina_id: produto.sabor_proteina_id || '',
        apresentacao_peso_id: produto.apresentacao_peso_id || '',
      });

      if (produto.produto_predecessor_id) {
        try {
          const predecessorRes = await getProduto(produto.produto_predecessor_id);
          setPredecessorInfo({
            id: predecessorRes.data.id,
            codigo: predecessorRes.data.codigo,
            nome: predecessorRes.data.nome,
            motivo_descontinuacao: produto.motivo_descontinuacao,
            data_descontinuacao: produto.predecessor?.data_descontinuacao,
          });
        } catch (error) {
          console.error('Erro ao carregar predecessor:', error);
        }
      }

      if (produto.data_descontinuacao) {
        try {
          const sucessoresResponse = await api.get('/produtos/', {
            params: {
              produto_predecessor_id: produto.id,
              ativo: null,
            },
          });

          const sucessores = Array.isArray(sucessoresResponse.data)
            ? sucessoresResponse.data
            : (sucessoresResponse.data.items || []);

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
        } catch (error) {
          console.error('❌ Erro ao carregar sucessor:', error);
        }
      }

      try {
        const imagensRes = await api.get(`/produtos/${id}/imagens`);
        setImagens(imagensRes.data || []);
      } catch (error) {
        console.error('Erro ao carregar imagens:', error);
        setImagens([]);
      }

      try {
        const lotesRes = await getLotes(id);
        const lotesCarregados = lotesRes.data || [];
        setLotes(lotesCarregados);
        if (lotesCarregados.length > 0 && !produto.controle_lote) {
          setFormData((prev) => ({ ...prev, controle_lote: true }));
        }
      } catch (error) {
        console.error('Erro ao carregar lotes:', error);
        setLotes([]);
      }

      const fornecedoresResponse = await getFornecedoresProduto(id);
      setFornecedores(fornecedoresResponse.data);

      await carregarFiscal(produto);
    } catch (error) {
      console.error('❌ Erro ao carregar produto:', error);
      alert('Erro ao carregar produto: ' + (error.response?.data?.detail || error.message));
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

    if (produto.tipo_produto === 'KIT') {
      await api.put(`/produtos/${produto.id}/kit/fiscal`, payload);
    } else {
      await api.put(`/produtos/${produto.id}/fiscal`, payload);
    }
  };

  useEffect(() => {
    carregarDadosAuxiliares();

    if (isEdicao) {
      carregarProduto();
    }
  }, [id, isEdicao]);

  return {
    carregarDadosAuxiliares,
    carregarProduto,
    salvarFiscal,
  };
}
