/**
 * ModalRemoverCredito
 *
 * Modal para remover crédito de um cliente.
 * Mesmo padrão visual do ModalAdicionarCredito.
 *
 * Props:
 *   cliente     {id, nome, credito} — dados do cliente
 *   onConfirmar (novoSaldo) => void — chamado com o novo saldo após salvar
 *   onClose     () => void
 */

import { useState } from 'react';
import { X, MinusCircle, AlertCircle, Info } from 'lucide-react';
import CurrencyInput from './CurrencyInput';
import { formatBRL } from '../utils/formatters';
import api from '../api';

export default function ModalRemoverCredito({ cliente, onConfirmar, onClose }) {
  const creditoDisponivel = parseFloat(cliente?.credito || 0);

  const [valor, setValor] = useState(0);
  const [motivo, setMotivo] = useState('Ajuste manual');
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState('');

  const handleConfirmar = async () => {
    if (!valor || valor <= 0) {
      setErro('Informe um valor maior que zero.');
      return;
    }
    if (valor > creditoDisponivel) {
      setErro(`Valor excede o crédito disponível (R$ ${formatBRL(creditoDisponivel)}).`)
      return;
    }
    if (!motivo.trim()) {
      setErro('Informe o motivo da remoção de crédito.');
      return;
    }

    setErro('');
    setLoading(true);

    try {
      const response = await api.post(`/clientes/${cliente.id}/credito/remover`, {
        valor,
        motivo: motivo.trim(),
      });

      onConfirmar && onConfirmar(response.data.credito_atual);
      onClose(); // fecha automaticamente após confirmar
    } catch (error) {
      setErro(
        error.response?.data?.detail ||
          'Erro ao remover crédito. Tente novamente.'
      );
    } finally {
      setLoading(false);
    }
  };

  // --- Tela principal ---
  return (
    <div className="fixed inset-0 z-[300] flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm mx-4 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-red-500 to-rose-600 px-6 py-4 text-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <MinusCircle className="w-6 h-6 flex-shrink-0" />
            <div>
              <h2 className="text-base font-bold leading-tight">Remover Crédito</h2>
              <p className="text-sm text-red-100 truncate max-w-[180px]">{cliente?.nome}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-white/20 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {/* Saldo atual */}
          <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-xl px-4 py-3">
            <Info className="w-4 h-4 text-red-500 flex-shrink-0" />
            <span className="text-sm text-red-800">
              Crédito disponível:{' '}
              <strong>R$ {formatBRL(creditoDisponivel)}</strong>
            </span>
          </div>

          {creditoDisponivel <= 0 && (
            <div className="flex items-start gap-2 bg-yellow-50 border border-yellow-200 rounded-xl px-4 py-3">
              <AlertCircle className="w-4 h-4 text-yellow-500 flex-shrink-0 mt-0.5" />
              <span className="text-sm text-yellow-800">
                Este cliente não possui crédito disponível para remover.
              </span>
            </div>
          )}

          {/* Campo de valor */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Valor a remover
            </label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 font-medium select-none">
                R$
              </span>
              <CurrencyInput
                value={valor}
                onChange={setValor}
                placeholder="0,00"
                className="w-full pl-10 pr-4 py-3 text-lg font-bold border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-red-400 focus:border-red-400 outline-none transition-colors"
                autoFocus
              />
            </div>
          </div>

          {/* Campo motivo */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Motivo
            </label>
            <input
              type="text"
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              placeholder="Ex: Estorno, ajuste manual..."
              className="w-full px-4 py-2.5 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-red-400 focus:border-red-400 outline-none transition-colors text-sm"
              maxLength={200}
            />
          </div>

          {/* Erro */}
          {erro && (
            <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-xl px-4 py-3">
              <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
              <span className="text-sm text-red-700">{erro}</span>
            </div>
          )}
        </div>

        {/* Rodapé */}
        <div className="px-6 pb-6 flex gap-3">
          <button
            onClick={onClose}
            disabled={loading}
            className="flex-1 py-2.5 border-2 border-gray-200 text-gray-600 font-semibold rounded-xl hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            onClick={handleConfirmar}
            disabled={loading || !valor || valor <= 0 || creditoDisponivel <= 0}
            className="flex-1 py-2.5 bg-red-500 hover:bg-red-600 text-white font-bold rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                Removendo...
              </>
            ) : (
              'Remover Crédito'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
