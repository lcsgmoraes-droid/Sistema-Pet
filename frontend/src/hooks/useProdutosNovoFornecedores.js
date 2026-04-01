import { useState } from 'react';
import {
  addFornecedorProduto,
  deleteFornecedorProduto,
  getFornecedoresProduto,
  updateFornecedorProduto,
} from '../api/produtos';

const FORNECEDOR_INICIAL = {
  fornecedor_id: '',
  codigo_fornecedor: '',
  preco_custo: '',
  prazo_entrega: '',
  estoque_fornecedor: '',
  e_principal: false,
};

export default function useProdutosNovoFornecedores({ id }) {
  const [fornecedores, setFornecedores] = useState([]);
  const [modalFornecedor, setModalFornecedor] = useState(false);
  const [fornecedorEdit, setFornecedorEdit] = useState(null);
  const [fornecedorData, setFornecedorData] = useState(FORNECEDOR_INICIAL);

  const recarregarFornecedores = async () => {
    const fornecedorRes = await getFornecedoresProduto(id);
    setFornecedores(fornecedorRes.data);
  };

  const handleAddFornecedor = () => {
    setFornecedorEdit(null);
    setFornecedorData(FORNECEDOR_INICIAL);
    setModalFornecedor(true);
  };

  const handleEditFornecedor = (fornecedor) => {
    setFornecedorEdit(fornecedor);
    setFornecedorData({
      fornecedor_id: fornecedor.fornecedor_id,
      codigo_fornecedor: fornecedor.codigo_fornecedor || '',
      preco_custo: fornecedor.preco_custo || '',
      prazo_entrega: fornecedor.prazo_entrega || '',
      estoque_fornecedor: fornecedor.estoque_fornecedor || '',
      e_principal: fornecedor.e_principal || false,
    });
    setModalFornecedor(true);
  };

  const handleSaveFornecedor = async () => {
    if (!fornecedorData.fornecedor_id) {
      alert('Selecione um fornecedor');
      return;
    }

    try {
      const dados = {
        ...fornecedorData,
        preco_custo: fornecedorData.preco_custo
          ? parseFloat(fornecedorData.preco_custo)
          : null,
        prazo_entrega: fornecedorData.prazo_entrega
          ? parseInt(fornecedorData.prazo_entrega, 10)
          : null,
        estoque_fornecedor: fornecedorData.estoque_fornecedor
          ? parseFloat(fornecedorData.estoque_fornecedor)
          : null,
      };

      if (fornecedorEdit) {
        await updateFornecedorProduto(fornecedorEdit.id, dados);
        alert('Fornecedor atualizado!');
      } else {
        await addFornecedorProduto(id, dados);
        alert('Fornecedor vinculado!');
      }

      await recarregarFornecedores();
      setModalFornecedor(false);
    } catch (error) {
      console.error('Erro ao salvar fornecedor:', error);
      alert(error.response?.data?.detail || 'Erro ao salvar fornecedor');
    }
  };

  const handleDeleteFornecedor = async (fornecedorId) => {
    if (!window.confirm('Deseja realmente desvincular este fornecedor?')) {
      return;
    }

    try {
      await deleteFornecedorProduto(fornecedorId);
      await recarregarFornecedores();
      alert('Fornecedor desvinculado!');
    } catch (error) {
      console.error('Erro ao desvincular fornecedor:', error);
      alert('Erro ao desvincular fornecedor');
    }
  };

  return {
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
  };
}
