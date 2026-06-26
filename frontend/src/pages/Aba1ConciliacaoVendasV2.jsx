import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import { getAccessToken } from "../auth/tokenStorage";
import { useEscapeToClose } from "../utils/modalEscape";
import { MatchPair, NSUStoneItem, VendaPDVItem } from "./conciliacao/Aba1ConciliacaoCards";

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
                vendasPDV.map((venda) => (
                  <VendaPDVItem
                    key={venda.id}
                    expandido={expandido}
                    onAtualizarOperadora={handleAtualizarOperadora}
                    onRecarregarVendas={carregarVendasPDV}
                    operadoraSelecionada={operadoraSelecionada}
                    operadoras={operadoras}
                    venda={venda}
                  />
                ))
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
                nsusStone.map((nsu, idx) => (
                  <NSUStoneItem key={idx} expandido={expandido} nsu={nsu} />
                ))
              )}
            </div>
          </div>
        </div>
      )}
      {/* Fim da condicional mostrarConfirmacao */}
    </div>
  );
}
