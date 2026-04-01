import { useEffect, useState } from 'react';
import api from '../api';

export default function useProdutosNovoKit({ abaAtiva, formData, setFormData }) {
  const [produtosDisponiveis, setProdutosDisponiveis] = useState([]);
  const [produtoKitSelecionado, setProdutoKitSelecionado] = useState('');
  const [quantidadeKit, setQuantidadeKit] = useState('');
  const [estoqueVirtualKit, setEstoqueVirtualKit] = useState(0);
  const [buscaComponente, setBuscaComponente] = useState('');
  const [dropdownComponenteVisivel, setDropdownComponenteVisivel] = useState(false);

  const calcularEstoqueVirtualKit = (composicao) => {
    if (!composicao || composicao.length === 0) {
      setEstoqueVirtualKit(0);
      return;
    }

    const possibilidades = composicao.map((item) => {
      const estoqueComponente = item.estoque_componente || 0;
      const quantidadeNecessaria = item.quantidade || 1;
      return Math.floor(estoqueComponente / quantidadeNecessaria);
    });

    const estoqueMin = Math.min(...possibilidades);
    setEstoqueVirtualKit(estoqueMin >= 0 ? estoqueMin : 0);
  };

  const carregarProdutosDisponiveis = async () => {
    try {
      const response = await api.get('/produtos/', {
        params: {
          apenas_ativos: true,
          tipo_produto: 'SIMPLES',
          page_size: 2000,
        },
      });
      setProdutosDisponiveis(response.data.items || []);
    } catch (error) {
      console.error('Erro ao carregar produtos:', error);
      setProdutosDisponiveis([]);
    }
  };

  const adicionarProdutoKit = () => {
    if (!produtoKitSelecionado || !quantidadeKit || quantidadeKit <= 0) {
      alert('Selecione um produto e informe a quantidade!');
      return;
    }

    const produtoId = parseInt(produtoKitSelecionado, 10);
    const jaExiste = formData.composicao_kit.find((item) => item.produto_id === produtoId);

    if (jaExiste) {
      alert('Este produto já foi adicionado ao kit!');
      return;
    }

    const produtoSelecionado = produtosDisponiveis.find((produto) => produto.id === produtoId);
    if (!produtoSelecionado) {
      alert('Produto selecionado não encontrado.');
      return;
    }

    const novoItem = {
      produto_componente_id: produtoSelecionado.id,
      produto_id: produtoSelecionado.id,
      produto_nome: produtoSelecionado.nome,
      produto_sku: produtoSelecionado.codigo,
      quantidade: parseFloat(quantidadeKit),
      estoque_componente: produtoSelecionado.estoque_atual || 0,
    };

    const novaComposicao = [...formData.composicao_kit, novoItem];
    setFormData((prev) => ({
      ...prev,
      composicao_kit: novaComposicao,
    }));

    setProdutoKitSelecionado('');
    setQuantidadeKit('');
    setBuscaComponente('');
    calcularEstoqueVirtualKit(novaComposicao);
  };

  const removerProdutoKit = (produtoId) => {
    const novaComposicao = formData.composicao_kit.filter((item) => item.produto_id !== produtoId);

    setFormData((prev) => ({
      ...prev,
      composicao_kit: novaComposicao,
    }));

    calcularEstoqueVirtualKit(novaComposicao);
  };

  useEffect(() => {
    const ehKit =
      formData.tipo_produto === 'KIT' ||
      (formData.tipo_produto === 'VARIACAO' && formData.tipo_kit);

    if (abaAtiva === 9 && ehKit) {
      carregarProdutosDisponiveis();
      if (formData.composicao_kit && formData.composicao_kit.length > 0) {
        calcularEstoqueVirtualKit(formData.composicao_kit);
      }
    }
  }, [abaAtiva, formData.composicao_kit, formData.tipo_produto, formData.tipo_kit]);

  return {
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
  };
}
