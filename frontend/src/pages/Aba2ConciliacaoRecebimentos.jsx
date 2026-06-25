import { useState, useEffect } from "react";
import api from "../api";
import Aba2ConciliacaoRecebimentosView from "./conciliacaoRecebimentos/Aba2ConciliacaoRecebimentosView";

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
export default function Aba2ConciliacaoRecebimentos({ onConcluida, status: _status }) {
  const [avisoOculto, setAvisoOculto] = useState(false);
  const [arquivos, setArquivos] = useState({
    recebimentos: null,
    recibo: null,
    ofx: null,
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
    console.log("🎯 Tentando avançar para Aba 3...");
    console.log("onConcluida existe?", typeof onConcluida);

    if (typeof onConcluida === "function") {
      console.log("✅ Chamando onConcluida()");
      onConcluida();
      console.log("✅ onConcluida() foi chamado com sucesso");
    } else {
      console.error("❌ onConcluida não é uma função!", onConcluida);
      alert("Erro: Função de callback não encontrada. Recarregue a página.");
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
    console.log("🔄 Estado resetado");
  };

  // Carregar operadoras ao montar
  useEffect(() => {
    const carregarOperadoras = async () => {
      try {
        const response = await api.get("/operadoras-cartao?apenas_ativas=true");
        setOperadoras(response.data);

        // Pré-selecionar operadora padrão (Stone geralmente)
        const padrao = response.data.find((op) => op.padrao);
        if (padrao) {
          setOperadoraSelecionada(padrao);
        }
      } catch (error) {
        console.error("Erro ao carregar operadoras:", error);
        setErro("Erro ao carregar operadoras");
      } finally {
        setCarregandoOperadoras(false);
      }
    };
    carregarOperadoras();
  }, []);

  useEffect(() => {
    const raw = localStorage.getItem("conciliacao_aba2_aviso_ate");
    if (!raw) return;
    const expiraEm = Number(raw);
    if (Number.isFinite(expiraEm) && Date.now() < expiraEm) {
      setAvisoOculto(true);
    }
  }, []);

  const ocultarAviso = (dias) => {
    const expiraEm = Date.now() + dias * 24 * 60 * 60 * 1000;
    localStorage.setItem("conciliacao_aba2_aviso_ate", String(expiraEm));
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
      lastModified: new Date(file.lastModified).toISOString(),
    });

    setArquivos((prev) => ({ ...prev, [tipo]: file }));
    setErro(null);
    setResultado(null); // Limpar resultado anterior
  };

  // Handler para abrir modal de confirmação
  const handleClickValidar = () => {
    if (!operadoraSelecionada) {
      setErro("Por favor, selecione uma operadora antes de validar.");
      return;
    }

    if (!arquivos.recebimentos || !arquivos.recibo || !arquivos.ofx) {
      setErro("Por favor, faça upload dos 3 arquivos antes de validar.");
      return;
    }

    setMostrarModalConfirmacao(true);
  };

  // Processar validação (após confirmação)
  const handleValidar = async () => {
    setMostrarModalConfirmacao(false);
    console.log("🚀 Iniciando validação...", {
      arquivos_estado: {
        recebimentos: !!arquivos.recebimentos,
        recibo: !!arquivos.recibo,
        ofx: !!arquivos.ofx,
      },
    });

    if (!arquivos.recebimentos || !arquivos.recibo || !arquivos.ofx) {
      setErro("Você precisa enviar os 3 arquivos para continuar");
      return;
    }

    // Validar que os arquivos são objetos File válidos
    console.log("🔍 Validando tipos de arquivo...", {
      recebimentos_isFile: arquivos.recebimentos instanceof File,
      recibo_isFile: arquivos.recibo instanceof File,
      ofx_isFile: arquivos.ofx instanceof File,
    });

    if (!(arquivos.recebimentos instanceof File)) {
      console.error("❌ Arquivo de recebimentos não é um File válido:", arquivos.recebimentos);
      setErro("Arquivo de recebimentos inválido. Por favor, selecione novamente.");
      setArquivos((prev) => ({ ...prev, recebimentos: null }));
      return;
    }

    if (!(arquivos.recibo instanceof File)) {
      console.error("❌ Arquivo de recibo não é um File válido:", arquivos.recibo);
      setErro("Arquivo de recibo inválido. Por favor, selecione novamente.");
      setArquivos((prev) => ({ ...prev, recibo: null }));
      return;
    }

    if (!(arquivos.ofx instanceof File)) {
      console.error("❌ Arquivo OFX não é um File válido:", arquivos.ofx);
      setErro("Arquivo OFX inválido. Por favor, selecione novamente.");
      setArquivos((prev) => ({ ...prev, ofx: null }));
      return;
    }

    setProcessando(true);
    setErro(null);

    try {
      // 1. Parsear arquivos
      let recebimentos_text, recibo_text, ofx_text;

      console.log("📂 Lendo arquivos:", {
        recebimentos: arquivos.recebimentos.name,
        recibo: arquivos.recibo.name,
        ofx: arquivos.ofx.name,
      });

      try {
        recebimentos_text = await arquivos.recebimentos.text();
        if (!recebimentos_text || recebimentos_text.trim().length === 0) {
          throw new Error("Arquivo de recebimentos está vazio");
        }
      } catch (fileError) {
        console.error("Erro ao ler recebimentos:", fileError);
        throw new Error(`Erro ao ler arquivo de recebimentos: ${fileError.message}`, {
          cause: fileError,
        });
      }

      try {
        recibo_text = await arquivos.recibo.text();
        if (!recibo_text || recibo_text.trim().length === 0) {
          throw new Error("Arquivo de recibo está vazio");
        }
      } catch (fileError) {
        console.error("Erro ao ler recibo:", fileError);
        throw new Error(`Erro ao ler arquivo de recibo: ${fileError.message}`, {
          cause: fileError,
        });
      }

      try {
        ofx_text = await arquivos.ofx.text();
        if (!ofx_text || ofx_text.trim().length === 0) {
          throw new Error("Arquivo OFX está vazio");
        }
      } catch (fileError) {
        console.error("Erro ao ler OFX:", fileError);
        throw new Error(`Erro ao ler arquivo OFX: ${fileError.message}`, {
          cause: fileError,
        });
      }

      console.log("📄 Arquivos carregados:", {
        recebimentos_length: recebimentos_text.length,
        recibo_length: recibo_text.length,
        ofx_length: ofx_text.length,
      });

      // Mostrar primeiras 3 linhas para debug
      const recebimentos_lines = recebimentos_text.split("\n");
      console.log("🔍 Primeiras 3 linhas do arquivo de recebimentos:");
      console.log("Linha 0 (header):", recebimentos_lines[0]);
      console.log("Linha 1:", recebimentos_lines[1]);
      console.log("Linha 2:", recebimentos_lines[2]);

      const recibo_lines = recibo_text.split("\n");
      console.log("🔍 Primeiras 3 linhas do arquivo de recibo:");
      console.log("Linha 0 (header):", recibo_lines[0]);
      console.log("Linha 1:", recibo_lines[1]);
      console.log("Linha 2:", recibo_lines[2]);

      // Detectar separador (vírgula ou ponto-e-vírgula)
      const separator = recebimentos_lines[0]?.includes(";") ? ";" : ",";
      console.log("📋 Separador detectado:", separator);

      let recebimentos_detalhados, recibo_lote, ofx_creditos;

      try {
        // Parsear recebimentos detalhados
        recebimentos_detalhados = recebimentos_text
          .split("\n")
          .slice(1)
          .filter((line) => line.trim())
          .map((line, idx) => {
            try {
              const campos = line.split(separator);

              // Log detalhado da primeira linha para debug
              if (idx === 0) {
                console.log("🔍 DEBUG - Primeira linha parseada:");
                console.log("Total de campos:", campos.length);
                console.log("Campos relevantes:");
                console.log("  Campo 8 (STONE ID/NSU):", campos[8]);
                console.log("  Campo 4 (DATA DE VENCIMENTO):", campos[4]);
                console.log("  Campo 12 (VALOR LÍQUIDO):", campos[12]);
                console.log("  Campo 10 (Nº DA PARCELA):", campos[10]);
                console.log("  Campo 9 (QTD DE PARCELAS):", campos[9]);
                console.log("  Campo 16 (ÚLTIMO STATUS):", campos[16]);
              }

              // Formato da Stone:
              // 0:DOCUMENTO, 1:STONECODE, 2:CATEGORIA, 3:DATA DA VENDA,
              // 4:DATA DE VENCIMENTO, 5:DATA DE VENCIMENTO ORIGINAL, 6:BANDEIRA, 7:PRODUTO,
              // 8:STONE ID, 9:QTD DE PARCELAS, 10:Nº DA PARCELA, 11:VALOR BRUTO,
              // 12:VALOR LÍQUIDO, 13:DESCONTO DE MDR, 14:DESCONTO DE ANTECIPAÇÃO,
              // 15:DESCONTO UNIFICADO, 16:ÚLTIMO STATUS, 17:DATA DO ÚLTIMO STATUS

              const nsu = campos[8]?.trim(); // STONE ID
              const data = campos[4]?.trim(); // DATA DE VENCIMENTO
              const valorOriginal = campos[12]?.trim(); // VALOR LÍQUIDO
              const parcela = campos[10]?.trim(); // Nº DA PARCELA
              const totalParcelas = campos[9]?.trim(); // QTD DE PARCELAS
              const status = campos[16]?.trim(); // ÚLTIMO STATUS

              // Converter valor: trocar vírgula por ponto (formato brasileiro)
              const valorLimpo = valorOriginal?.replace(",", ".");
              const valorFinal = parseFloat(valorLimpo || 0);

              // Log para primeira linha
              if (idx === 0) {
                console.log("💰 Conversão de valor:");
                console.log("  Original:", valorOriginal);
                console.log("  Limpo:", valorLimpo);
                console.log("  Final:", valorFinal);
                console.log("  Is NaN?", isNaN(valorFinal));
              }

              return {
                nsu: nsu,
                data_recebimento: data,
                valor: valorFinal,
                parcela_numero: parseInt(parcela || 1),
                total_parcelas: parseInt(totalParcelas || 1),
                tipo_recebimento: status || "Pago",
                lote_id: null, // Stone não tem lote_id neste formato
              };
            } catch (err) {
              console.error(`Erro ao parsear linha ${idx + 1} de recebimentos:`, line, err);
              throw new Error(`Erro na linha ${idx + 1} do arquivo de recebimentos detalhados`, {
                cause: err,
              });
            }
          });
      } catch (err) {
        setErro(`❌ Erro ao processar arquivo de recebimentos: ${err.message}`);
        return;
      }

      try {
        // Parsear recibo lote (Comprovante de Pagamentos Stone - 19 colunas)
        // Formato: Valor;Bandeira;Modalidade;...;Identificador Rastreável do Pagamento;...;Status do Pagamento
        const recibo_separator = recibo_lines[0]?.includes(";") ? ";" : ",";

        console.log("📄 Primeira linha do recibo:", recibo_lines[0]);
        console.log("📄 Segunda linha do recibo:", recibo_lines[1]);

        recibo_lote = recibo_text
          .split("\n")
          .slice(1)
          .filter((line) => line.trim())
          .map((line, idx) => {
            try {
              const campos = line.split(recibo_separator);

              // Log primeira linha para debug
              if (idx === 0) {
                console.log("🔍 DEBUG - Recibo primeira linha parseada:");
                console.log("Total de campos:", campos.length);
                console.log("  Campo 0 (Valor):", campos[0]);
                console.log("  Campo 13 (ID Rastreável):", campos[13]);
                console.log("  Campo 18 (Status):", campos[18]);
              }

              // Coluna 0: Valor
              // Coluna 13: Identificador Rastreável do Pagamento (ID único)
              // Coluna 18: Status do Pagamento
              const valorOriginal = campos[0]?.trim();
              const lote_id = campos[13]?.trim();
              const status = campos[18]?.trim();

              // Converter valor: trocar vírgula por ponto (formato brasileiro)
              const valorLimpo = valorOriginal?.replace(",", ".");
              const valorFinal = parseFloat(valorLimpo || 0);

              if (idx === 0) {
                console.log("💰 Conversão recibo:");
                console.log("  Original:", valorOriginal);
                console.log("  Limpo:", valorLimpo);
                console.log("  Final:", valorFinal);
              }

              return {
                lote_id: lote_id,
                valor: valorFinal,
                status: status,
              };
            } catch (err) {
              console.error(`Erro ao parsear linha ${idx + 1} de recibo:`, line, err);
              throw new Error(`Erro na linha ${idx + 1} do arquivo de recibo de lote`, {
                cause: err,
              });
            }
          });
      } catch (err) {
        setErro(`❌ Erro ao processar arquivo de recibo: ${err.message}`);
        return;
      }

      try {
        // Parsear OFX (formato STMTTRN)
        console.log("📄 Primeiras linhas do OFX:", ofx_text.split("\n").slice(0, 30).join("\n"));

        const transactions = [];
        const lines = ofx_text.split("\n");
        let currentTransaction = null;

        for (let i = 0; i < lines.length; i++) {
          const line = lines[i].trim();

          if (line === "<STMTTRN>") {
            currentTransaction = {};
          } else if (line === "</STMTTRN>" && currentTransaction) {
            // Só adicionar créditos (CREDIT ou valores positivos)
            if (
              currentTransaction.type === "CREDIT" ||
              (currentTransaction.valor && currentTransaction.valor > 0)
            ) {
              transactions.push(currentTransaction);
            }
            currentTransaction = null;
          } else if (currentTransaction) {
            // Extrair campos
            if (line.startsWith("<TRNTYPE>")) {
              currentTransaction.type = line.replace("<TRNTYPE>", "").replace("</TRNTYPE>", "");
            } else if (line.startsWith("<DTPOSTED>")) {
              currentTransaction.data = line.replace("<DTPOSTED>", "").replace("</DTPOSTED>", "");
            } else if (line.startsWith("<TRNAMT>")) {
              const valor = line.replace("<TRNAMT>", "").replace("</TRNAMT>", "");
              currentTransaction.valor = parseFloat(valor);
            } else if (line.startsWith("<FITID>")) {
              currentTransaction.id = line.replace("<FITID>", "").replace("</FITID>", "");
            } else if (line.startsWith("<MEMO>")) {
              currentTransaction.memo = line.replace("<MEMO>", "").replace("</MEMO>", "");
            }
          }
        }

        ofx_creditos = transactions;
        console.log("💳 OFX parseado:", ofx_creditos.length, "transações encontradas");
        if (ofx_creditos.length > 0) {
          console.log("Primeira transação:", ofx_creditos[0]);
        }
      } catch (err) {
        console.error("Erro ao parsear OFX:", err);
        setErro(`❌ Erro ao processar arquivo OFX: ${err.message}`);
        return;
      }

      // Validar que não estão vazios
      if (recebimentos_detalhados.length === 0) {
        setErro(
          "❌ Arquivo de recebimentos detalhados está vazio ou mal formatado. Verifique o formato CSV.",
        );
        return;
      }

      if (recibo_lote.length === 0) {
        setErro(
          "❌ Arquivo de recibo de lote está vazio ou mal formatado. Verifique o formato CSV.",
        );
        return;
      }

      if (ofx_creditos.length === 0) {
        setErro("❌ Arquivo OFX está vazio ou mal formatado. Verifique o formato.");
        return;
      }

      // Validar valores parseados
      const recebimentosInvalidos = recebimentos_detalhados.filter(
        (r) => isNaN(r.valor) || r.valor === null,
      );
      if (recebimentosInvalidos.length > 0) {
        console.error("❌ Recebimentos com valores inválidos:", recebimentosInvalidos);
        console.error("📋 Primeiras 5 linhas RAW do arquivo:");
        recebimentos_lines.slice(0, 6).forEach((line, idx) => {
          console.error(`Linha ${idx}:`, line);
        });
        setErro(
          `❌ ${recebimentosInvalidos.length} recebimentos têm valores inválidos. Verifique o formato dos valores no CSV (use vírgula ou ponto decimal). Veja o console para mais detalhes.`,
        );
        return;
      }

      const lotesInvalidos = recibo_lote.filter((l) => isNaN(l.valor) || l.valor === null);
      if (lotesInvalidos.length > 0) {
        console.error("❌ Lotes com valores inválidos:", lotesInvalidos);
        setErro(
          `❌ ${lotesInvalidos.length} lotes têm valores inválidos. Verifique o formato dos valores no CSV.`,
        );
        return;
      }

      console.log("✅ Todos os valores validados! Enviando para API...");

      // 2. Log para debug
      console.log("📤 Enviando dados para API:", {
        recebimentos_count: recebimentos_detalhados.length,
        recibo_count: recibo_lote.length,
        ofx_count: ofx_creditos.length,
        sample_recebimento: recebimentos_detalhados[0],
        sample_recebimento_2: recebimentos_detalhados[1],
        sample_recibo: recibo_lote[0],
        sample_ofx: ofx_creditos[0],
      });

      console.log("💰 Valores parseados (primeiros 3):");
      console.log("Recebimento 1:", recebimentos_detalhados[0]?.valor);
      console.log("Recebimento 2:", recebimentos_detalhados[1]?.valor);
      console.log("Recibo 1:", recibo_lote[0]?.valor);
      console.log("OFX 1:", ofx_creditos[0]?.valor);

      // 2.5 - Extrair data de referência dos recebimentos
      const extrairDataReferencia = (recebimentos) => {
        const datas = {};

        recebimentos.forEach((rec) => {
          // Procurar campo de data (pode ter vários nomes)
          const camposData = [
            "data",
            "data_recebimento",
            "data_pagamento",
            "Data de Pagamento",
            "Data do Pagamento",
          ];

          for (const campo of camposData) {
            if (rec[campo]) {
              // Normalizar data para YYYY-MM-DD
              let dataStr = rec[campo];

              // Converter DD/MM/YYYY para YYYY-MM-DD
              if (dataStr.match(/^\d{2}\/\d{2}\/\d{4}$/)) {
                const [dia, mes, ano] = dataStr.split("/");
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
      console.log("📅 Data de referência detectada:", dataReferencia);

      // Metadados dos arquivos para histórico
      const arquivosInfo = [
        {
          nome: arquivos.recebimentos.name,
          tamanho: arquivos.recebimentos.size,
          tipo: "recebimentos_detalhados",
        },
        { nome: arquivos.recibo.name, tamanho: arquivos.recibo.size, tipo: "recibo_lote" },
        { nome: arquivos.ofx.name, tamanho: arquivos.ofx.size, tipo: "extrato_ofx" },
      ];

      // 3. Chamar API
      const response = await api.post("/conciliacao/aba2/validar-recebimentos", {
        recebimentos_detalhados,
        recibo_lote,
        ofx_creditos,
        data_referencia: dataReferencia,
        arquivos_info: arquivosInfo,
        operadora: operadoraSelecionada?.nome,
      });

      // Verificar divergência de operadora (somente se não ignorar)
      if (!ignorarDivergenciaOperadora) {
        const operadoraSelecionadaNome = operadoraSelecionada.nome;
        const operadoraDetectadaNome = response.data.operadora_detectada;
        const confianca = response.data.confianca_deteccao || 0;

        console.log("🔍 Comparação de operadoras:", {
          selecionada: operadoraSelecionadaNome,
          detectada: operadoraDetectadaNome,
          confianca: confianca,
          ignorar: ignorarDivergenciaOperadora,
        });

        // Se operadora detectada é diferente e confiança >= 70%, mostrar aviso
        if (
          operadoraDetectadaNome &&
          operadoraSelecionadaNome !== operadoraDetectadaNome &&
          confianca >= 0.7
        ) {
          setOperadoraDetectada(operadoraDetectadaNome);
          setConfiancaDeteccao(confianca);
          setResultado(response.data); // Salvar resultado temporariamente
          setMostrarModalDivergencia(true);
          setProcessando(false);
          return; // Aguardar decisão do usuário
        }
      }

      setResultado(response.data);

      console.log("📊 Resultado da validação:", {
        success: response.data.success,
        tem_divergencias: response.data.tem_divergencias,
        validado: response.data.validado,
        historico_id: response.data.historico_id,
        operadora_detectada: response.data.operadora_detectada,
        ja_conciliado: response.data.ja_conciliado,
      });

      // Mostrar aviso se já foi conciliado antes
      if (response.data.ja_conciliado && response.data.aviso_reprocessamento) {
        console.warn("⚠️ Reprocessamento detectado:", response.data.aviso_reprocessamento);
      }

      // Sempre avança se success=true (divergências são informativas)
      if (response.data.success) {
        // Se não tem divergências, avança automaticamente
        if (!response.data.tem_divergencias) {
          console.log("✅ Validação perfeita, avançando automaticamente em 1.5s...");
          setTimeout(() => {
            handleAvancar();
          }, 1500);
        } else {
          console.log("⚠️ Tem divergências, aguardando decisão do usuário...");
        }
        // Se tem divergências, usuário precisa confirmar manualmente
      }
    } catch (error) {
      console.error("Erro ao validar:", error);
      console.error("Detalhes do erro:", error.response?.data);

      // Mostrar erro detalhado para debug
      const errorMsg =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        JSON.stringify(error.response?.data) ||
        "Erro ao validar recebimentos";

      setErro(errorMsg);
    } finally {
      setProcessando(false);
    }
  };

  const todosArquivosEnviados = arquivos.recebimentos && arquivos.recibo && arquivos.ofx;

  return (
    <Aba2ConciliacaoRecebimentosView
      avisoOculto={avisoOculto}
      setAvisoOculto={setAvisoOculto}
      ocultarAviso={ocultarAviso}
      operadoras={operadoras}
      operadoraSelecionada={operadoraSelecionada}
      setOperadoraSelecionada={setOperadoraSelecionada}
      carregandoOperadoras={carregandoOperadoras}
      processando={processando}
      setProcessando={setProcessando}
      arquivos={arquivos}
      handleFileChange={handleFileChange}
      todosArquivosEnviados={todosArquivosEnviados}
      resultado={resultado}
      setResultado={setResultado}
      erro={erro}
      setErro={setErro}
      resetarTudo={resetarTudo}
      handleClickValidar={handleClickValidar}
      handleValidar={handleValidar}
      handleAvancar={handleAvancar}
      mostrarModalConfirmacao={mostrarModalConfirmacao}
      setMostrarModalConfirmacao={setMostrarModalConfirmacao}
      mostrarModalDivergencia={mostrarModalDivergencia}
      setMostrarModalDivergencia={setMostrarModalDivergencia}
      operadoraDetectada={operadoraDetectada}
      setOperadoraDetectada={setOperadoraDetectada}
      confiancaDeteccao={confiancaDeteccao}
      setIgnorarDivergenciaOperadora={setIgnorarDivergenciaOperadora}
    />
  );
}
