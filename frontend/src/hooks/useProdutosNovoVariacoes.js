import { useEffect, useState } from 'react';
import { createProduto, deleteProduto, getProdutoVariacoes } from '../api/produtos';

const VARIACAO_INICIAL = {
  sku: '',
  nome: '',
  codigo_barras: '',
  preco_custo: '',
  preco_venda: '',
  estoque_minimo: 0,
  e_kit: false,
  e_kit_fisico: false,
  composicao_kit: [],
};

export default function useProdutosNovoVariacoes({
  id,
  isEdicao,
  abaAtiva,
  formData,
  navigate,
}) {
  const [variacoes, setVariacoes] = useState([]);
  const [novaVariacao, setNovaVariacao] = useState(VARIACAO_INICIAL);
  const [mostrarFormVariacao, setMostrarFormVariacao] = useState(false);

  const carregarVariacoes = async () => {
    try {
      const response = await getProdutoVariacoes(id);
      setVariacoes(response.data || []);
    } catch (error) {
      console.error('Erro ao carregar variações:', error);
    }
  };

  const resetNovaVariacao = () => {
    setNovaVariacao(VARIACAO_INICIAL);
  };

  const handleToggleFormVariacao = () => {
    setMostrarFormVariacao((prev) => !prev);
  };

  const handleCancelarVariacao = () => {
    setMostrarFormVariacao(false);
    resetNovaVariacao();
  };

  const handleSalvarVariacao = async () => {
    if (!novaVariacao.sku || !novaVariacao.nome || !novaVariacao.preco_venda) {
      alert('Preencha SKU, Nome e Preço de Venda');
      return;
    }

    try {
      const dadosVariacao = {
        codigo: novaVariacao.sku,
        nome: `${formData.nome} - ${novaVariacao.nome}`,
        codigo_barras: novaVariacao.codigo_barras || null,
        preco_custo: parseFloat(novaVariacao.preco_custo) || 0,
        preco_venda: parseFloat(novaVariacao.preco_venda),
        estoque_minimo: parseInt(novaVariacao.estoque_minimo, 10) || 0,
        tipo_produto: 'VARIACAO',
        produto_pai_id: parseInt(id, 10),
        categoria_id: formData.categoria_id || null,
        marca_id: formData.marca_id || null,
        unidade: formData.unidade || 'UN',
      };

      if (novaVariacao.e_kit) {
        dadosVariacao.tipo_kit = 'VIRTUAL';
        dadosVariacao.e_kit_fisico = false;
      }

      const respostaCriacao = await createProduto(dadosVariacao);
      const variacaoCriada = respostaCriacao?.data;

      if (novaVariacao.e_kit && variacaoCriada?.id) {
        alert('Variação-kit cadastrada com sucesso! Agora defina a composição.');
        navigate(`/produtos/${variacaoCriada.id}/editar?aba=9`);
        return;
      }

      alert('Variação cadastrada com sucesso!');
      setMostrarFormVariacao(false);
      resetNovaVariacao();
      await carregarVariacoes();
    } catch (error) {
      console.error('Erro ao cadastrar variação:', error);
      alert(error.response?.data?.detail || 'Erro ao cadastrar variação');
    }
  };

  const handleExcluirVariacao = async (variacao) => {
    if (!window.confirm(`Deseja excluir a variação ${variacao.nome}?`)) {
      return;
    }

    try {
      await deleteProduto(variacao.id);
      alert('Variação excluída com sucesso!');
      await carregarVariacoes();
    } catch (error) {
      console.error('Erro ao excluir variação:', error);
      alert('Erro ao excluir variação');
    }
  };

  useEffect(() => {
    if (isEdicao && abaAtiva === 8 && formData.tipo_produto === 'PAI') {
      carregarVariacoes();
    }
  }, [abaAtiva, formData.tipo_produto, id, isEdicao]);

  return {
    variacoes,
    novaVariacao,
    setNovaVariacao,
    mostrarFormVariacao,
    setMostrarFormVariacao,
    handleToggleFormVariacao,
    handleCancelarVariacao,
    handleSalvarVariacao,
    handleExcluirVariacao,
  };
}
