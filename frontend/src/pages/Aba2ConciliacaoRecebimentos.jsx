import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

/**
 * ABA 2: CONCILIAÇÃO DE RECEBIMENTOS (3 arquivos)
 * 
 * Objetivo:
 *   Validar que DINHEIRO ENTROU na conta bancária.
 *   NÃO conhece vendas! Apenas valida arquivos financeiros.
 * 
 * Fluxo:
 *   1. Upload 3 arquivos:
 *      - recebimentos_detalhados.csv (lista 1 a 1)
 *      - recibo_lote.csv (agrupado)
 *      - extrato.ofx (banco)
 *   2. Validação em cascata:
 *      Soma(detalhados) == Soma(lote) == Soma(OFX)
 *   3. Se bater tudo → validado = true
 * 
 * Resultado:
 *   conciliacao_recebimentos.validado = true
 *   Desbloqueia Aba 3
 */
export default function Aba2ConciliacaoRecebimentos({ onConcluida, status }) {
  const [avisoOculto, setAvisoOculto] = useState(false);
  const [arquivos, setArquivos] = useState({
    recebimentos: null,
    recibo: null,
    ofx: null
  });
  const [processando, setProcessando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState(null);
  
  // Estados para operadoras
  const [operadoras, setOperadoras] = useState([]);
  const [operadoraSelecionada, setOperadoraSelecionada] = useState(null);
  const [carregandoOperadoras, setCarregandoOperadoras] = useState(true);
  
  // Estados para modais
  const [mostrarModalConfirmacao, setMostrarModalConfirmacao] = useState(false);
  const [mostrarModalDivergencia, setMostrarModalDivergencia] = useState(false);
  const [operadoraDetectada, setOperadoraDetectada] = useState(null);
  const [confiancaDeteccao, setConfiancaDeteccao] = useState(0);
  const [ignorarDivergenciaOperadora, setIgnorarDivergenciaOperadora] = useState(false);

  // Handler para avançar
  const handleAvancar = () => {
    console.log('🎯 Tentando avançar para Aba 3...');
    console.log('onConcluida existe?', typeof onConcluida);
    
    if (typeof onConcluida === 'function') {
      console.log('✅ Chamando onConcluida()');
      onConcluida();
      console.log('✅ onConcluida() foi chamado com sucesso');
    } else {
      console.error('❌ onConcluida não é uma função!', onConcluida);
      alert('Erro: Função de callback não encontrada. Recarregue a página.');
    }
  };

  // Reset completo
  const resetarTudo = () => {
    setArquivos({ recebimentos: null, recibo: null, ofx: null });
    setResultado(null);
    setErro(null);
    setProcessando(false);
    setIgnorarDivergenciaOperadora(false); // Resetar flag de divergência
    setOperadoraDetectada(null);
    setConfiancaDeteccao(0);
    setMostrarModalConfirmacao(false);
    setMostrarModalDivergencia(false);
    console.log('🔄 Estado resetado');
  };

  // Carregar operadoras ao montar
  useEffect(() => {
    const carregarOperadoras = async () => {
      try {
        const response = await api.get('/operadoras-cartao?apenas_ativas=true');
        setOperadoras(response.data);
        
        // Pré-selecionar operadora padrão (Stone geralmente)
        const padrao = response.data.find(op => op.padrao);
        if (padrao) {
          setOperadoraSelecionada(padrao);
        }
      } catch (error) {
        console.error('Erro ao carregar operadoras:', error);
        setErro('Erro ao carregar operadoras');
      } finally {
        setCarregandoOperadoras(false);
      }
    };
    carregarOperadoras();
  }, []);

  useEffect(() => {
    const raw = localStorage.getItem('conciliacao_aba2_aviso_ate');
    if (!raw) return;
    const expiraEm = Number(raw);
    if (Number.isFinite(expiraEm) && Date.now() < expiraEm) {
      setAvisoOculto(true);
    }
  }, []);

  const ocultarAviso = (dias) => {
    const expiraEm = Date.now() + dias * 24 * 60 * 60 * 1000;
    localStorage.setItem('conciliacao_aba2_aviso_ate', String(expiraEm));
    setAvisoOculto(true);
  };

  // Handler upload arquivos
  const handleFileChange = (tipo, e) => {
    const file = e.target.files?.[0];
    
    if (!file) {
      console.warn(`Nenhum arquivo selecionado para ${tipo}`);
      return;
    }
    
    console.log(`📎 Arquivo selecionado para ${tipo}:`, {
      name: file.name,
      size: file.size,
      type: file.type,
      lastModified: new Date(file.lastModified).toISOString()
    });
    
    setArquivos(prev => ({ ...prev, [tipo]: file }));
    setErro(null);
    setResultado(null); // Limpar resultado anterior
  };

  // Handler para abrir modal de confirmação
  const handleClickValidar = () => {
    if (!operadoraSelecionada) {
      setErro('Por favor, selecione uma operadora antes de validar.');
      return;
    }
    
    if (!arquivos.recebimentos || !arquivos.recibo || !arquivos.ofx) {
      setErro('Por favor, faça upload dos 3 arquivos antes de validar.');
      return;
    }
    
    setMostrarModalConfirmacao(true);
  };

  // Processar validação (após confirmação)
  const handleValidar = async () => {
    setMostrarModalConfirmacao(false);
    console.log('🚀 Iniciando validação...', {
      arquivos_estado: {
        recebimentos: !!arquivos.recebimentos,
        recibo: !!arquivos.recibo,
        ofx: !!arquivos.ofx
      }
    });

    if (!arquivos.recebimentos || !arquivos.recibo || !arquivos.ofx) {
      setErro('Você precisa enviar os 3 arquivos para continuar');
      return;
    }

    // Validar que os arquivos são objetos File válidos
    console.log('🔍 Validando tipos de arquivo...', {
      recebimentos_isFile: arquivos.recebimentos instanceof File,
      recibo_isFile: arquivos.recibo instanceof File,
      ofx_isFile: arquivos.ofx instanceof File
    });

    if (!(arquivos.recebimentos instanceof File)) {
      console.error('❌ Arquivo de recebimentos não é um File válido:', arquivos.recebimentos);
      setErro('Arquivo de recebimentos inválido. Por favor, selecione novamente.');
      setArquivos(prev => ({ ...prev, recebimentos: null }));
      return;
    }
    
    if (!(arquivos.recibo instanceof File)) {
      console.error('❌ Arquivo de recibo não é um File válido:', arquivos.recibo);
      setErro('Arquivo de recibo inválido. Por favor, selecione novamente.');
      setArquivos(prev => ({ ...prev, recibo: null }));
      return;
    }
    
    if (!(arquivos.ofx instanceof File)) {
      console.error('❌ Arquivo OFX não é um File válido:', arquivos.ofx);
      setErro('Arquivo OFX inválido. Por favor, selecione novamente.');
      setArquivos(prev => ({ ...prev, ofx: null }));
      return;
    }

    setProcessando(true);
    setErro(null);

    try {
      // 1. Parsear arquivos
      let recebimentos_text, recibo_text, ofx_text;
      
      console.log('📂 Lendo arquivos:', {
        recebimentos: arquivos.recebimentos.name,
        recibo: arquivos.recibo.name,
        ofx: arquivos.ofx.name
      });
      
      try {
        recebimentos_text = await arquivos.recebimentos.text();
        if (!recebimentos_text || recebimentos_text.trim().length === 0) {
          throw new Error('Arquivo de recebimentos está vazio');
        }
      } catch (fileError) {
        console.error('Erro ao ler recebimentos:', fileError);
        throw new Error(`Erro ao ler arquivo de recebimentos: ${fileError.message}`);
      }
      
      try {
        recibo_text = await arquivos.recibo.text();
        if (!recibo_text || recibo_text.trim().length === 0) {
          throw new Error('Arquivo de recibo está vazio');
        }
      } catch (fileError) {
        console.error('Erro ao ler recibo:', fileError);
        throw new Error(`Erro ao ler arquivo de recibo: ${fileError.message}`);
      }
      
      try {
        ofx_text = await arquivos.ofx.text();
        if (!ofx_text || ofx_text.trim().length === 0) {
          throw new Error('Arquivo OFX está vazio');
        }
      } catch (fileError) {
        console.error('Erro ao ler OFX:', fileError);
        throw new Error(`Erro ao ler arquivo OFX: ${fileError.message}`);
      }

      console.log('📄 Arquivos carregados:', {
        recebimentos_length: recebimentos_text.length,
        recibo_length: recibo_text.length,
        ofx_length: ofx_text.length
      });

      // Mostrar primeiras 3 linhas para debug
      const recebimentos_lines = recebimentos_text.split('\n');
      console.log('🔍 Primeiras 3 linhas do arquivo de recebimentos:');
      console.log('Linha 0 (header):', recebimentos_lines[0]);
      console.log('Linha 1:', recebimentos_lines[1]);
      console.log('Linha 2:', recebimentos_lines[2]);

      const recibo_lines = recibo_text.split('\n');
      console.log('🔍 Primeiras 3 linhas do arquivo de recibo:');
      console.log('Linha 0 (header):', recibo_lines[0]);
      console.log('Linha 1:', recibo_lines[1]);
      console.log('Linha 2:', recibo_lines[2]);

      // Detectar separador (vírgula ou ponto-e-vírgula)
      const separator = recebimentos_lines[0]?.includes(';') ? ';' : ',';
      console.log('📋 Separador detectado:', separator);

      let recebimentos_detalhados, recibo_lote, ofx_creditos;

      try {
        // Parsear recebimentos detalhados
        recebimentos_detalhados = recebimentos_text
          .split('\n')
          .slice(1)
          .filter(line => line.trim())
          .map((line, idx) => {
            try {
              const campos = line.split(separator);
              
              // Log detalhado da primeira linha para debug
              if (idx === 0) {
                console.log('🔍 DEBUG - Primeira linha parseada:');
                console.log('Total de campos:', campos.length);
                console.log('Campos relevantes:');
                console.log('  Campo 8 (STONE ID/NSU):', campos[8]);
                console.log('  Campo 4 (DATA DE VENCIMENTO):', campos[4]);
                console.log('  Campo 12 (VALOR LÍQUIDO):', campos[12]);
                console.log('  Campo 10 (Nº DA PARCELA):', campos[10]);
                console.log('  Campo 9 (QTD DE PARCELAS):', campos[9]);
                console.log('  Campo 16 (ÚLTIMO STATUS):', campos[16]);
              }
              
              // Formato da Stone:
              // 0:DOCUMENTO, 1:STONECODE, 2:CATEGORIA, 3:DATA DA VENDA, 
              // 4:DATA DE VENCIMENTO, 5:DATA DE VENCIMENTO ORIGINAL, 6:BANDEIRA, 7:PRODUTO,
              // 8:STONE ID, 9:QTD DE PARCELAS, 10:Nº DA PARCELA, 11:VALOR BRUTO, 
              // 12:VALOR LÍQUIDO, 13:DESCONTO DE MDR, 14:DESCONTO DE ANTECIPAÇÃO,
              // 15:DESCONTO UNIFICADO, 16:ÚLTIMO STATUS, 17:DATA DO ÚLTIMO STATUS
              
              const nsu = campos[8]?.trim();  // STONE ID
              const data = campos[4]?.trim();  // DATA DE VENCIMENTO
              const valorOriginal = campos[12]?.trim();  // VALOR LÍQUIDO
              const parcela = campos[10]?.trim();  // Nº DA PARCELA
              const totalParcelas = campos[9]?.trim();  // QTD DE PARCELAS
              const status = campos[16]?.trim();  // ÚLTIMO STATUS
              
              // Converter valor: trocar vírgula por ponto (formato brasileiro)
              const valorLimpo = valorOriginal?.replace(',', '.');
              const valorFinal = parseFloat(valorLimpo || 0);
              
              // Log para primeira linha
              if (idx === 0) {
                console.log('💰 Conversão de valor:');
                console.log('  Original:', valorOriginal);
                console.log('  Limpo:', valorLimpo);
                console.log('  Final:', valorFinal);
                console.log('  Is NaN?', isNaN(valorFinal));
              }
              
              return {
                nsu: nsu,
                data_recebimento: data,
                valor: valorFinal,
                parcela_numero: parseInt(parcela || 1),
                total_parcelas: parseInt(totalParcelas || 1),
                tipo_recebimento: status || 'Pago',
                lote_id: null  // Stone não tem lote_id neste formato
              };
            } catch (err) {
              console.error(`Erro ao parsear linha ${idx + 1} de recebimentos:`, line, err);
              throw new Error(`Erro na linha ${idx + 1} do arquivo de recebimentos detalhados`);
            }
          });
      } catch (err) {
        setErro(`❌ Erro ao processar arquivo de recebimentos: ${err.message}`);
        return;
      }

      try {
        // Parsear recibo lote (Comprovante de Pagamentos Stone - 19 colunas)
        // Formato: Valor;Bandeira;Modalidade;...;Identificador Rastreável do Pagamento;...;Status do Pagamento
        const recibo_separator = recibo_lines[0]?.includes(';') ? ';' : ',';
        
        console.log('📄 Primeira linha do recibo:', recibo_lines[0]);
        console.log('📄 Segunda linha do recibo:', recibo_lines[1]);
        
        recibo_lote = recibo_text
          .split('\n')
          .slice(1)
          .filter(line => line.trim())
          .map((line, idx) => {
            try {
              const campos = line.split(recibo_separator);
              
              // Log primeira linha para debug
              if (idx === 0) {
                console.log('🔍 DEBUG - Recibo primeira linha parseada:');
                console.log('Total de campos:', campos.length);
                console.log('  Campo 0 (Valor):', campos[0]);
                console.log('  Campo 13 (ID Rastreável):', campos[13]);
                console.log('  Campo 18 (Status):', campos[18]);
              }
              
              // Coluna 0: Valor
              // Coluna 13: Identificador Rastreável do Pagamento (ID único)
              // Coluna 18: Status do Pagamento
              const valorOriginal = campos[0]?.trim();
              const lote_id = campos[13]?.trim();
              const status = campos[18]?.trim();
              
              // Converter valor: trocar vírgula por ponto (formato brasileiro)
              const valorLimpo = valorOriginal?.replace(',', '.');
              const valorFinal = parseFloat(valorLimpo || 0);
              
              if (idx === 0) {
                console.log('💰 Conversão recibo:');
                console.log('  Original:', valorOriginal);
                console.log('  Limpo:', valorLimpo);
                console.log('  Final:', valorFinal);
              }
              
              return {
                lote_id: lote_id,
                valor: valorFinal,
                status: status
              };
            } catch (err) {
              console.error(`Erro ao parsear linha ${idx + 1} de recibo:`, line, err);
              throw new Error(`Erro na linha ${idx + 1} do arquivo de recibo de lote`);
            }
          });
      } catch (err) {
        setErro(`❌ Erro ao processar arquivo de recibo: ${err.message}`);
        return;
      }

      try {
        // Parsear OFX (formato STMTTRN)
        console.log('📄 Primeiras linhas do OFX:', ofx_text.split('\n').slice(0, 30).join('\n'));
        
        const transactions = [];
        const lines = ofx_text.split('\n');
        let currentTransaction = null;
        
        for (let i = 0; i < lines.length; i++) {
          const line = lines[i].trim();
          
          if (line === '<STMTTRN>') {
            currentTransaction = {};
          } else if (line === '</STMTTRN>' && currentTransaction) {
            // Só adicionar créditos (CREDIT ou valores positivos)
            if (currentTransaction.type === 'CREDIT' || (currentTransaction.valor && currentTransaction.valor > 0)) {
              transactions.push(currentTransaction);
            }
            currentTransaction = null;
          } else if (currentTransaction) {
            // Extrair campos
            if (line.startsWith('<TRNTYPE>')) {
              currentTransaction.type = line.replace('<TRNTYPE>', '').replace('</TRNTYPE>', '');
            } else if (line.startsWith('<DTPOSTED>')) {
              currentTransaction.data = line.replace('<DTPOSTED>', '').replace('</DTPOSTED>', '');
            } else if (line.startsWith('<TRNAMT>')) {
              const valor = line.replace('<TRNAMT>', '').replace('</TRNAMT>', '');
              currentTransaction.valor = parseFloat(valor);
            } else if (line.startsWith('<FITID>')) {
              currentTransaction.id = line.replace('<FITID>', '').replace('</FITID>', '');
            } else if (line.startsWith('<MEMO>')) {
              currentTransaction.memo = line.replace('<MEMO>', '').replace('</MEMO>', '');
            }
          }
        }
        
        ofx_creditos = transactions;
        console.log('💳 OFX parseado:', ofx_creditos.length, 'transações encontradas');
        if (ofx_creditos.length > 0) {
          console.log('Primeira transação:', ofx_creditos[0]);
        }
      } catch (err) {
        console.error('Erro ao parsear OFX:', err);
        setErro(`❌ Erro ao processar arquivo OFX: ${err.message}`);
        return;
      }

      // Validar que não estão vazios
      if (recebimentos_detalhados.length === 0) {
        setErro('❌ Arquivo de recebimentos detalhados está vazio ou mal formatado. Verifique o formato CSV.');
        return;
      }
      
      if (recibo_lote.length === 0) {
        setErro('❌ Arquivo de recibo de lote está vazio ou mal formatado. Verifique o formato CSV.');
        return;
      }
      
      if (ofx_creditos.length === 0) {
        setErro('❌ Arquivo OFX está vazio ou mal formatado. Verifique o formato.');
        return;
      }

      // Validar valores parseados
      const recebimentosInvalidos = recebimentos_detalhados.filter(r => isNaN(r.valor) || r.valor === null);
      if (recebimentosInvalidos.length > 0) {
        console.error('❌ Recebimentos com valores inválidos:', recebimentosInvalidos);
        console.error('📋 Primeiras 5 linhas RAW do arquivo:');
        recebimentos_lines.slice(0, 6).forEach((line, idx) => {
          console.error(`Linha ${idx}:`, line);
        });
        setErro(`❌ ${recebimentosInvalidos.length} recebimentos têm valores inválidos. Verifique o formato dos valores no CSV (use vírgula ou ponto decimal). Veja o console para mais detalhes.`);
        return;
      }

      const lotesInvalidos = recibo_lote.filter(l => isNaN(l.valor) || l.valor === null);
      if (lotesInvalidos.length > 0) {
        console.error('❌ Lotes com valores inválidos:', lotesInvalidos);
        setErro(`❌ ${lotesInvalidos.length} lotes têm valores inválidos. Verifique o formato dos valores no CSV.`);
        return;
      }

      console.log('✅ Todos os valores validados! Enviando para API...');

      // 2. Log para debug
      console.log('📤 Enviando dados para API:', {
        recebimentos_count: recebimentos_detalhados.length,
        recibo_count: recibo_lote.length,
        ofx_count: ofx_creditos.length,
        sample_recebimento: recebimentos_detalhados[0],
        sample_recebimento_2: recebimentos_detalhados[1],
        sample_recibo: recibo_lote[0],
        sample_ofx: ofx_creditos[0]
      });

      console.log('💰 Valores parseados (primeiros 3):');
      console.log('Recebimento 1:', recebimentos_detalhados[0]?.valor);
      console.log('Recebimento 2:', recebimentos_detalhados[1]?.valor);
      console.log('Recibo 1:', recibo_lote[0]?.valor);
      console.log('OFX 1:', ofx_creditos[0]?.valor);

      // 2.5 - Extrair data de referência dos recebimentos
      const extrairDataReferencia = (recebimentos) => {
        const datas = {};
        
        recebimentos.forEach(rec => {
          // Procurar campo de data (pode ter vários nomes)
          const camposData = ['data', 'data_recebimento', 'data_pagamento', 'Data de Pagamento', 'Data do Pagamento'];
          
          for (const campo of camposData) {
            if (rec[campo]) {
              // Normalizar data para YYYY-MM-DD
              let dataStr = rec[campo];
              
              // Converter DD/MM/YYYY para YYYY-MM-DD
              if (dataStr.match(/^\d{2}\/\d{2}\/\d{4}$/)) {
                const [dia, mes, ano] = dataStr.split('/');
                dataStr = `${ano}-${mes}-${dia}`;
              }
              
              // Contar ocorrências
              datas[dataStr] = (datas[dataStr] || 0) + 1;
              break;
            }
          }
        });
        
        // Retornar data mais frequente
        const datasOrdenadas = Object.entries(datas).sort((a, b) => b[1] - a[1]);
        return datasOrdenadas[0]?.[0] || null;
      };

      const dataReferencia = extrairDataReferencia(recebimentos_detalhados);
      console.log('📅 Data de referência detectada:', dataReferencia);

      // Metadados dos arquivos para histórico
      const arquivosInfo = [
        { nome: arquivos.recebimentos.name, tamanho: arquivos.recebimentos.size, tipo: 'recebimentos_detalhados' },
        { nome: arquivos.recibo.name, tamanho: arquivos.recibo.size, tipo: 'recibo_lote' },
        { nome: arquivos.ofx.name, tamanho: arquivos.ofx.size, tipo: 'extrato_ofx' }
      ];

      // 3. Chamar API
      const response = await api.post('/conciliacao/aba2/validar-recebimentos', {
        recebimentos_detalhados,
        recibo_lote,
        ofx_creditos,
        data_referencia: dataReferencia,
        arquivos_info: arquivosInfo,
        operadora: operadoraSelecionada?.nome
      });

      // Verificar divergência de operadora (somente se não ignorar)
      if (!ignorarDivergenciaOperadora) {
        const operadoraSelecionadaNome = operadoraSelecionada.nome;
        const operadoraDetectadaNome = response.data.operadora_detectada;
        const confianca = response.data.confianca_deteccao || 0;
        
        console.log('🔍 Comparação de operadoras:', {
          selecionada: operadoraSelecionadaNome,
          detectada: operadoraDetectadaNome,
          confianca: confianca,
          ignorar: ignorarDivergenciaOperadora
        });
        
        // Se operadora detectada é diferente e confiança >= 70%, mostrar aviso
        if (operadoraDetectadaNome && 
            operadoraSelecionadaNome !== operadoraDetectadaNome && 
            confianca >= 0.7) {
          setOperadoraDetectada(operadoraDetectadaNome);
          setConfiancaDeteccao(confianca);
          setResultado(response.data); // Salvar resultado temporariamente
          setMostrarModalDivergencia(true);
          setProcessando(false);
          return; // Aguardar decisão do usuário
        }
      }
      
      setResultado(response.data);

      console.log('📊 Resultado da validação:', {
        success: response.data.success,
        tem_divergencias: response.data.tem_divergencias,
        validado: response.data.validado,
        historico_id: response.data.historico_id,
        operadora_detectada: response.data.operadora_detectada,
        ja_conciliado: response.data.ja_conciliado
      });

      // Mostrar aviso se já foi conciliado antes
      if (response.data.ja_conciliado && response.data.aviso_reprocessamento) {
        console.warn('⚠️ Reprocessamento detectado:', response.data.aviso_reprocessamento);
      }

      // Sempre avança se success=true (divergências são informativas)
      if (response.data.success) {
        // Se não tem divergências, avança automaticamente
        if (!response.data.tem_divergencias) {
          console.log('✅ Validação perfeita, avançando automaticamente em 1.5s...');
          setTimeout(() => {
            handleAvancar();
          }, 1500);
        } else {
          console.log('⚠️ Tem divergências, aguardando decisão do usuário...');
        }
        // Se tem divergências, usuário precisa confirmar manualmente
      }

    } catch (error) {
      console.error('Erro ao validar:', error);
      console.error('Detalhes do erro:', error.response?.data);
      
      // Mostrar erro detalhado para debug
      const errorMsg = error.response?.data?.detail 
        || error.response?.data?.message 
        || JSON.stringify(error.response?.data)
        || 'Erro ao validar recebimentos';
      
      setErro(errorMsg);
    } finally {
      setProcessando(false);
    }
  };

  const todosArquivosEnviados = arquivos.recebimentos && arquivos.recibo && arquivos.ofx;

  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">
            Aba 2: Conciliação de Recebimentos
          </h2>
          <p className="text-gray-600">
            Valide que dinheiro entrou na conta (3 arquivos: detalhados, recibo, OFX)
          </p>
        </div>
        <button
          onClick={() => navigate('/financeiro/historico-conciliacoes')}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-500 to-indigo-600 text-white rounded-lg hover:from-purple-600 hover:to-indigo-700 transition-all shadow-md hover:shadow-lg"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="font-semibold">📜 Ver Histórico</span>
        </button>
      </div>

      {/* Aviso de Sequencia */}
      {!avisoOculto ? (
        <div className="bg-blue-50 border-l-4 border-blue-400 p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-blue-700">
                  <strong>Ordem recomendada:</strong> Aba 1 prepara os NSUs; esta Aba 2 valida os recebimentos; a Aba 3 baixa as parcelas com seguranca.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => ocultarAviso(30)}
                className="text-xs text-blue-700 hover:text-blue-900"
              >
                Ocultar 30 dias
              </button>
              <button
                onClick={() => ocultarAviso(365)}
                className="text-xs text-blue-700 hover:text-blue-900"
              >
                Ocultar 1 ano
              </button>
            </div>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setAvisoOculto(false)}
          className="text-xs text-blue-700 hover:text-blue-900"
        >
          Mostrar aviso de sequencia
        </button>
      )}

      {/* Alerta Importante */}
      <div className="bg-purple-50 border-l-4 border-purple-400 p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-purple-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-purple-700 mb-2">
              <strong>Esta aba NÃO conhece vendas.</strong> Apenas valida que o dinheiro entrou na conta.
              Validação em cascata: Recebimentos → Recibo → OFX (todos precisam bater).
            </p>
            <details className="text-xs text-purple-600 mt-2">
              <summary className="cursor-pointer font-semibold hover:text-purple-800">
                📋 Formato esperado dos arquivos
              </summary>
              <div className="mt-2 space-y-2 pl-4">
                <p><strong>Recebimentos Detalhados CSV da Stone:</strong></p>
                <p className="text-xs font-mono">DOCUMENTO;STONECODE;CATEGORIA;DATA DA VENDA;DATA DE VENCIMENTO;DATA DE VENCIMENTO ORIGINAL;BANDEIRA;PRODUTO;STONE ID;QTD DE PARCELAS;Nº DA PARCELA;VALOR BRUTO;VALOR LÍQUIDO;DESCONTO DE MDR;DESCONTO DE ANTECIPAÇÃO;DESCONTO UNIFICADO;ÚLTIMO STATUS;DATA DO ÚLTIMO STATUS</p>
                <p className="text-xs text-purple-500">Separador: ponto-e-vírgula (;) | Valores com vírgula decimal (21,012265)</p>
                
                <p className="mt-2"><strong>Comprovante de Pagamentos CSV da Stone:</strong></p>
                <p className="text-xs font-mono">Valor;Bandeira;Modalidade;...;Identificador Rastreável do Pagamento;...;Status do Pagamento (19 colunas)</p>
                <p className="text-xs text-purple-500">Separador: ponto-e-vírgula (;) | Valores com vírgula decimal (202,11)</p>
                
                <p className="mt-2"><strong>OFX:</strong></p>
                <p className="text-xs">Arquivo bancário padrão OFX com tags &lt;STMTTRN&gt;, &lt;TRNAMT&gt;, &lt;TRNTYPE&gt;</p>
              </div>
            </details>
          </div>
        </div>
      </div>

      {/* Seleção de Operadora */}
      <div className="bg-gradient-to-r from-blue-50 to-blue-100 border-2 border-blue-200 rounded-lg p-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="flex-shrink-0">
            <svg className="h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
            </svg>
          </div>
          <div className="flex-1">
            <label className="block text-sm font-semibold text-blue-900 mb-2">
              🏛 Operadora de Cartão:
            </label>
            <select
              value={operadoraSelecionada?.id || ''}
              onChange={(e) => {
                const op = operadoras.find(o => o.id === parseInt(e.target.value));
                setOperadoraSelecionada(op);
                // Limpar resultado anterior ao trocar operadora
                setResultado(null);
                setErro(null);
                setIgnorarDivergenciaOperadora(false); // Resetar flag ao trocar operadora
                setOperadoraDetectada(null);
              }}
              disabled={carregandoOperadoras || processando}
              className="w-full border-2 border-blue-300 rounded-lg px-4 py-3 text-base font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              <option value="">Selecione a operadora...</option>
              {operadoras.map(op => (
                <option key={op.id} value={op.id}>
                  {op.nome} {op.padrao ? '🎯 (Padrão)' : ''}
                </option>
              ))}
            </select>
            {operadoraSelecionada && (
              <p className="mt-2 text-xs text-blue-700">
                ✅ Operadora selecionada: <strong>{operadoraSelecionada.nome}</strong>
              </p>
            )}
            {!operadoraSelecionada && (
              <p className="mt-2 text-xs text-orange-600 font-medium">
                ⚠️ Selecione a operadora antes de fazer upload dos arquivos
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Uploads dos 3 Arquivos */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Arquivo 1: Recebimentos Detalhados */}
        <div className="bg-white border-2 border-dashed border-gray-300 rounded-lg p-4">
          <div className="text-center">
            <div className="mx-auto h-12 w-12 text-blue-400 flex items-center justify-center">
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" className="h-full w-full">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div className="mt-3">
              <label htmlFor="file-recebimentos" className="cursor-pointer">
                <span className="block text-sm font-medium text-gray-900 mb-1">
                  1️⃣ Recebimentos Detalhados
                </span>
                <span className="block text-xs text-gray-500 mb-3">
                  Arquivo CSV da Stone (18 colunas)
                </span>
                <input
                  id="file-recebimentos"
                  type="file"
                  accept=".csv"
                  onChange={(e) => handleFileChange('recebimentos', e)}
                  className="sr-only"
                />
                <span className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50">
                  Selecionar CSV
                </span>
              </label>
              {arquivos.recebimentos && (
                <p className="mt-2 text-xs text-green-600 font-medium truncate">
                  ✓ {arquivos.recebimentos.name}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Arquivo 2: Recibo Lote */}
        <div className="bg-white border-2 border-dashed border-gray-300 rounded-lg p-4">
          <div className="text-center">
            <div className="mx-auto h-12 w-12 text-green-400 flex items-center justify-center">
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" className="h-full w-full">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div className="mt-3">
              <label htmlFor="file-recibo" className="cursor-pointer">
                <span className="block text-sm font-medium text-gray-900 mb-1">
                  2️⃣ Recibo de Lote
                </span>
                <span className="block text-xs text-gray-500 mb-3">
                  CSV "Comprovante de Pagamentos" (19 colunas)
                </span>
                <input
                  id="file-recibo"
                  type="file"
                  accept=".csv"
                  onChange={(e) => handleFileChange('recibo', e)}
                  className="sr-only"
                />
                <span className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50">
                  Selecionar CSV
                </span>
              </label>
              {arquivos.recibo && (
                <p className="mt-2 text-xs text-green-600 font-medium truncate">
                  ✓ {arquivos.recibo.name}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Arquivo 3: OFX */}
        <div className="bg-white border-2 border-dashed border-gray-300 rounded-lg p-4">
          <div className="text-center">
            <div className="mx-auto h-12 w-12 text-purple-400 flex items-center justify-center">
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" className="h-full w-full">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
              </svg>
            </div>
            <div className="mt-3">
              <label htmlFor="file-ofx" className="cursor-pointer">
                <span className="block text-sm font-medium text-gray-900 mb-1">
                  3️⃣ Extrato OFX
                </span>
                <span className="block text-xs text-gray-500 mb-3">
                  Extrato bancário
                </span>
                <input
                  id="file-ofx"
                  type="file"
                  accept=".ofx,.xml"
                  onChange={(e) => handleFileChange('ofx', e)}
                  className="sr-only"
                />
                <span className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50">
                  Selecionar OFX
                </span>
              </label>
              {arquivos.ofx && (
                <p className="mt-2 text-xs text-green-600 font-medium truncate">
                  ✓ {arquivos.ofx.name}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Botão Validar */}
      {todosArquivosEnviados && !resultado && (
        <button
          onClick={handleClickValidar}
          disabled={processando || !operadoraSelecionada}
          className={`
            w-full flex justify-center items-center gap-2 py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white
            ${processando ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}
          `}
        >
          {processando ? (
            <>
              <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span>Validando recebimentos...</span>
            </>
          ) : (
            <>
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              <span>Validar Cascata (3 arquivos)</span>
            </>
          )}
        </button>
      )}

      {/* Erro */}
      {erro && (
        <div className="bg-red-50 border-l-4 border-red-400 p-4">
          <div className="flex items-start justify-between">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-700">{erro}</p>
              </div>
            </div>
            <button
              onClick={resetarTudo}
              className="ml-4 px-3 py-1 bg-red-100 hover:bg-red-200 text-red-700 text-xs font-medium rounded"
            >
              Limpar e Tentar Novamente
            </button>
          </div>
        </div>
      )}

      {/* Resultado */}
      {resultado && resultado.success && (
        <div className="space-y-4">
          {/* Aviso de Reprocessamento (se aplicável) */}
          {resultado.ja_conciliado && resultado.aviso_reprocessamento && (
            <div className="bg-orange-50 border-l-4 border-orange-400 p-4 rounded-lg">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-6 w-6 text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <div className="ml-3 flex-1">
                  <h3 className="text-sm font-medium text-orange-800">
                    ⚠️ REPROCESSAMENTO DETECTADO
                  </h3>
                  <div className="mt-2 text-sm text-orange-700">
                    <p>{resultado.aviso_reprocessamento.mensagem}</p>
                    {resultado.aviso_reprocessamento.usuario_anterior && (
                      <p className="mt-1">
                        <span className="font-medium">Processado anteriormente por:</span>{' '}
                        {resultado.aviso_reprocessamento.usuario_anterior}
                      </p>
                    )}
                  </div>
                  <div className="mt-3">
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                      Data: {resultado.data_referencia} | Operadora: {resultado.operadora_detectada}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Informações da Conciliação */}
          {(resultado.operadora_detectada || resultado.data_referencia) && (
            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-lg">
              <div className="flex items-start">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-blue-800">
                    Informações da Conciliação
                  </h3>
                  <div className="mt-2 text-sm text-blue-700 space-y-1">
                    {resultado.operadora_detectada && (
                      <p>
                        <span className="font-medium">Operadora:</span> {resultado.operadora_detectada}
                        {resultado.confianca_deteccao && (
                          <span className="ml-2 text-xs">
                            (Confiança: {(resultado.confianca_deteccao * 100).toFixed(0)}%)
                          </span>
                        )}
                      </p>
                    )}
                    {resultado.data_referencia && (
                      <p>
                        <span className="font-medium">Data de Referência:</span>{' '}
                        {new Date(resultado.data_referencia + 'T00:00:00').toLocaleDateString('pt-BR')}
                      </p>
                    )}
                    {resultado.historico_id && (
                      <p>
                        <span className="font-medium">ID do Histórico:</span> #{resultado.historico_id}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {/* Resumo dos Valores */}
          <div className="bg-white border-2 border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <svg className="h-6 w-6 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              Resumo da Validação em Cascata
            </h3>
            
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="bg-blue-50 rounded-lg p-4">
                <p className="text-xs text-blue-600 font-medium mb-1">1️⃣ Recebimentos Detalhados</p>
                <p className="text-2xl font-bold text-blue-900">R$ {resultado.valor_total_recebimentos?.toFixed(2)}</p>
                <p className="text-xs text-blue-600 mt-1">{resultado.recebimentos_salvos} transações</p>
              </div>
              
              <div className="bg-green-50 rounded-lg p-4">
                <p className="text-xs text-green-600 font-medium mb-1">2️⃣ Comprovante (Lotes)</p>
                <p className="text-2xl font-bold text-green-900">R$ {resultado.valor_total_lotes?.toFixed(2)}</p>
                <p className="text-xs text-green-600 mt-1">{resultado.lotes_count} lotes</p>
              </div>
              
              <div className="bg-purple-50 rounded-lg p-4">
                <p className="text-xs text-purple-600 font-medium mb-1">3️⃣ Extrato Bancário (OFX)</p>
                <p className="text-2xl font-bold text-purple-900">R$ {resultado.valor_total_ofx?.toFixed(2)}</p>
                <p className="text-xs text-purple-600 mt-1">{resultado.ofx_count} créditos</p>
              </div>
            </div>
          </div>

          {/* Status: Sem Divergências */}
          {!resultado.tem_divergencias && (
            <div className="bg-green-50 border-l-4 border-green-400 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-green-800">
                    ✅ Validação Perfeita! Nenhuma divergência encontrada.
                  </h3>
                  <p className="mt-1 text-sm text-green-700">
                    Todas as 3 somas estão idênticas. As {resultado.recebimentos_salvos} vendas foram confirmadas na conta.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Status: Com Divergências (Informativo) */}
          {resultado.tem_divergencias && resultado.divergencias && resultado.divergencias.length > 0 && (
            <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3 flex-1">
                  <h3 className="text-sm font-medium text-yellow-800">
                    ⚠️ Divergências Detectadas
                  </h3>
                  <p className="mt-1 text-sm text-yellow-700">
                    Foram encontradas diferenças entre os arquivos. Analise abaixo e decida se aceita ou não.
                  </p>
                  
                  {/* Divergências Detalhadas */}
                  <div className="mt-4 space-y-3">
                    {resultado.divergencias.map((div, idx) => {
                      const isArredondamento = div.nivel === 'arredondamento';
                      const bgColor = isArredondamento ? 'bg-blue-50 border-blue-200' : 'bg-orange-50 border-orange-200';
                      const textColor = isArredondamento ? 'text-blue-900' : 'text-orange-900';
                      const badgeColor = isArredondamento ? 'bg-blue-100 text-blue-800' : 'bg-orange-100 text-orange-800';
                      
                      return (
                        <div key={idx} className={`border rounded-lg p-4 ${bgColor}`}>
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <span className={`text-xs font-semibold px-2 py-1 rounded ${badgeColor}`}>
                                {isArredondamento ? '🔵 Arredondamento' : '🟠 Atenção'}
                              </span>
                              <p className={`text-sm font-medium ${textColor}`}>
                                {div.tipo === 'recebimentos_vs_lotes' ? 'Recebimentos × Lotes' : 'Lotes × OFX'}
                              </p>
                            </div>
                            <div className={`text-right ${textColor}`}>
                              <p className="text-lg font-bold">R$ {Math.abs(div.diferenca).toFixed(2)}</p>
                              <p className="text-xs">{div.percentual?.toFixed(3)}%</p>
                            </div>
                          </div>
                          
                          <div className="grid grid-cols-2 gap-3 text-xs">
                            <div>
                              <p className="text-gray-600">
                                {div.tipo === 'recebimentos_vs_lotes' ? 'Recebimentos:' : 'Lotes:'}
                              </p>
                              <p className={`font-semibold ${textColor}`}>
                                R$ {(div.tipo === 'recebimentos_vs_lotes' ? div.soma_recebimentos : div.soma_lotes)?.toFixed(2)}
                              </p>
                            </div>
                            <div>
                              <p className="text-gray-600">
                                {div.tipo === 'recebimentos_vs_lotes' ? 'Lotes:' : 'OFX:'}
                              </p>
                              <p className={`font-semibold ${textColor}`}>
                                R$ {(div.tipo === 'recebimentos_vs_lotes' ? div.soma_lotes : div.soma_ofx)?.toFixed(2)}
                              </p>
                            </div>
                          </div>
                          
                          <p className="text-xs text-gray-600 mt-2 italic">{div.mensagem}</p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Botões de Ação */}
          <div className="flex items-center justify-between pt-4 border-t">
            <div className="text-sm text-gray-600">
              {resultado.tem_divergencias ? (
                <p>⚠️ Analise as divergências e decida se aceita a validação</p>
              ) : (
                <p>✅ Validação perfeita! Pode avançar para a Aba 3.</p>
              )}
            </div>
            <div className="flex gap-3">
              {resultado.tem_divergencias && (
                <button
                  onClick={resetarTudo}
                  className="px-6 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 font-medium"
                >
                  ✕ Cancelar e Recomeçar
                </button>
              )}
              <button
                onClick={() => {
                  console.log('🖱️ Botão Aceitar e Avançar clicado');
                  handleAvancar();
                }}
                className={`px-6 py-2 rounded-md font-medium transition-colors ${
                  resultado.tem_divergencias
                    ? 'bg-yellow-600 hover:bg-yellow-700 text-white'
                    : 'bg-green-600 hover:bg-green-700 text-white'
                }`}
              >
                {resultado.tem_divergencias ? '✓ Aceitar e Avançar →' : 'Avançar para Aba 3 →'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Confirmação - Antes de Validar */}
      {mostrarModalConfirmacao && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            {/* Overlay */}
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={() => setMostrarModalConfirmacao(false)}></div>

            {/* Modal */}
            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="sm:flex sm:items-start">
                  <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-blue-100 sm:mx-0 sm:h-10 sm:w-10">
                    <svg className="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
                    <h3 className="text-lg leading-6 font-medium text-gray-900">
                      Confirmar Operadora
                    </h3>
                    <div className="mt-2">
                      <p className="text-sm text-gray-500">
                        Você está prestes a validar recebimentos para a operadora:
                      </p>
                      <div className="mt-3 p-3 bg-blue-50 rounded border border-blue-200">
                        <p className="text-lg font-bold text-blue-900">
                          🏦 {operadoraSelecionada?.nome}
                        </p>
                      </div>
                      <p className="text-sm text-gray-500 mt-3">
                        ⚠️ <strong>Todos os lançamentos serão vinculados a esta operadora.</strong>
                      </p>
                      <p className="text-xs text-gray-400 mt-2">
                        O sistema detectará automaticamente se os arquivos correspondem a esta operadora e alertará se houver divergência.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button
                  type="button"
                  onClick={handleValidar}
                  className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none sm:ml-3 sm:w-auto sm:text-sm"
                >
                  ✓ Confirmar e Validar
                </button>
                <button
                  type="button"
                  onClick={() => setMostrarModalConfirmacao(false)}
                  className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                >
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Divergência de Operadora */}
      {mostrarModalDivergencia && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            {/* Overlay */}
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"></div>

            {/* Modal */}
            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-2xl sm:w-full">
              <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="sm:flex sm:items-start">
                  <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-orange-100 sm:mx-0 sm:h-10 sm:w-10">
                    <svg className="h-6 w-6 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                  </div>
                  <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left flex-1">
                    <h3 className="text-lg leading-6 font-bold text-orange-900">
                      ⚠️ Divergência de Operadora Detectada
                    </h3>
                    <div className="mt-4">
                      <p className="text-sm text-gray-700 mb-4">
                        <strong>Os arquivos enviados parecem ser de uma operadora diferente da selecionada.</strong>
                      </p>
                      
                      <div className="space-y-3">
                        {/* Operadora Selecionada */}
                        <div className="p-3 bg-red-50 border-2 border-red-300 rounded-lg">
                          <p className="text-xs text-red-600 font-medium mb-1">Operadora Selecionada:</p>
                          <p className="text-lg font-bold text-red-900">
                            {operadoraSelecionada?.nome}
                          </p>
                        </div>
                        
                        {/* Operadora Detectada */}
                        <div className="p-3 bg-green-50 border-2 border-green-300 rounded-lg">
                          <p className="text-xs text-green-600 font-medium mb-1">Operadora Detectada nos Arquivos:</p>
                          <p className="text-lg font-bold text-green-900">
                            {operadoraDetectada}
                          </p>
                          <p className="text-xs text-green-700 mt-1">
                            Confiança da detecção: {(confiancaDeteccao * 100).toFixed(0)}%
                          </p>
                        </div>
                      </div>
                      
                      <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
                        <p className="text-sm text-yellow-800">
                          <strong>O que você deseja fazer?</strong>
                        </p>
                        <ul className="text-xs text-yellow-700 mt-2 space-y-1 list-disc list-inside">
                          <li><strong>Mudar para {operadoraDetectada}:</strong> Recomendado se os arquivos estão corretos</li>
                          <li><strong>Manter {operadoraSelecionada?.nome}:</strong> Use se você tem certeza da operadora</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse gap-3">
                <button
                  type="button"
                  onClick={() => {
                    // Mudar para operadora detectada
                    const operadoraNova = operadoras.find(op => op.nome === operadoraDetectada);
                    if (operadoraNova) {
                      setOperadoraSelecionada(operadoraNova);
                    }
                    setMostrarModalDivergencia(false);
                    // Processar com nova operadora
                    setTimeout(() => {
                      handleValidar();
                    }, 100);
                  }}
                  className="inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-green-600 text-base font-medium text-white hover:bg-green-700 focus:outline-none sm:text-sm"
                >
                  ✓ Mudar para {operadoraDetectada}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    // Manter operadora selecionada e continuar (ignorando divergência)
                    setIgnorarDivergenciaOperadora(true);
                    setMostrarModalDivergencia(false);
                    
                    // Reprocessar com divergência ignorada
                    setTimeout(() => {
                      handleValidar();
                    }, 100);
                  }}
                  className="inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none sm:text-sm"
                >
                  Manter {operadoraSelecionada?.nome}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setMostrarModalDivergencia(false);
                    setProcessando(false);
                    resetarTudo();
                  }}
                  className="inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none sm:text-sm"
                >
                  ✕ Cancelar Tudo
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
