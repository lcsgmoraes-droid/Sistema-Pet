import React, { useState, useEffect } from 'react';
import { parseIdadeParaMeses, formatarIdadeMeses, getPlaceholderIdade, calcularIdadeMeses } from '../helpers/idadeHelper';

/**
 * Campo inteligente para entrada de idade
 * Aceita: anos, meses, anos e meses, data de nascimento
 * Sempre retorna valor em meses via onChange
 */
export default function CampoIdadeInteligente({ 
  value, 
  onChange, 
  name = "idade", 
  label = "Idade",
  className = "",
  mostrarDataNascimento = true,
  required = false
}) {
  const [modo, setModo] = useState('texto'); // 'texto' ou 'data'
  const [textoIdade, setTextoIdade] = useState('');
  const [dataNascimento, setDataNascimento] = useState('');
  const [feedback, setFeedback] = useState('');

  // Inicializar com valor recebido
  useEffect(() => {
    if (value && typeof value === 'number') {
      setTextoIdade(formatarIdadeMeses(value));
    }
  }, [value]);

  const handleTextoChange = (e) => {
    const texto = e.target.value;
    setTextoIdade(texto);
    
    if (!texto) {
      setFeedback('');
      onChange(null);
    }
  };

  const handleTextoBlur = () => {
    if (!textoIdade) {
      setFeedback('');
      onChange(null);
      return;
    }

    // Converter ao sair do campo
    const meses = parseIdadeParaMeses(textoIdade);
    
    if (meses !== null) {
      const formatado = formatarIdadeMeses(meses);
      setTextoIdade(formatado);
      setFeedback(`✓ ${formatado}`);
      onChange(meses);
    } else {
      setFeedback('⚠️ Formato inválido. Ex: 12 meses, 2 anos, 1.5 anos');
      onChange(null);
    }
  };

  const handleDataChange = (e) => {
    const data = e.target.value;
    setDataNascimento(data);
    
    if (!data) {
      setFeedback('');
      onChange(null);
      return;
    }

    // Calcular idade em meses
    const meses = calcularIdadeMeses(data);
    
    if (meses !== null) {
      setFeedback(`✓ ${formatarIdadeMeses(meses)}`);
      onChange(meses);
    } else {
      setFeedback('⚠️ Data inválida');
      onChange(null);
    }
  };

  const toggleModo = () => {
    const novoModo = modo === 'texto' ? 'data' : 'texto';
    setModo(novoModo);
    setTextoIdade('');
    setDataNascimento('');
    setFeedback('');
    onChange(null);
  };

  return (
    <div className={className}>
      <div className="flex items-center justify-between mb-2">
        <label className="block text-sm font-medium text-gray-700">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
        
        {mostrarDataNascimento && (
          <button
            type="button"
            onClick={toggleModo}
            className="text-xs text-blue-600 hover:text-blue-800 underline"
          >
            {modo === 'texto' ? '📅 Usar data de nascimento' : '⌨️ Digitar idade'}
          </button>
        )}
      </div>

      {modo === 'texto' ? (
        <div>
          <input
            type="text"
            name={name}
            value={textoIdade}
            onChange={handleTextoChange}
            onBlur={handleTextoBlur}
            placeholder="Ex: 12 meses, 2 anos, 1.5 anos, 2anos6meses"
            className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required={required}
          />
          {feedback && (
            <p className={`text-xs mt-1 ${feedback.startsWith('✓') ? 'text-green-600' : 'text-orange-600'}`}>
              {feedback}
            </p>
          )}
          <p className="text-xs text-gray-500 mt-1">
            Digite a idade e pressione Tab ou clique fora do campo
          </p>
        </div>
      ) : (
        <div>
          <input
            type="date"
            name={name}
            value={dataNascimento}
            onChange={handleDataChange}
            max={new Date().toISOString().split('T')[0]}
            className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required={required}
          />
          {feedback && (
            <p className={`text-xs mt-1 ${feedback.startsWith('✓') ? 'text-green-600' : 'text-orange-600'}`}>
              {feedback}
            </p>
          )}
          <p className="text-xs text-gray-500 mt-1">
            Data de nascimento do pet
          </p>
        </div>
      )}
    </div>
  );
}
