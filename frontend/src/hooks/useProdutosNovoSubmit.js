import { createProduto, updateProduto } from '../api/produtos';
import { debugLog } from '../utils/debug';

export default function useProdutosNovoSubmit({
  id,
  isEdicao,
  formData,
  navigate,
  salvarFiscal,
  setSalvando,
}) {
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.nome) {
      alert('Preencha o campo Nome');
      return;
    }

    if (formData.tipo_produto !== 'PAI' && !formData.preco_venda) {
      alert('Preencha o Preço de Venda');
      return;
    }

    if (!formData.codigo && !formData.sku) {
      alert('Preencha o campo SKU/Código');
      return;
    }

    try {
      setSalvando(true);
      const skuNormalizado = (formData.sku || formData.codigo || '').trim().toUpperCase();

      const composicaoKitNormalizada = (formData.composicao_kit || []).map((item) => ({
        produto_componente_id: item.produto_componente_id || item.produto_id,
        quantidade: item.quantidade ? parseFloat(item.quantidade) : 1,
        ordem: Number.isFinite(Number(item.ordem)) ? Number(item.ordem) : 0,
        opcional: Boolean(item.opcional),
      }));

      const dados = {
        codigo: skuNormalizado,
        nome: formData.nome,
        descricao_curta: formData.descricao || null,
        codigo_barras: formData.codigo_barras || null,
        unidade: formData.unidade || 'UN',
        preco_custo: formData.preco_custo ? parseFloat(formData.preco_custo) : 0,
        preco_venda: parseFloat(formData.preco_venda),
        preco_promocional: formData.preco_promocional ? parseFloat(formData.preco_promocional) : null,
        promocao_inicio: formData.data_inicio_promocao || null,
        promocao_fim: formData.data_fim_promocao || null,
        preco_ecommerce: formData.preco_ecommerce ? parseFloat(formData.preco_ecommerce) : null,
        preco_ecommerce_promo: formData.preco_ecommerce_promo
          ? parseFloat(formData.preco_ecommerce_promo)
          : null,
        preco_ecommerce_promo_inicio: formData.preco_ecommerce_promo_inicio || null,
        preco_ecommerce_promo_fim: formData.preco_ecommerce_promo_fim || null,
        preco_app: formData.preco_app ? parseFloat(formData.preco_app) : null,
        preco_app_promo: formData.preco_app_promo ? parseFloat(formData.preco_app_promo) : null,
        preco_app_promo_inicio: formData.preco_app_promo_inicio || null,
        preco_app_promo_fim: formData.preco_app_promo_fim || null,
        controle_lote: formData.controle_lote || false,
        estoque_minimo: formData.estoque_minimo ? parseInt(formData.estoque_minimo) : 0,
        estoque_maximo: formData.estoque_maximo ? parseInt(formData.estoque_maximo) : null,
        categoria_id: formData.categoria_id ? parseInt(formData.categoria_id) : null,
        marca_id: formData.marca_id ? parseInt(formData.marca_id) : null,
        departamento_id: formData.departamento_id ? parseInt(formData.departamento_id) : null,
        tipo_produto: formData.tipo_produto || 'SIMPLES',
        produto_pai_id: formData.produto_pai_id || null,
        tipo_kit:
          formData.tipo_produto === 'KIT' ||
          (formData.tipo_produto === 'VARIACAO' && formData.tipo_kit)
            ? formData.e_kit_fisico
              ? 'FISICO'
              : 'VIRTUAL'
            : null,
        e_kit_fisico:
          formData.tipo_produto === 'KIT' ||
          (formData.tipo_produto === 'VARIACAO' && formData.tipo_kit)
            ? formData.e_kit_fisico
            : null,
        composicao_kit:
          formData.tipo_produto === 'KIT' ||
          (formData.tipo_produto === 'VARIACAO' && formData.tipo_kit)
            ? composicaoKitNormalizada
            : null,
        produto_predecessor_id: formData.produto_predecessor_id || null,
        motivo_descontinuacao: formData.motivo_descontinuacao || null,
        tem_recorrencia: formData.tem_recorrencia || false,
        tipo_recorrencia: formData.tem_recorrencia ? formData.tipo_recorrencia : null,
        intervalo_dias:
          formData.tem_recorrencia && formData.intervalo_dias
            ? parseInt(formData.intervalo_dias)
            : null,
        numero_doses:
          formData.tem_recorrencia && formData.numero_doses
            ? parseInt(formData.numero_doses)
            : null,
        especie_compativel: formData.tem_recorrencia ? formData.especie_compativel : null,
        observacoes_recorrencia: formData.tem_recorrencia
          ? formData.observacoes_recorrencia
          : null,
        classificacao_racao: formData.classificacao_racao || null,
        peso_embalagem: formData.peso_embalagem ? parseFloat(formData.peso_embalagem) : null,
        tabela_nutricional: formData.tabela_nutricional || null,
        tabela_consumo: formData.tabela_consumo || null,
        categoria_racao: formData.categoria_racao || null,
        especies_indicadas: formData.especies_indicadas || null,
        linha_racao_id: formData.linha_racao_id ? parseInt(formData.linha_racao_id) : null,
        porte_animal_id: formData.porte_animal_id ? parseInt(formData.porte_animal_id) : null,
        fase_publico_id: formData.fase_publico_id ? parseInt(formData.fase_publico_id) : null,
        tipo_tratamento_id: formData.tipo_tratamento_id
          ? parseInt(formData.tipo_tratamento_id)
          : null,
        sabor_proteina_id: formData.sabor_proteina_id
          ? parseInt(formData.sabor_proteina_id)
          : null,
        apresentacao_peso_id: formData.apresentacao_peso_id
          ? parseInt(formData.apresentacao_peso_id)
          : null,
      };

      debugLog('Enviando dados para API:', dados);

      if (isEdicao) {
        await salvarFiscal({ id, tipo_produto: formData.tipo_produto });
        await updateProduto(id, dados);
        alert('Produto atualizado com sucesso!');
        navigate('/produtos');
        return;
      }

      const response = await createProduto(dados);
      const produtoId = response.data.id;

      if (formData.tipo_produto === 'PAI') {
        alert('Produto PAI criado com sucesso! Agora cadastre as variações.');
        navigate(`/produtos/${produtoId}/editar?aba=8`);
        return;
      }

      alert('Produto cadastrado com sucesso!');
      navigate('/produtos');
    } catch (error) {
      console.error('Erro ao salvar produto:', error);
      alert(error.response?.data?.detail || 'Erro ao salvar produto');
    } finally {
      setSalvando(false);
    }
  };

  return { handleSubmit };
}
