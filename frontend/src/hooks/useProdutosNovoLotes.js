import { useState } from 'react';
import { deleteLote, entradaEstoque, getLotes, updateLote } from '../api/produtos';

const ENTRADA_INICIAL = {
  quantidade: '',
  nome_lote: '',
  data_fabricacao: '',
  data_validade: '',
  preco_custo: '',
};

export default function useProdutosNovoLotes({ id }) {
  const [lotes, setLotes] = useState([]);
  const [modalEntrada, setModalEntrada] = useState(false);
  const [entradaData, setEntradaData] = useState(ENTRADA_INICIAL);
  const [modalEdicaoLote, setModalEdicaoLote] = useState(false);
  const [loteEmEdicao, setLoteEmEdicao] = useState(null);

  const recarregarLotes = async () => {
    const lotesRes = await getLotes(id);
    setLotes(lotesRes.data);
  };

  const handleEntradaEstoque = async () => {
    if (!entradaData.quantidade || !entradaData.preco_custo) {
      alert('Preencha quantidade e preÃ§o de custo!');
      return;
    }

    try {
      const numeroLote = entradaData.nome_lote || `LOTE-${Date.now()}`;
      const dataFabricacao = entradaData.data_fabricacao
        ? new Date(`${entradaData.data_fabricacao}T00:00:00`).toISOString()
        : null;
      const dataValidade = entradaData.data_validade
        ? new Date(`${entradaData.data_validade}T23:59:59`).toISOString()
        : null;

      await entradaEstoque(id, {
        nome_lote: numeroLote,
        quantidade: parseFloat(entradaData.quantidade),
        preco_custo: parseFloat(entradaData.preco_custo),
        data_fabricacao: dataFabricacao,
        data_validade: dataValidade,
        observacoes: entradaData.observacoes || null,
      });

      alert('Entrada de estoque realizada com sucesso!');
      setModalEntrada(false);
      setEntradaData(ENTRADA_INICIAL);
      await recarregarLotes();
    } catch (error) {
      console.error('Erro ao registrar entrada:', error);
      alert(error.response?.data?.detail || 'Erro ao registrar entrada de estoque');
    }
  };

  const handleEditarLote = (lote) => {
    setLoteEmEdicao({
      id: lote.id,
      nome_lote: lote.nome_lote,
      quantidade_inicial: lote.quantidade_inicial,
      data_fabricacao: lote.data_fabricacao?.split('T')[0] || '',
      data_validade: lote.data_validade?.split('T')[0] || '',
      custo_unitario: lote.custo_unitario,
    });
    setModalEdicaoLote(true);
  };

  const handleSalvarEdicaoLote = async () => {
    try {
      const dataFabricacao = loteEmEdicao.data_fabricacao
        ? new Date(`${loteEmEdicao.data_fabricacao}T00:00:00`).toISOString()
        : null;
      const dataValidade = loteEmEdicao.data_validade
        ? new Date(`${loteEmEdicao.data_validade}T23:59:59`).toISOString()
        : null;

      await updateLote(id, loteEmEdicao.id, {
        nome_lote: loteEmEdicao.nome_lote,
        quantidade_inicial: parseFloat(loteEmEdicao.quantidade_inicial),
        data_fabricacao: dataFabricacao,
        data_validade: dataValidade,
        custo_unitario: parseFloat(loteEmEdicao.custo_unitario),
      });

      alert('Lote atualizado com sucesso!');
      setModalEdicaoLote(false);
      setLoteEmEdicao(null);
      await recarregarLotes();
    } catch (error) {
      console.error('Erro ao atualizar lote:', error);
      alert(error.response?.data?.detail || 'Erro ao atualizar lote');
    }
  };

  const handleExcluirLote = async (lote) => {
    if (
      !window.confirm(
        `Deseja realmente excluir o lote ${lote.nome_lote}?\n\nQuantidade: ${lote.quantidade_disponivel} unidades\nIsso removerá o registro de entrada do estoque.`,
      )
    ) {
      return;
    }

    try {
      await deleteLote(id, lote.id);
      alert('Lote excluído com sucesso!');
      await recarregarLotes();
    } catch (error) {
      console.error('Erro ao excluir lote:', error);
      alert(error.response?.data?.detail || 'Erro ao excluir lote');
    }
  };

  return {
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
  };
}
