import { useState } from 'react';
import api from '../api';

export default function useProdutosNovoPredecessor({ handleChange }) {
  const [mostrarBuscaPredecessor, setMostrarBuscaPredecessor] = useState(false);
  const [produtosBusca, setProdutosBusca] = useState([]);
  const [buscaPredecessor, setBuscaPredecessor] = useState('');
  const [predecessorSelecionado, setPredecessorSelecionado] = useState(null);
  const [predecessorInfo, setPredecessorInfo] = useState(null);
  const [sucessorInfo, setSucessorInfo] = useState(null);

  const handleToggleBuscaPredecessor = (checked) => {
    setMostrarBuscaPredecessor(checked);

    if (!checked) {
      setPredecessorSelecionado(null);
      setBuscaPredecessor('');
      setProdutosBusca([]);
      handleChange('produto_predecessor_id', null);
      handleChange('motivo_descontinuacao', '');
    }
  };

  const handleBuscaPredecessorChange = async (value) => {
    setBuscaPredecessor(value);

    if (value.length >= 2) {
      try {
        const response = await api.get('/produtos/', {
          params: { busca: value, page_size: 10 },
        });
        setProdutosBusca(response.data.items || []);
      } catch (error) {
        console.error('Erro ao buscar produtos:', error);
      }
      return;
    }

    setProdutosBusca([]);
  };

  const handleSelecionarPredecessor = (produto) => {
    setPredecessorSelecionado(produto);
    handleChange('produto_predecessor_id', produto.id);
    setBuscaPredecessor('');
    setProdutosBusca([]);
  };

  const handleRemoverPredecessor = () => {
    setPredecessorSelecionado(null);
    handleChange('produto_predecessor_id', null);
  };

  return {
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
  };
}
