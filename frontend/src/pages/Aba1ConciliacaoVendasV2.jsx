import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import { getAccessToken } from "../auth/tokenStorage";
import SaleReference from "../components/ui/SaleReference";
import { useEscapeToClose } from "../utils/modalEscape";

/**
 * ABA 1 V2: CONCILIAÇÃO DE VENDAS (Duas Colunas)
 *
 * Arquitetura:
 * - Coluna Esquerda: Vendas PDV com cartão (sempre carregadas)
 * - Coluna Direita: NSUs da planilha Stone importada
 * - Match automático + confirmação manual
 * - Filtro de status: não conciliado / conciliado / todas
 */
export default function Aba1ConciliacaoVendasV2({ onConcluida: _onConcluida, status: _status }) {
  const navigate = useNavigate();

  // Estados
  const [vendasPDV, setVendasPDV] = useState([]);
  const [nsusStone, setNsusStone] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState(null);
  const [expandido, setExpandido] = useState(false); // Toggle mostrar expandido
  const [arquivo, setArquivo] = useState(null);
  const [processando, setProcessando] = useState(false);
  const [matches, setMatches] = useState([]); // Matches após processar
  const [matchesConciliados, setMatchesConciliados] = useState([]); // Matches já conciliados (visualização)
  const [, setModoBusca] = useState(false); // true = após processar matches
  const [mostrarConfirmacao, setMostrarConfirmacao] = useState(false); // Mostrar botão confirmar

  // Filtro de status das vendas
  const [statusFiltro, setStatusFiltro] = useState("pendentes"); // 'pendentes' ou 'todas' ou 'conciliadas'

  // Operadoras
  const [operadoras, setOperadoras] = useState([]);
  const [operadoraSelecionada, setOperadoraSelecionada] = useState(null);
  const [carregandoOperadoras, setCarregandoOperadoras] = useState(true);

  // Paginação
  const [paginaPDV, setPaginaPDV] = useState(1);
  const [totalPaginasPDV, setTotalPaginasPDV] = useState(1);

  // Carregar operadoras ao montar
  useEffect(() => {
    const carregarOperadoras = async () => {
      try {
        const token = getAccessToken();
        if (!token) {
          setErro("Você precisa estar logado.");
          setTimeout(() => navigate("/login"), 2000);
          return;
        }

        const response = await api.get("/operadoras-cartao?apenas_ativas=true");
        setOperadoras(response.data);

        // Pré-selecionar operadora padrão
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
  }, [navigate]);

  // Carregar vendas PDV ao montar e quando mudar página/operadora/filtro
  useEffect(() => {
    if (operadoraSelecionada) {
      carregarVendasPDV();
      carregarNSUsStone(); // Recarregar NSUs também quando filtro muda
    }
  }, [paginaPDV, operadoraSelecionada, statusFiltro]);

  // Construir matches conciliados quando filtro = "conciliadas"
  useEffect(() => {
    if (statusFiltro === "conciliadas" && vendasPDV.length > 0 && nsusStone.length > 0) {
      const matchesConstruidos = [];

      // Para cada venda conciliada, buscar o NSU correspondente
      vendasPDV.forEach((venda) => {
        const pagamento = venda.pagamento || venda.pagamentos?.find((p) => p.nsu || p.nsu_cartao);
        const nsuVenda = pagamento?.nsu || pagamento?.nsu_cartao || venda.nsu;
        if (!nsuVenda) return;

        // Buscar NSU correspondente na planilha
        const nsuPlanilha = nsusStone.find((nsu) => nsu.nsu === nsuVenda);
        if (!nsuPlanilha) return;

        // Normalizar campos esperados pelo MatchPair
        const vendaNormalizada = {
          ...venda,
          numero: venda.numero || venda.numero_venda,
          nsu: nsuVenda,
          bandeira: pagamento?.bandeira,
          parcelas: pagamento?.parcelas,
          valor: pagamento?.valor ?? venda.total,
        };

        matchesConstruidos.push({
          venda_id: venda.id,
          status: "ok",
          venda_pdv: vendaNormalizada,
          venda_stone: nsuPlanilha,
        });
      });

      setMatchesConciliados(matchesConstruidos);
    } else {
      setMatchesConciliados([]);
    }
  }, [statusFiltro, vendasPDV, nsusStone]);

  // Suporte a ESC para fechar visualização de matches
  useEscapeToClose({
    isOpen: mostrarConfirmacao,
    onClose: () => {
      setMostrarConfirmacao(false);
      setMatches([]);
      setModoBusca(false);
    },
  });

  // Carregar NSUs Stone automaticamente ao selecionar operadora
  useEffect(() => {
    if (operadoraSelecionada) {
      carregarNSUsStone();
      carregarVendasPDV(); // Recarregar vendas ao trocar operadora
    }
  }, [operadoraSelecionada]);

  // Função: Carregar vendas PDV (coluna esquerda)
  const carregarVendasPDV = async () => {
    try {
      setCarregando(true);
      const token = getAccessToken();
      if (!token) {
        setErro("Você precisa estar logado.");
        setTimeout(() => navigate("/login"), 2000);
        return;
      }

      const response = await api.get("/conciliacao/aba1/vendas-pdv", {
        params: {
          status: statusFiltro, // Usar filtro selecionado pelo usuário
          operadora_id: operadoraSelecionada?.id === "legacy" ? "legacy" : operadoraSelecionada?.id, // Filtrar por operadora ou legacy
          page: paginaPDV,
          limit: 50,
        },
      });

      if (response.data.success) {
        setVendasPDV(response.data.vendas);
        setTotalPaginasPDV(response.data.total_pages);
      }
    } catch (error) {
      console.error("Erro ao carregar vendas PDV:", error);
      setErro("Erro ao carregar vendas do PDV");
    } finally {
      setCarregando(false);
    }
  };

  // Função: Upload planilha Stone
  const handleUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (!operadoraSelecionada) {
      alert(
        "⚠️ Selecione uma operadora primeiro!\n\nAs vendas da planilha serão importadas com a tag da operadora selecionada.\nIsso é importante para o processo de conciliação.",
      );
      event.target.value = ""; // Limpar input
      return;
    }

    // Bloquear upload para Legacy
    if (operadoraSelecionada.id === "legacy") {
      alert(
        '⚠️ Vendas Legacy não têm planilha!\n\nVendas sem operadora devem ter a operadora preenchida manualmente usando o botão "Preencher Operadora".',
      );
      event.target.value = ""; // Limpar input
      return;
    }

    // Confirmar operadora antes de subir
    const confirmar = window.confirm(
      `🎯 Confirmar Upload\n\n` +
        `Operadora selecionada: ${operadoraSelecionada.nome}\n\n` +
        `Todas as vendas da planilha "${file.name}" serão marcadas com esta operadora.\n\n` +
        `Deseja continuar?`,
    );

    if (!confirmar) {
      event.target.value = ""; // Limpar input se cancelar
      return;
    }

    setArquivo(file);
    setProcessando(true);
    setErro(null);

    const formData = new FormData();
    formData.append("arquivo", file);
    formData.append("operadora_id", operadoraSelecionada.id);

    try {
      const response = await api.post("/conciliacao/aba1/upload-stone", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      if (response.data.success) {
        // Planilha salva - carregar NSUs na coluna direita
        await carregarNSUsStone();
        await carregarVendasPDV();

        // Mostrar resultado
        alert(
          `✅ Planilha importada com sucesso!\n\n` +
            `📊 ${response.data.total_nsus || 0} NSUs carregados\n` +
            `Operadora: ${operadoraSelecionada.nome}\n\n` +
            `Clique em "Processar Matches" para conciliar automaticamente.`,
        );

        event.target.value = ""; // Limpar input para permitir novo upload
      }
    } catch (error) {
      console.error("Erro no upload:", error);
      setErro(error.response?.data?.detail || "Erro ao importar planilha");
      event.target.value = ""; // Limpar input em caso de erro
    } finally {
      setProcessando(false);
    }
  };

  // Função: Carregar NSUs não conciliados (filtrado por operadora)
  const carregarNSUsStone = async () => {
    if (!operadoraSelecionada) return;

    // Legacy não tem planilha
    if (operadoraSelecionada.id === "legacy") {
      setNsusStone([]);
      return;
    }

    try {
      const response = await api.get("/conciliacao/aba1/stone-nao-conciliadas", {
        params: {
          operadora_id: operadoraSelecionada.id, // FILTRAR por operadora
          status: statusFiltro, // FILTRAR por status (pendentes/todas/conciliadas)
        },
      });

      if (response.data.success) {
        setNsusStone(response.data.nsus);
      }
    } catch (error) {
      console.error("Erro ao carregar NSUs:", error);
    }
  };

  // Função: Processar matches automáticos (APENAS visualização)
  const handleProcessarMatches = async () => {
    if (!operadoraSelecionada) {
      alert("Selecione uma operadora primeiro!");
      return;
    }

    setProcessando(true);
    setErro(null);

    try {
      const response = await api.post("/conciliacao/aba1/processar-matches");

      if (response.data.success) {
        // Armazenar matches para visualização
        setMatches(response.data.matches || []);
        setMostrarConfirmacao(true);

        // Mostrar resumo
        alert(
          `🔍 Matches encontrados!\n\n` +
            `📊 Resumo:\n` +
            `• ${response.data.conferidas || 0} vendas OK\n` +
            `• ${response.data.corrigidas || 0} com divergências\n` +
            `• ${response.data.sem_nsu || 0} sem NSU\n` +
            `• ${response.data.orfaos || 0} NSUs órfãos\n\n` +
            `👀 Visualize os matches abaixo e confirme para conciliar.`,
        );
      }
    } catch (error) {
      console.error("Erro ao processar matches:", error);
      setErro(error.response?.data?.detail || "Erro ao processar matches automáticos");
    } finally {
      setProcessando(false);
    }
  };

  // Função: Confirmar APENAS matches OK e marcar como conciliado
  const handleConfirmarMatches = async () => {
    if (matches.length === 0) return;

    // Filtrar APENAS matches OK (sem divergências, sem órfãos)
    const matchesOK = matches.filter((m) => m.status === "ok");

    if (matchesOK.length === 0) {
      alert(
        "⚠️ Nenhum match OK para confirmar!\n\nApenas matches perfeitos (sem divergências) podem ser conciliados.",
      );
      return;
    }

    setProcessando(true);

    try {
      // Buscar importacao_id da última importação (filtrada por operadora)
      const responseStone = await api.get("/conciliacao/aba1/stone-nao-conciliadas", {
        params: {
          operadora_id: operadoraSelecionada?.id,
        },
      });
      const importacaoId = responseStone.data.importacao_id;

      const response = await api.post("/conciliacao/aba1/confirmar-matches", {
        importacao_id: importacaoId,
        matches_confirmados: matchesOK, // Enviar APENAS os OK
      });

      if (response.data.success) {
        alert("✅ " + response.data.message);

        // Limpar estados e recarregar TUDO
        setMatches([]);
        setMostrarConfirmacao(false);
        await carregarVendasPDV(); // Recarregar vendas (agora com NSU preenchido)
        await carregarNSUsStone(); // Recarregar NSUs (agora só os restantes/órfãos)
      }
    } catch (error) {
      console.error("Erro ao confirmar matches:", error);
      setErro(error.response?.data?.detail || "Erro ao confirmar matches");
    } finally {
      setProcessando(false);
    }
  };

  // Função: Atualizar operadora de um pagamento
  const handleAtualizarOperadora = async (pagamentoId, operadoraId) => {
    try {
      const response = await api.put("/conciliacao/aba1/atualizar-operadora", {
        pagamento_id: pagamentoId,
        operadora_id: operadoraId,
      });

      if (response.data.success) {
        await carregarVendasPDV(); // Recarrega lista
        alert(`Operadora atualizada para ${response.data.operadora_nome}`);
        return true;
      }
    } catch (error) {
      console.error("Erro ao atualizar operadora:", error);
      alert(error.response?.data?.detail || "Erro ao atualizar operadora");
      return false;
    }
  };

  // Componente: Item de venda PDV (compacto)
  const VendaPDVItem = ({ venda }) => {
    const [expanded, setExpanded] = useState(expandido);
    const [editandoNSU, setEditandoNSU] = useState(false);
    const [novoNSU, setNovoNSU] = useState("");
    const [editandoOperadora, setEditandoOperadora] = useState(false);
    const [novaOperadora, setNovaOperadora] = useState("");

    const handleSalvarNSU = async () => {
      if (!novoNSU || novoNSU.trim() === "") {
        alert("Digite um NSU válido");
        return;
      }

      try {
        const response = await api.patch(
          `/vendas/${venda.id}/pagamento/${venda.pagamento.id}/nsu`,
          {
            nsu_cartao: novoNSU.trim(),
          },
        );

        if (response.data) {
          setEditandoNSU(false);
          setNovoNSU("");
          await carregarVendasPDV(); // Recarrega lista
          alert("NSU atualizado com sucesso!");
        }
      } catch (error) {
        console.error("Erro ao salvar NSU:", error);
        alert(error.response?.data?.detail || "Erro ao salvar NSU");
      }
    };

    const handleSalvarOperadora = async () => {
      if (!novaOperadora || novaOperadora === "") {
        alert("Selecione uma operadora");
        return;
      }

      const sucesso = await handleAtualizarOperadora(venda.pagamento.id, parseInt(novaOperadora));
      if (sucesso) {
        setEditandoOperadora(false);
        setNovaOperadora("");
      }
    };

    return (
      <div
        className="border border-gray-200 rounded-lg p-3 mb-2 hover:bg-gray-50 cursor-pointer"
        onClick={(e) => {
          // Não expandir se clicar no input ou botões
          if (e.target.tagName === "INPUT" || e.target.tagName === "BUTTON") return;
          if (!expandido) setExpanded(!expanded);
        }}
      >
        {/* Modo Compacto */}
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-gray-900">
              <SaleReference sale={venda} showPrefix={false} />
            </span>

            {/* Badge de Operadora ou Campo de Edição */}
            {venda.pagamento.operadora_id && !editandoOperadora ? (
              <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded-full">
                {operadoras.find((op) => op.id === venda.pagamento.operadora_id)?.nome || "N/A"}
              </span>
            ) : editandoOperadora ? (
              <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                <select
                  value={novaOperadora}
                  onChange={(e) => setNovaOperadora(e.target.value)}
                  className="border border-purple-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-purple-500"
                  autoFocus
                >
                  <option value="">Selecione...</option>
                  {operadoras.map((op) => (
                    <option key={op.id} value={op.id}>
                      {op.nome}
                    </option>
                  ))}
                </select>
                <button
                  onClick={handleSalvarOperadora}
                  className="bg-green-500 text-white px-2 py-1 rounded text-xs hover:bg-green-600"
                >
                  ✓
                </button>
                <button
                  onClick={() => {
                    setEditandoOperadora(false);
                    setNovaOperadora("");
                  }}
                  className="bg-gray-400 text-white px-2 py-1 rounded text-xs hover:bg-gray-500"
                >
                  ✗
                </button>
              </div>
            ) : (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setEditandoOperadora(true);
                }}
                className="text-xs text-purple-600 hover:text-purple-700 underline font-medium px-2 py-1 bg-purple-50 rounded"
              >
                🏢 Sem Operadora - Clique aqui
              </button>
            )}

            {/* NSU ou Campo de Edição */}
            {venda.pagamento.nsu ? (
              <span className="text-sm text-green-600">NSU: {venda.pagamento.nsu}</span>
            ) : editandoNSU ? (
              <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                <input
                  type="text"
                  value={novoNSU}
                  onChange={(e) => setNovoNSU(e.target.value)}
                  placeholder="Digite o NSU"
                  className="border border-orange-300 rounded px-2 py-1 text-xs w-32 focus:outline-none focus:ring-1 focus:ring-orange-500"
                  autoFocus
                />
                <button
                  onClick={handleSalvarNSU}
                  className="bg-green-500 text-white px-2 py-1 rounded text-xs hover:bg-green-600"
                >
                  ✓
                </button>
                <button
                  onClick={() => {
                    setEditandoNSU(false);
                    setNovoNSU("");
                  }}
                  className="bg-gray-400 text-white px-2 py-1 rounded text-xs hover:bg-gray-500"
                >
                  ✗
                </button>
              </div>
            ) : (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setEditandoNSU(true);
                }}
                className="text-sm text-orange-600 hover:text-orange-700 underline font-medium"
              >
                SEM NSU - Clique para preencher
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">R$ {venda.total.toFixed(2)}</span>
            {!expandido && (
              <svg
                className={`h-4 w-4 text-gray-400 transition-transform ${expanded ? "rotate-180" : ""}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            )}
          </div>
        </div>

        {/* Modo Expandido */}
        {(expanded || expandido) && (
          <div className="mt-3 pt-3 border-t border-gray-200 text-sm space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-600">Data:</span>
              <span>{new Date(venda.data_venda).toLocaleDateString("pt-BR")}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Tipo:</span>
              <span className="capitalize">{venda.pagamento.forma}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Operadora:</span>
              <span className="font-medium text-blue-600">
                {operadoraSelecionada?.nome || "N/A"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Bandeira:</span>
              <span>{venda.pagamento.bandeira || "N/A"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Parcelas:</span>
              <span>{venda.pagamento.parcelas}x</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Valor:</span>
              <span className="font-medium">R$ {venda.pagamento.valor.toFixed(2)}</span>
            </div>
          </div>
        )}
      </div>
    );
  };

  // Componente: Item de NSU Stone (compacto)
  const NSUStoneItem = ({ nsu }) => {
    const [expanded, setExpanded] = useState(expandido);

    return (
      <div
        className="border border-blue-200 rounded-lg p-3 mb-2 hover:bg-blue-50 cursor-pointer"
        onClick={() => !expandido && setExpanded(!expanded)}
      >
        {/* Modo Compacto */}
        <div className="flex justify-between items-center">
          <div>
            <span className="font-medium text-blue-900">NSU: {nsu.nsu}</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">R$ {nsu.valor_liquido?.toFixed(2)}</span>
            {!expandido && (
              <svg
                className={`h-4 w-4 text-gray-400 transition-transform ${expanded ? "rotate-180" : ""}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            )}
          </div>
        </div>

        {/* Modo Expandido */}
        {(expanded || expandido) && nsu.data_venda && (
          <div className="mt-3 pt-3 border-t border-blue-200 text-sm space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-600">Data:</span>
              <span>{new Date(nsu.data_venda).toLocaleDateString("pt-BR")}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Bandeira:</span>
              <span>{nsu.bandeira}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Parcelas:</span>
              <span>{nsu.parcelas}x</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Valor Bruto:</span>
              <span>R$ {nsu.valor_bruto?.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Valor Líquido:</span>
              <span className="font-medium text-green-600">R$ {nsu.valor_liquido?.toFixed(2)}</span>
            </div>
          </div>
        )}
      </div>
    );
  };

  // Componente: Visualizador de Matches
  const MatchPair = ({ match, isConciliado = false }) => {
    const statusCor = {
      ok: "bg-green-50 border-green-300",
      divergencia: "bg-yellow-50 border-yellow-300",
      orfao: "bg-red-50 border-red-300",
      sem_nsu: "bg-orange-50 border-orange-300",
    };

    return (
      <div className={`border-2 rounded-lg p-4 mb-3 ${statusCor[match.status]} relative`}>
        {/* Badge de Conciliado */}
        {isConciliado && (
          <div className="absolute top-2 right-2 px-3 py-1 bg-green-600 text-white text-xs font-bold rounded-full">
            ✅ CONCILIADO
          </div>
        )}

        <div className="grid grid-cols-3 gap-4 items-center">
          {/* Venda PDV */}
          <div className="bg-white p-3 rounded border">
            {match.venda_pdv ? (
              <>
                <div className="text-sm font-semibold text-gray-800">
                  <SaleReference value={match.venda_pdv.numero} />
                </div>
                <div className="text-xs text-gray-600 mt-1">
                  NSU: {match.venda_pdv.nsu || <span className="text-orange-600">SEM NSU</span>}
                </div>
                <div className="text-xs text-gray-600">
                  {match.venda_pdv.bandeira} - {match.venda_pdv.parcelas}x
                </div>
                <div className="text-xs font-semibold text-gray-800 mt-1">
                  R$ {match.venda_pdv.valor?.toFixed(2)}
                </div>
              </>
            ) : (
              <div className="text-sm text-gray-400 italic">Sem venda no PDV</div>
            )}
          </div>

          {/* Conexão Visual */}
          <div className="flex items-center justify-center">
            {match.status === "ok" && <div className="text-green-600 text-2xl">✅</div>}
            {match.status === "divergencia" && (
              <div className="flex flex-col items-center">
                <div className="text-yellow-600 text-xl">⚠️</div>
                <div className="text-xs text-yellow-700 font-semibold mt-1">
                  {match.divergencia?.tipo}
                </div>
              </div>
            )}
            {match.status === "orfao" && <div className="text-red-600 text-2xl">❌</div>}
            {match.status === "sem_nsu" && <div className="text-orange-600 text-2xl">➡️</div>}
          </div>

          {/* Venda da Operadora (Planilha) */}
          <div className="bg-blue-50 p-3 rounded border border-blue-200">
            {match.venda_stone ? (
              <>
                <div className="text-sm font-semibold text-blue-800">Planilha Operadora</div>
                <div className="text-xs text-blue-700 mt-1">NSU: {match.venda_stone.nsu}</div>
                <div className="text-xs text-blue-600">
                  {match.venda_stone.bandeira} - {match.venda_stone.parcelas}x
                </div>
                <div className="text-xs font-semibold text-blue-800 mt-1">
                  R$ {match.venda_stone.valor_bruto?.toFixed(2)}
                </div>
              </>
            ) : (
              <div className="text-sm text-blue-300 italic">Sem NSU na planilha</div>
            )}
          </div>
        </div>

        {/* Detalhes da Divergência */}
        {match.divergencia && (
          <div className="mt-3 pt-3 border-t border-yellow-300">
            <div className="text-xs text-yellow-800">
              <span className="font-semibold">PDV:</span> {match.divergencia.pdv} →{" "}
              <span className="font-semibold">Stone:</span> {match.divergencia.stone}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full p-6 bg-gray-50">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Conciliação de Vendas - Stone</h2>
        <p className="text-sm text-gray-600 mt-1">
          Compare vendas do PDV com a planilha da operadora
        </p>
      </div>

      {/* Toolbar */}
      <div className="flex gap-4 mb-4 items-center bg-white p-4 rounded-lg shadow">
        {/* Filtro de Status */}
        <div className="flex flex-col">
          <label className="text-xs text-gray-600 mb-1">Exibir:</label>
          <select
            value={statusFiltro}
            onChange={(e) => setStatusFiltro(e.target.value)}
            className="border border-gray-300 rounded px-3 py-2 text-sm min-w-[180px] focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="pendentes">⏳ Pendentes (Não Conciliadas)</option>
            <option value="todas">📋 Todas as Vendas</option>
            <option value="conciliadas">✅ Conciliadas</option>
          </select>
        </div>

        {/* Seletor de Operadora */}
        <div className="flex flex-col">
          <label className="text-xs text-gray-600 mb-1">Operadora de Cartão:</label>
          <select
            value={operadoraSelecionada?.id || ""}
            onChange={(e) => {
              const valor = e.target.value;
              if (valor === "legacy") {
                setOperadoraSelecionada({ id: "legacy", nome: "Legacy (Sem Operadora)" });
              } else {
                const op = operadoras.find((o) => o.id === parseInt(valor));
                setOperadoraSelecionada(op);
              }
              // NSUs e vendas serão recarregados automaticamente pelo useEffect
            }}
            disabled={carregandoOperadoras}
            className="border border-gray-300 rounded px-3 py-2 text-sm min-w-[200px] focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Selecione...</option>
            <option value="legacy" className="text-orange-600 font-semibold">
              📦 Legacy (Sem Operadora)
            </option>
            {operadoras.map((op) => (
              <option key={op.id} value={op.id}>
                {op.nome} {op.padrao ? "(Padrão)" : ""}
              </option>
            ))}
          </select>
        </div>

        {/* Upload Planilha */}
        <div>
          <label
            className={`px-4 py-2 rounded-md ${
              operadoraSelecionada && operadoraSelecionada.id !== "legacy"
                ? "bg-blue-600 text-white hover:bg-blue-700 cursor-pointer"
                : "bg-gray-300 text-gray-500 cursor-not-allowed"
            }`}
          >
            📤 Upload Planilha
            <input
              type="file"
              accept=".csv"
              onChange={handleUpload}
              className="hidden"
              disabled={!operadoraSelecionada || operadoraSelecionada.id === "legacy"}
            />
          </label>
          {operadoraSelecionada?.id === "legacy" && (
            <p className="text-xs text-orange-600 mt-1">
              Vendas Legacy não têm planilha. Use o campo "Preencher Operadora".
            </p>
          )}
        </div>

        {/* Botão Processar Matches */}
        {nsusStone.length > 0 && !mostrarConfirmacao && operadoraSelecionada?.id !== "legacy" && (
          <button
            onClick={handleProcessarMatches}
            disabled={processando}
            className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400"
          >
            🔍 Processar Matches
          </button>
        )}

        {/* Botões Confirmar e Cancelar Matches */}
        {mostrarConfirmacao && matches.length > 0 && (
          <div className="flex gap-2">
            <button
              onClick={handleConfirmarMatches}
              disabled={processando}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 animate-pulse"
            >
              ✅ Confirmar Matches OK
            </button>

            <button
              onClick={() => {
                setMostrarConfirmacao(false);
                setMatches([]);
                setModoBusca(false);
              }}
              className="px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600"
            >
              ❌ Cancelar
            </button>
          </div>
        )}

        {/* Toggle Expandido */}
        <label className="flex items-center gap-2 ml-auto">
          <input
            type="checkbox"
            checked={expandido}
            onChange={() => setExpandido(!expandido)}
            className="rounded"
          />
          <span className="text-sm text-gray-700">Mostrar Expandido</span>
        </label>
      </div>

      {/* Erro */}
      {erro && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
          {erro}
        </div>
      )}

      {/* VISUALIZAÇÃO DE MATCHES (após processar OU quando filtro = conciliadas) */}
      {(mostrarConfirmacao && matches.length > 0) ||
      (statusFiltro === "conciliadas" && matchesConciliados.length > 0) ? (
        <div className="flex-1 overflow-hidden bg-white rounded-lg shadow">
          <div className="px-6 py-4 bg-gradient-to-r from-blue-100 to-green-100 border-b">
            <h3 className="text-lg font-bold text-gray-800">
              {statusFiltro === "conciliadas"
                ? "✅ Vendas Conciliadas"
                : "🔍 Matches Encontrados - Revise e Confirme"}
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              {statusFiltro === "conciliadas"
                ? "Vendas PDV conciliadas com NSUs da planilha"
                : "Matches OK no topo → Divergências → Sem match"}
            </p>
          </div>

          <div className="overflow-y-auto p-6" style={{ maxHeight: "calc(100vh - 300px)" }}>
            {statusFiltro === "conciliadas" ? (
              // Mostrar matches conciliados
              matchesConciliados.length > 0 ? (
                matchesConciliados.map((match, idx) => (
                  <MatchPair key={idx} match={match} isConciliado={true} />
                ))
              ) : (
                <div className="text-center text-gray-500 py-8">Nenhuma venda conciliada ainda</div>
              )
            ) : (
              // Mostrar matches para confirmação
              matches
                .sort((a, b) => {
                  const ordem = { ok: 1, divergencia: 2, orfao: 3, sem_nsu: 4 };
                  return ordem[a.status] - ordem[b.status];
                })
                .map((match, idx) => <MatchPair key={idx} match={match} />)
            )}
          </div>
        </div>
      ) : (
        /* Duas Colunas (upload/visualização normal) */
        <div className="flex-1 grid grid-cols-2 gap-4 overflow-hidden">
          {/* Coluna Esquerda: Vendas PDV */}
          <div className="flex flex-col bg-white rounded-lg shadow overflow-hidden">
            <div className="px-4 py-3 bg-gray-100 border-b border-gray-200">
              <h3 className="font-semibold text-gray-800">⬅️ Vendas PDV ({vendasPDV.length})</h3>
              <p className="text-xs text-gray-600 mt-1">Vendas com cartão pendentes</p>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {carregando ? (
                <div className="text-center text-gray-500 py-8">Carregando...</div>
              ) : vendasPDV.length === 0 ? (
                <div className="text-center text-gray-500 py-8">Nenhuma venda pendente</div>
              ) : (
                vendasPDV.map((venda) => <VendaPDVItem key={venda.id} venda={venda} />)
              )}
            </div>

            {/* Paginação */}
            {totalPaginasPDV > 1 && (
              <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 flex justify-between items-center">
                <button
                  onClick={() => setPaginaPDV((p) => Math.max(1, p - 1))}
                  disabled={paginaPDV === 1}
                  className="px-3 py-1 text-sm bg-white border rounded disabled:opacity-50"
                >
                  ← Anterior
                </button>
                <span className="text-sm text-gray-600">
                  Página {paginaPDV} de {totalPaginasPDV}
                </span>
                <button
                  onClick={() => setPaginaPDV((p) => Math.min(totalPaginasPDV, p + 1))}
                  disabled={paginaPDV === totalPaginasPDV}
                  className="px-3 py-1 text-sm bg-white border rounded disabled:opacity-50"
                >
                  Próxima →
                </button>
              </div>
            )}
          </div>

          {/* Coluna Direita: NSUs da Operadora Selecionada */}
          <div className="flex flex-col bg-white rounded-lg shadow overflow-hidden">
            <div className="px-4 py-3 bg-blue-100 border-b border-blue-200">
              <h3 className="font-semibold text-blue-900">
                {operadoraSelecionada ? `${operadoraSelecionada.nome} Planilha` : "Planilha"} ➡️ (
                {nsusStone.length})
              </h3>
              <p className="text-xs text-blue-700 mt-1">NSUs não conciliados</p>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {operadoraSelecionada?.id === "legacy" ? (
                <div className="text-center text-orange-600 py-8 bg-orange-50 rounded-lg border-2 border-orange-200">
                  <div className="text-5xl mb-4">📦</div>
                  <h4 className="font-bold text-lg mb-2">Vendas Legacy</h4>
                  <p className="text-sm max-w-md mx-auto">
                    Vendas sem operadora não possuem planilha para conciliação automática.
                  </p>
                  <p className="text-sm max-w-md mx-auto mt-2">
                    Use o botão <strong>"🏢 Preencher Operadora"</strong> nas vendas do lado
                    esquerdo para associá-las a uma operadora.
                  </p>
                </div>
              ) : nsusStone.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  {arquivo
                    ? "Processando..."
                    : `Faça upload da planilha ${operadoraSelecionada?.nome || ""}`}
                </div>
              ) : (
                nsusStone.map((nsu, idx) => <NSUStoneItem key={idx} nsu={nsu} />)
              )}
            </div>
          </div>
        </div>
      )}
      {/* Fim da condicional mostrarConfirmacao */}
    </div>
  );
}
