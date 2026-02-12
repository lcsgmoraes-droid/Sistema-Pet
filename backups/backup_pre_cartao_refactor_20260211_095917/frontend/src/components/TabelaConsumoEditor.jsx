import React, { useState, useEffect, useCallback, useRef } from 'react';
import { FiPlus, FiTrash2, FiSave, FiAlertCircle } from 'react-icons/fi';

const TabelaConsumoEditor = ({ value, onChange, pesoEmbalagem }) => {
  const [tipoTabela, setTipoTabela] = useState('filhote_peso_adulto');
  const [linhas, setLinhas] = useState([]);
  const [carregado, setCarregado] = useState(false);
  const ultimoSalvoRef = useRef(null); // Rastreia última versão salva
  const [colunas] = useState([
    { id: '2m', label: '2 meses' },
    { id: '3m', label: '3 meses' },
    { id: '4m', label: '4 meses' },
    { id: '6m', label: '6 meses' },
    { id: '8m', label: '8 meses' },
    { id: '10m', label: '10 meses' },
    { id: '12m', label: '12 meses' },
    { id: '15m', label: '15 meses' },
    { id: '18m', label: '18 meses' },
    { id: 'adulto', label: 'Adulto' }
  ]);

  // Carregar dados existentes APENAS UMA VEZ
  useEffect(() => {
    if (value && !carregado) {
      try {
        const data = typeof value === 'string' ? JSON.parse(value) : value;
        console.log('📥 Carregando tabela:', data);
        if (data.tipo) setTipoTabela(data.tipo);
        if (data.dados) {
          const linhasCarregadas = Object.entries(data.dados).map(([peso, consumos]) => ({
            peso,
            consumos
          }));
          setLinhas(linhasCarregadas);
        }
        setCarregado(true);
      } catch (error) {
        console.error('Erro ao carregar tabela:', error);
        setCarregado(true);
      }
    }
  }, [value, carregado]);

  const getLabelPeso = () => {
    switch (tipoTabela) {
      case 'filhote_peso_adulto':
        return 'Peso Adulto Esperado';
      case 'adulto':
        return 'Peso Atual';
      default:
        return 'Peso';
    }
  };

  const getPlaceholderPeso = () => {
    switch (tipoTabela) {
      case 'filhote_peso_adulto':
        return 'Ex: 5kg, 10kg, 15kg, 20kg';
      case 'adulto':
        return 'Ex: 5kg, 10kg, 15kg, 20kg';
      default:
        return '';
    }
  };

  const adicionarLinha = () => {
    const novaLinha = {
      peso: '',
      consumos: {}
    };
    const novasLinhas = [...linhas, novaLinha];
    setLinhas(novasLinhas);
  };

  const removerLinha = (index) => {
    const novasLinhas = linhas.filter((_, i) => i !== index);
    setLinhas(novasLinhas);
    salvarDados(novasLinhas);
  };

  const atualizarPeso = (index, novoPeso) => {
    const novasLinhas = [...linhas];
    novasLinhas[index].peso = novoPeso;
    setLinhas(novasLinhas);
  };

  const atualizarConsumo = (indexLinha, colunaId, valorGramas) => {
    const novasLinhas = [...linhas];
    if (!novasLinhas[indexLinha].consumos) {
      novasLinhas[indexLinha].consumos = {};
    }
    
    // Armazenar apenas gramas (número)
    const gramas = parseFloat(valorGramas) || 0;
    novasLinhas[indexLinha].consumos[colunaId] = gramas;
    
    setLinhas(novasLinhas);
  };

  const calcularDuracao = (consumoDiario) => {
    if (!pesoEmbalagem || !consumoDiario) return '-';
    const pesoGramas = pesoEmbalagem * 1000; // converter kg para gramas
    const dias = Math.floor(pesoGramas / consumoDiario);
    return `${dias}d`;
  };

  const salvarDados = useCallback((linhasParaSalvar) => {
    if (!carregado) {
      console.log('⏸️ Aguardando carregamento inicial...');
      return; // Não salvar se ainda não carregou
    }
    
    const linhasAtuais = linhasParaSalvar || linhas;
    const dados = {};
    linhasAtuais.forEach(linha => {
      if (linha.peso) {
        dados[linha.peso] = linha.consumos;
      }
    });

    const tabelaCompleta = {
      tipo: tipoTabela,
      dados: dados
    };

    const jsonString = JSON.stringify(tabelaCompleta);
    
    // Comparar com última versão salva para evitar salvamentos duplicados
    if (ultimoSalvoRef.current === jsonString) {
      console.log('⏭️ Ignorando - já está salvo');
      return;
    }
    
    console.log('💾 Salvando tabela:', tabelaCompleta);
    ultimoSalvoRef.current = jsonString;
    onChange(jsonString);
  }, [linhas, tipoTabela, onChange, carregado]);

  const handleSalvar = () => {
    salvarDados();
    alert('✅ Tabela de consumo salva com sucesso!');
  };

  return (
    <div className="border border-gray-300 rounded-lg p-4 bg-white">
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-800 mb-2 flex items-center gap-2">
          📊 Tabela de Consumo da Embalagem
        </h3>
        <p className="text-sm text-gray-600 mb-3">
          Preencha a tabela com as informações da embalagem. A IA usará esses dados para calcular duração e custo-benefício.
        </p>

        {/* Seletor de Tipo */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Tipo de Tabela da Embalagem:
          </label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                value="filhote_peso_adulto"
                checked={tipoTabela === 'filhote_peso_adulto'}
                onChange={(e) => setTipoTabela(e.target.value)}
                className="text-blue-600"
              />
              <span className="text-sm font-medium">🐶 Filhote (Peso Adulto Esperado)</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                value="adulto"
                checked={tipoTabela === 'adulto'}
                onChange={(e) => setTipoTabela(e.target.value)}
                className="text-blue-600"
              />
              <span className="text-sm font-medium">🐕 Adulto (Peso Atual)</span>
            </label>
          </div>
        </div>
      </div>

      {/* Tabela */}
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse border border-gray-300">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-3 py-2 text-left text-sm font-semibold text-gray-700 w-32">
                {getLabelPeso()}
              </th>
              {colunas.map(col => (
                <th key={col.id} className="border border-gray-300 px-2 py-2 text-center text-xs font-semibold text-gray-700 min-w-[90px]">
                  {col.label}
                  <div className="text-[10px] text-gray-500 font-normal">g/dia | dias</div>
                </th>
              ))}
              <th className="border border-gray-300 px-2 py-2 text-center text-sm font-semibold text-gray-700 w-16">
                Ações
              </th>
            </tr>
          </thead>
          <tbody>
            {linhas.length === 0 ? (
              <tr>
                <td colSpan={colunas.length + 2} className="border border-gray-300 px-4 py-8 text-center text-gray-500">
                  <FiAlertCircle className="inline-block mr-2" />
                  Nenhuma linha adicionada. Clique em "Adicionar Linha" para começar.
                </td>
              </tr>
            ) : (
              linhas.map((linha, indexLinha) => (
                <tr key={indexLinha} className="hover:bg-gray-50">
                  <td className="border border-gray-300 px-2 py-2">
                    <input
                      type="text"
                      value={linha.peso}
                      onChange={(e) => atualizarPeso(indexLinha, e.target.value)}
                      onBlur={() => salvarDados()}
                      placeholder={getPlaceholderPeso()}
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </td>
                  {colunas.map(col => {
                    const consumo = linha.consumos?.[col.id] || '';
                    const duracao = calcularDuracao(consumo);
                    return (
                      <td key={col.id} className="border border-gray-300 px-1 py-1">
                        <input
                          type="number"
                          value={consumo}
                          onChange={(e) => atualizarConsumo(indexLinha, col.id, e.target.value)}
                          onBlur={() => salvarDados()}
                          placeholder="0"
                          className="w-full px-2 py-1 text-sm text-center border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        <div className="text-[10px] text-center text-gray-500 mt-0.5">
                          {duracao}
                        </div>
                      </td>
                    );
                  })}
                  <td className="border border-gray-300 px-2 py-2 text-center">
                    <button
                      type="button"
                      onClick={() => removerLinha(indexLinha)}
                      className="text-red-600 hover:text-red-800 p-1"
                      title="Remover linha"
                    >
                      <FiTrash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Botões */}
      <div className="flex gap-3 mt-4">
        <button
          type="button"
          onClick={adicionarLinha}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
        >
          <FiPlus size={16} />
          Adicionar Linha
        </button>
        <button
          type="button"
          onClick={handleSalvar}
          className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm"
        >
          <FiSave size={16} />
          Salvar Tabela
        </button>
      </div>

      {/* Info */}
      {pesoEmbalagem && (
        <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-sm text-yellow-800">
            💡 <strong>Peso da embalagem:</strong> {pesoEmbalagem}kg ({pesoEmbalagem * 1000}g)
            <br />
            A duração (dias) é calculada automaticamente: <code>peso_embalagem ÷ consumo_diário</code>
          </p>
        </div>
      )}
    </div>
  );
};

export default TabelaConsumoEditor;
