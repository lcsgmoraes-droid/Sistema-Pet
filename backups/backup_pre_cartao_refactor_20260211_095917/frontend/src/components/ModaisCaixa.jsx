import { useState } from 'react';
import { X, TrendingUp, TrendingDown, Receipt, ArrowRightLeft, RotateCcw, AlertCircle } from 'lucide-react';
import { adicionarMovimentacao } from '../api/caixa';

/**
 * Modal de Suprimento - Entrada de valores no caixa
 */
export function ModalSuprimento({ caixaId, onClose, onSucesso }) {
  const [valor, setValor] = useState('');
  const [contaOrigem, setContaOrigem] = useState('');
  const [descricao, setDescricao] = useState('');
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState('');

  const handleSalvar = async () => {
    const valorNum = parseFloat(valor);
    if (!valorNum || valorNum <= 0) {
      setErro('Informe um valor válido');
      return;
    }

    setLoading(true);
    try {
      await adicionarMovimentacao(caixaId, {
        tipo: 'suprimento',
        valor: valorNum,
        forma_pagamento: 'Dinheiro',
        conta_origem_nome: contaOrigem || 'Não informado',
        descricao: descricao
      });
      onSucesso();
    } catch (error) {
      setErro(error.response?.data?.detail || 'Erro ao adicionar suprimento');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ModalBase
      titulo="Suprimento para o caixa"
      icone={TrendingUp}
      corIcone="green"
      onClose={onClose}
      erro={erro}
    >
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Conta de origem*
          </label>
          <select
            value={contaOrigem}
            onChange={(e) => setContaOrigem(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Selecione...</option>
            <option value="Dinheiro em mãos">Dinheiro em mãos</option>
            <option value="Caixa geral">Caixa geral</option>
            <option value="Banco">Banco</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Valor*
          </label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">R$</span>
            <input
              type="number"
              step="0.01"
              value={valor}
              onChange={(e) => setValor(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Descrição*
          </label>
          <textarea
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            rows={3}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            placeholder="Motivo do suprimento..."
          />
        </div>

        <div className="flex space-x-3 pt-4">
          <button
            onClick={onClose}
            disabled={loading}
            className="flex-1 px-4 py-2 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg font-medium transition-colors"
          >
            Fechar
          </button>
          <button
            onClick={handleSalvar}
            disabled={loading}
            className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors"
          >
            {loading ? 'Salvando...' : 'Salvar'}
          </button>
        </div>
      </div>
    </ModalBase>
  );
}

/**
 * Modal de Sangria - Retirada de valores do caixa
 */
export function ModalSangria({ caixaId, saldoAtual, onClose, onSucesso }) {
  const [valor, setValor] = useState('');
  const [contaDestino, setContaDestino] = useState('');
  const [descricao, setDescricao] = useState('');
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState('');

  const handleSalvar = async () => {
    const valorNum = parseFloat(valor);
    if (!valorNum || valorNum <= 0) {
      setErro('Informe um valor válido');
      return;
    }

    setLoading(true);
    try {
      await adicionarMovimentacao(caixaId, {
        tipo: 'sangria',
        valor: valorNum,
        forma_pagamento: 'Dinheiro',
        conta_destino_nome: contaDestino || 'Não informado',
        descricao: descricao
      });
      onSucesso();
    } catch (error) {
      setErro(error.response?.data?.detail || 'Erro ao adicionar sangria');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ModalBase
      titulo="Sangria no caixa"
      icone={TrendingDown}
      corIcone="orange"
      onClose={onClose}
      erro={erro}
    >
      <div className="space-y-4">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
          <div className="text-sm text-blue-800">
            <strong>Em caixa:</strong> R$ {saldoAtual.toFixed(2)}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Valor da Sangria*
          </label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">R$</span>
            <input
              type="number"
              step="0.01"
              value={valor}
              onChange={(e) => setValor(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Selecione a conta de destino*
          </label>
          <select
            value={contaDestino}
            onChange={(e) => setContaDestino(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Selecione...</option>
            <option value="Cofre">Cofre</option>
            <option value="Banco">Banco</option>
            <option value="Outro caixa">Outro caixa</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Descrição
          </label>
          <textarea
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            rows={3}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            placeholder="Motivo da sangria..."
          />
        </div>

        <div className="flex space-x-3 pt-4">
          <button
            onClick={onClose}
            disabled={loading}
            className="flex-1 px-4 py-2 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg font-medium transition-colors"
          >
            Fechar
          </button>
          <button
            onClick={handleSalvar}
            disabled={loading}
            className="flex-1 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg font-medium transition-colors"
          >
            {loading ? 'Salvando...' : 'Salvar'}
          </button>
        </div>
      </div>
    </ModalBase>
  );
}

/**
 * Modal de Despesa - Registro de despesas
 */
export function ModalDespesa({ caixaId, onClose, onSucesso }) {
  const [categoria, setCategoria] = useState('');
  const [descricao, setDescricao] = useState('');
  const [valor, setValor] = useState('');
  const [formaPagamento, setFormaPagamento] = useState('Dinheiro');
  const [fornecedor, setFornecedor] = useState('');
  const [documento, setDocumento] = useState('');
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState('');

  const CATEGORIAS = [
    'Água e Luz',
    'Aluguel',
    'Telefone/Internet',
    'Material de Limpeza',
    'Material de Escritório',
    'Manutenção',
    'Outros'
  ];

  const handleSalvar = async () => {
    const valorNum = parseFloat(valor);
    if (!valorNum || valorNum <= 0) {
      setErro('Informe um valor válido');
      return;
    }

    if (!categoria) {
      setErro('Selecione uma categoria');
      return;
    }

    setLoading(true);
    try {
      await adicionarMovimentacao(caixaId, {
        tipo: 'despesa',
        valor: valorNum,
        categoria: categoria,
        descricao: descricao,
        forma_pagamento: formaPagamento,
        fornecedor_nome: fornecedor,
        documento: documento
      });
      onSucesso();
    } catch (error) {
      setErro(error.response?.data?.detail || 'Erro ao adicionar despesa');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ModalBase
      titulo="Despesa no caixa"
      icone={Receipt}
      corIcone="red"
      onClose={onClose}
      erro={erro}
    >
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Categoria*
          </label>
          <select
            value={categoria}
            onChange={(e) => setCategoria(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Selecione...</option>
            {CATEGORIAS.map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Descrição*
          </label>
          <input
            type="text"
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            placeholder="Ex: Conta de luz - Janeiro"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Forma de pagamento*
            </label>
            <select
              value={formaPagamento}
              onChange={(e) => setFormaPagamento(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="Dinheiro">Dinheiro</option>
              <option value="PIX">PIX</option>
              <option value="Cartão de Crédito">Cartão de Crédito</option>
              <option value="Cartão de Débito">Cartão de Débito</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Valor*
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">R$</span>
              <input
                type="number"
                step="0.01"
                value={valor}
                onChange={(e) => setValor(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Fornecedor
            </label>
            <input
              type="text"
              value={fornecedor}
              onChange={(e) => setFornecedor(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Documento / NF
            </label>
            <input
              type="text"
              value={documento}
              onChange={(e) => setDocumento(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="flex space-x-3 pt-4">
          <button
            onClick={onClose}
            disabled={loading}
            className="flex-1 px-4 py-2 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg font-medium transition-colors"
          >
            Fechar
          </button>
          <button
            onClick={handleSalvar}
            disabled={loading}
            className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
          >
            {loading ? 'Salvando...' : 'Salvar'}
          </button>
        </div>
      </div>
    </ModalBase>
  );
}

/**
 * Modal Base - Componente reutilizável para os modais
 */
function ModalBase({ titulo, icone: Icone, corIcone, children, onClose, erro }) {
  const coresIcone = {
    green: 'bg-green-100 text-green-600',
    orange: 'bg-orange-100 text-orange-600',
    red: 'bg-red-100 text-red-600',
    blue: 'bg-blue-100 text-blue-600',
    purple: 'bg-purple-100 text-purple-600'
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center space-x-3">
            <div className={`w-12 h-12 ${coresIcone[corIcone]} rounded-full flex items-center justify-center`}>
              <Icone className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-gray-900">{titulo}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {erro && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2 text-red-700">
              <AlertCircle className="w-5 h-5" />
              <span className="text-sm">{erro}</span>
            </div>
          )}
          {children}
        </div>
      </div>
    </div>
  );
}
