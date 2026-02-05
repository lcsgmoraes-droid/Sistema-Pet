/**
 * Modal de Justificativa para Vendas com Margem Crítica
 * Aparece quando statusMargem === 'vermelho' ou parcelamento proibido
 */
import React, { useState } from 'react';
import { X, AlertTriangle } from 'lucide-react';

const ModalJustificativa = ({ mostrar, onConfirmar, onCancelar, tipo = 'margem_critica' }) => {
  const [justificativa, setJustificativa] = useState('');

  if (!mostrar) return null;

  const mensagens = {
    margem_critica: {
      titulo: '⚠️ Margem Crítica Detectada',
      descricao: 'A margem desta venda está abaixo do recomendado. Por favor, informe o motivo para continuar:',
      placeholder: 'Ex: Cliente preferencial, promoção especial, venda estratégica...'
    },
    parcelamento_proibido: {
      titulo: '⚠️ Parcelamento não Recomendado',
      descricao: 'O número de parcelas selecionado pode comprometer a margem da venda. Justifique para prosseguir:',
      placeholder: 'Ex: Cliente fiel, necessidade de fluxo de caixa, acordo comercial...'
    },
    desconto_alto: {
      titulo: '⚠️ Desconto Elevado',
      descricao: 'O desconto aplicado é alto para a margem atual. Informe a justificativa:',
      placeholder: 'Ex: Acordo com gerência, cliente VIP, liquidação de estoque...'
    }
  };

  const config = mensagens[tipo] || mensagens.margem_critica;

  const handleConfirmar = () => {
    // Permite continuar mesmo sem justificativa (apenas alerta, não bloqueia)
    onConfirmar(justificativa.trim());
    setJustificativa('');
  };

  const handleCancelar = () => {
    setJustificativa('');
    onCancelar();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b bg-yellow-50">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-yellow-600" />
            <h3 className="text-lg font-bold text-gray-900">{config.titulo}</h3>
          </div>
          <button
            onClick={handleCancelar}
            className="p-1 hover:bg-yellow-100 rounded transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          <p className="text-sm text-gray-600">
            {config.descricao}
          </p>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Justificativa (opcional)
            </label>
            <textarea
              value={justificativa}
              onChange={(e) => setJustificativa(e.target.value)}
              className="w-full border border-gray-300 rounded-lg p-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              rows={4}
              placeholder={config.placeholder}
              autoFocus
            />
            <p className="text-xs text-gray-500 mt-1">
              💡 A justificativa será registrada junto com a venda
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex gap-3 p-4 border-t bg-gray-50">
          <button
            onClick={handleCancelar}
            className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors font-medium"
          >
            Cancelar
          </button>
          <button
            onClick={handleConfirmar}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            Continuar
          </button>
        </div>
      </div>
    </div>
  );
};

export default ModalJustificativa;
