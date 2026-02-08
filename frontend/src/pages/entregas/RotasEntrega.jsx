import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../../api";

export default function RotasEntrega() {
  const navigate = useNavigate();
  const [rotas, setRotas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtroStatus, setFiltroStatus] = useState("");
  const [rotaExpandida, setRotaExpandida] = useState(null);

  useEffect(() => {
    carregarRotas();
  }, [filtroStatus]);

  async function carregarRotas() {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filtroStatus) {
        params.append("status", filtroStatus);
      }
      
      const response = await api.get(`/rotas-entrega/?${params.toString()}`);
      setRotas(response.data);
    } catch (err) {
      console.error("Erro ao carregar rotas:", err);
      alert("Erro ao carregar rotas de entrega");
    } finally {
      setLoading(false);
    }
  }

  function toggleRotaExpandida(rotaId) {
    if (rotaExpandida === rotaId) {
      setRotaExpandida(null);
    } else {
      setRotaExpandida(rotaId);
    }
  }

  async function reordenarParadas(rotaId, paradasOrdenadas) {
    try {
      // API call para atualizar ordem das paradas
      // Backend espera lista de IDs na nova ordem
      const novaOrdem = paradasOrdenadas.map(p => p.id);
      
      await api.put(`/rotas-entrega/${rotaId}/paradas/reordenar`, novaOrdem);
      
      // Atualizar localmente
      setRotas(prev => prev.map(r => 
        r.id === rotaId 
          ? { ...r, paradas: paradasOrdenadas.map((p, idx) => ({ ...p, ordem: idx + 1 })) }
          : r
      ));
      
      alert("Ordem das paradas atualizada!");
    } catch (err) {
      console.error("Erro ao reordenar paradas:", err);
      alert("Erro ao reordenar paradas");
    }
  }

  async function iniciarRota(rotaId) {
    if (!confirm("Deseja iniciar esta rota? Uma mensagem será enviada ao primeiro cliente.")) {
      return;
    }
    
    // Solicitar KM inicial (opcional)
    const kmInicial = prompt("🏍️ Digite o KM atual da moto (opcional):\n\nDeixe em branco se não quiser registrar.");

    try {
      const params = {};
      if (kmInicial && !isNaN(kmInicial) && parseFloat(kmInicial) > 0) {
        params.km_inicial = parseFloat(kmInicial);
      }
      
      await api.post(`/rotas-entrega/${rotaId}/iniciar`, null, { params });
      alert("✅ Rota iniciada! Mensagem enviada ao primeiro cliente.");
      carregarRotas(); // Recarregar lista para atualizar status
    } catch (err) {
      console.error("Erro ao iniciar rota:", err);
      const mensagem = err.response?.data?.detail || "Erro ao iniciar rota";
      alert(`❌ ${mensagem}`);
    }
  }

  async function excluirRota(rotaId) {
    if (!confirm("⚠️ Tem certeza que deseja excluir esta rota?\n\nAs vendas voltarão para a listagem de entregas pendentes.")) {
      return;
    }

    try {
      const response = await api.delete(`/rotas-entrega/${rotaId}`);
      const { total_vendas } = response.data;
      alert(`✅ Rota excluída com sucesso!\n${total_vendas} venda(s) voltaram para entregas pendentes.`);
      carregarRotas(); // Recarregar lista
    } catch (err) {
      console.error("Erro ao excluir rota:", err);
      const mensagem = err.response?.data?.detail || "Erro ao excluir rota";
      alert(`❌ ${mensagem}`);
    }
  }

  async function reverterInicioRota(rotaId) {
    if (!confirm("↩️ Reverter início desta rota?\n\nA rota voltará para status pendente e você poderá adicionar mais entregas.")) {
      return;
    }

    try {
      await api.post(`/rotas-entrega/${rotaId}/reverter-inicio`);
      alert("✅ Rota revertida para pendente! Agora você pode adicionar mais entregas.");
      carregarRotas(); // Recarregar lista
    } catch (err) {
      console.error("Erro ao reverter rota:", err);
      const mensagem = err.response?.data?.detail || "Erro ao reverter início da rota";
      alert(`❌ ${mensagem}`);
    }
  }

  function calcularTempoEstimado(rota) {
    if (!rota.paradas || rota.paradas.length === 0) return null;
    
    // Só mostrar tempo se a rota foi otimizada (tem tempo_acumulado nas paradas)
    const ultimaParada = rota.paradas[rota.paradas.length - 1];
    if (ultimaParada.tempo_acumulado) {
      return ultimaParada.tempo_acumulado;
    }
    
    // Se não foi otimizada, retornar null (não mostrar estimativa)
    return null;
  }

  function formatarTempo(segundos) {
    if (!segundos) return "N/A";
    // Converter de segundos para minutos
    const minutos = Math.floor(segundos / 60);
    const horas = Math.floor(minutos / 60);
    const mins = minutos % 60;
    if (horas > 0) {
      return `${horas}h${mins}min`;
    }
    return `${mins}min`;
  }

  function getStatusColor(status) {
    switch (status) {
      case "pendente": return "#FFA500";
      case "em_andamento": return "#007BFF";
      case "em_rota": return "#007BFF";
      case "concluida": return "#28A745";
      case "cancelada": return "#DC3545";
      default: return "#6C757D";
    }
  }

  function getStatusLabel(status) {
    switch (status) {
      case "pendente": return "🟠 Pendente";
      case "em_andamento": return "🔵 Em Andamento";
      case "em_rota": return "🔵 Em Rota";
      case "concluida": return "✅ Concluída";
      case "cancelada": return "❌ Cancelada";
      default: return status;
    }
  }

  if (loading) {
    return (
      <div className="page">
        <h1>Rotas de Entrega</h1>
        <p>Carregando rotas...</p>
      </div>
    );
  }

  return (
    <div className="page">
      <h1>Rotas de Entrega</h1>
      <p style={{ color: "#666", marginBottom: 20 }}>
        Rotas criadas e em andamento
      </p>

      <div style={{ marginBottom: 20, display: "flex", gap: 10, alignItems: "center" }}>
        <label>
          Filtrar por status:
          <select
            value={filtroStatus}
            onChange={(e) => setFiltroStatus(e.target.value)}
            style={{ marginLeft: 10, padding: "5px 10px" }}
          >
            <option value="">Todos</option>
            <option value="pendente">Pendente</option>
            <option value="em_andamento">Em Andamento</option>
            <option value="concluida">Concluída</option>
            <option value="cancelada">Cancelada</option>
          </select>
        </label>

        <button
          onClick={carregarRotas}
          className="btn-secondary"
          style={{ marginLeft: "auto" }}
        >
          🔄 Atualizar
        </button>
      </div>

      {!Array.isArray(rotas) || rotas.length === 0 ? (
        <div className="empty-state">
          <p>Nenhuma rota encontrada</p>
          <button
            onClick={() => navigate("/entregas/abertas")}
            className="btn-primary"
            style={{ marginTop: 10 }}
          >
            Criar Nova Rota
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 15 }}>
          {rotas.map((rota) => (
            <RotaCard
              key={rota.id}
              rota={rota}
              expandida={rotaExpandida === rota.id}
              onToggleExpand={() => toggleRotaExpandida(rota.id)}
              onReordenar={reordenarParadas}
              onIniciarRota={iniciarRota}
              onExcluirRota={excluirRota}
              onReverterInicio={reverterInicioRota}
              getStatusColor={getStatusColor}
              getStatusLabel={getStatusLabel}
              calcularTempoEstimado={calcularTempoEstimado}
              formatarTempo={formatarTempo}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Componente separado para o card da rota
function RotaCard({ 
  rota, 
  expandida, 
  onToggleExpand, 
  onReordenar,
  onIniciarRota,
  onExcluirRota,
  onReverterInicio,
  getStatusColor,
  getStatusLabel,
  calcularTempoEstimado,
  formatarTempo
}) {
  const [paradasOrdenadas, setParadasOrdenadas] = useState(rota.paradas || []);
  const [draggedIndex, setDraggedIndex] = useState(null);
  const [paradaDetalhesAberta, setParadaDetalhesAberta] = useState(null); // ID da parada com detalhes abertos
  const [vendaDetalhes, setVendaDetalhes] = useState(null);
  const [loadingDetalhes, setLoadingDetalhes] = useState(false);
  const [processandoEntrega, setProcessandoEntrega] = useState(null); // ID da parada sendo marcada como entregue
  const [processandoNaoEntregue, setProcessandoNaoEntregue] = useState(null);
  const [processandoFinalizacao, setProcessandoFinalizacao] = useState(false);

  useEffect(() => {
    setParadasOrdenadas(rota.paradas || []);
  }, [rota.paradas]);

  const tempoEstimado = calcularTempoEstimado(rota);
  
  // Calcular paradas pendentes
  const paradasPendentes = paradasOrdenadas.filter(p => p.status !== "entregue").length;
  const todasEntregue = paradasOrdenadas.length > 0 && paradasPendentes === 0;

  async function carregarDetalhesVenda(paradaId, vendaId) {
    try {
      setLoadingDetalhes(true);
      setParadaDetalhesAberta(paradaId);
      const response = await api.get(`/vendas/${vendaId}`);
      console.log('📦 Detalhes da venda carregados:', response.data);
      console.log('📞 Telefones do cliente:', {
        telefone: response.data.cliente?.telefone,
        celular: response.data.cliente?.celular,
        email: response.data.cliente?.email
      });
      setVendaDetalhes(response.data);
    } catch (err) {
      console.error("Erro ao carregar detalhes da venda:", err);
      alert("Erro ao carregar detalhes da venda");
      setParadaDetalhesAberta(null);
    } finally {
      setLoadingDetalhes(false);
    }
  }

  function fecharDetalhes() {
    setParadaDetalhesAberta(null);
    setVendaDetalhes(null);
  }

  async function marcarComoEntregue(paradaId, rotaId) {
    if (!confirm("✅ Confirmar entrega realizada?\n\nUma mensagem será enviada automaticamente para o próximo cliente da rota.")) {
      return;
    }
    
    // Solicitar KM da entrega (opcional)
    const kmEntrega = prompt("🏍️ Digite o KM atual da moto (opcional):\n\nDeixe em branco se não quiser registrar.");

    try {
      setProcessandoEntrega(paradaId);
      
      const params = {};
      if (kmEntrega && !isNaN(kmEntrega) && parseFloat(kmEntrega) > 0) {
        params.km_entrega = parseFloat(kmEntrega);
      }
      
      const response = await api.post(`/rotas-entrega/${rotaId}/paradas/${paradaId}/marcar-entregue`, null, { params });
      alert("✅ " + response.data.message);
      
      // Atualizar estado local da parada
      setParadasOrdenadas(prev => prev.map(p => 
        p.id === paradaId 
          ? { ...p, status: "entregue", data_entrega: new Date().toISOString(), km_entrega: kmEntrega ? parseFloat(kmEntrega) : null }
          : p
      ));
      
      // Recarregar a rota completa para garantir sincronização
      window.location.reload();
    } catch (err) {
      console.error("Erro ao marcar entrega:", err);
      const mensagem = err.response?.data?.detail || "Erro ao marcar entrega como concluída";
      alert("❌ " + mensagem);
    } finally {
      setProcessandoEntrega(null);
    }
  }

  async function adicionarObservacao(paradaId, rotaId) {
    const observacao = prompt("📋 Digite a observação sobre esta entrega:\n\n(Ex: 'Sempre entregar no vizinho', 'Chamar na casa da frente')");
    
    if (!observacao || observacao.trim() === "") {
      return;
    }

    try {
      await api.put(`/rotas-entrega/${rotaId}/paradas/${paradaId}/observacao`, null, {
        params: { observacao: observacao.trim() }
      });
      
      alert("✅ Observação salva com sucesso!");
      
      // Atualizar localmente
      setParadasOrdenadas(prev => prev.map(p => 
        p.id === paradaId 
          ? { ...p, observacoes: observacao.trim() }
          : p
      ));
    } catch (err) {
      console.error("Erro ao salvar observação:", err);
      alert("❌ Erro ao salvar observação");
    }
  }

  async function marcarNaoEntregue(paradaId, rotaId, vendaId) {
    const motivo = prompt("⚠️ Por que a entrega não foi realizada?\n\n(Ex: 'Cliente ausente', 'Cartão recusado', 'Endereço não encontrado')");
    
    if (!motivo || motivo.trim() === "") {
      return;
    }

    if (!confirm("⚠️ Confirmar que a entrega NÃO foi realizada?\n\nA venda voltará para entregas em aberto.")) {
      return;
    }

    try {
      setProcessandoNaoEntregue(paradaId);
      await api.post(`/rotas-entrega/${rotaId}/paradas/${paradaId}/nao-entregue`, null, {
        params: { motivo: motivo.trim() }
      });
      
      alert("✅ Entrega marcada como não realizada. Venda #" + vendaId + " voltou para entregas em aberto.");
      window.location.reload();
    } catch (err) {
      console.error("Erro ao marcar como não entregue:", err);
      alert("❌ Erro ao processar");
    } finally {
      setProcessandoNaoEntregue(null);
    }
  }

  async function finalizarRota(rotaId, kmInicial) {
    // Solicitar KM final (opcional)
    const kmFinal = prompt("🏍️ Digite o KM final da moto (opcional):\n\nDeixe em branco se não quiser registrar.");
    
    let distanciaReal = null;
    
    // Se tiver KM inicial e final, mostrar distância calculada
    if (kmInicial && kmFinal && !isNaN(kmFinal) && parseFloat(kmFinal) > parseFloat(kmInicial)) {
      const distanciaCalculada = (parseFloat(kmFinal) - parseFloat(kmInicial)).toFixed(2);
      const confirmaDistancia = confirm(
        `📏 Distância calculada: ${distanciaCalculada} km\n\n` +
        `KM Inicial: ${kmInicial}\n` +
        `KM Final: ${kmFinal}\n\n` +
        `Deseja usar esta distância?`
      );
      
      if (confirmaDistancia) {
        distanciaReal = parseFloat(distanciaCalculada);
      }
    }
    
    // Se não calculou automaticamente, solicitar manualmente (opcional)
    if (!distanciaReal) {
      const distanciaManual = prompt("📏 Digite a distância percorrida em km (opcional):\n\nDeixe em branco se não souber.");
      if (distanciaManual && !isNaN(distanciaManual) && parseFloat(distanciaManual) > 0) {
        distanciaReal = parseFloat(distanciaManual);
      }
    }

    const observacoes = prompt("📋 Observações sobre a rota (opcional):") || "";

    if (!confirm("✅ Finalizar esta rota?\n\nEsta ação não pode ser desfeita.")) {
      return;
    }

    try {
      setProcessandoFinalizacao(true);
      
      const payload = {
        observacoes: observacoes.trim()
      };
      
      if (kmFinal && !isNaN(kmFinal) && parseFloat(kmFinal) > 0) {
        payload.km_final = parseFloat(kmFinal);
      }
      
      if (distanciaReal) {
        payload.distancia_real = distanciaReal;
      }
      
      await api.post(`/rotas-entrega/${rotaId}/fechar`, payload);
      
      alert("✅ Rota finalizada com sucesso!");
      window.location.reload();
    } catch (err) {
      console.error("Erro ao finalizar rota:", err);
      const mensagem = err.response?.data?.detail || "Erro ao finalizar rota";
      alert("❌ " + mensagem);
    } finally {
      setProcessandoFinalizacao(false);
    }
  }

  const handleDragStart = (e, index) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragOver = (e, index) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === index) return;

    const newParadas = [...paradasOrdenadas];
    const draggedItem = newParadas[draggedIndex];
    newParadas.splice(draggedIndex, 1);
    newParadas.splice(index, 0, draggedItem);
    
    setParadasOrdenadas(newParadas);
    setDraggedIndex(index);
  };

  const handleDragEnd = () => {
    if (draggedIndex !== null) {
      onReordenar(rota.id, paradasOrdenadas);
    }
    setDraggedIndex(null);
  };

  return (
    <div
      style={{
        border: "1px solid #ddd",
        borderRadius: 8,
        padding: 15,
        backgroundColor: "#fff",
      }}
    >
      {/* Cabeçalho do Card - Clicável */}
      <div
        style={{
          cursor: "pointer",
          transition: "all 0.2s",
        }}
        onClick={onToggleExpand}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div style={{ flex: 1 }}>
            <h3 style={{ margin: 0, marginBottom: 10 }}>
              🚚 {rota.numero || `Rota #${rota.id}`}
              {expandida ? " 🔽" : " ▶️"}
            </h3>
            
            <div style={{ display: "flex", flexDirection: "column", gap: 5, color: "#555" }}>
              <div>
                <strong>Entregador:</strong> {rota.entregador?.nome || "Não informado"}
              </div>
              
              <div>
                <strong>Paradas:</strong> {rota.paradas?.length || 0} entrega(s)
              </div>
              
              {rota.distancia_prevista && (
                <div>
                  <strong>Distância Prevista:</strong> {rota.distancia_prevista} km
                </div>
              )}
              
              {tempoEstimado && (
                <div>
                  <strong>Tempo Estimado:</strong> {formatarTempo(tempoEstimado)}
                </div>
              )}
              
              {/* KM Inicial - Mostra quando a rota foi iniciada */}
              {rota.km_inicial && (
                <div>
                  <strong>🏁 KM Inicial:</strong> {parseFloat(rota.km_inicial).toFixed(1)} km
                </div>
              )}
              
              {/* KM Final - Mostra quando a rota foi finalizada */}
              {rota.km_final && (
                <div>
                  <strong>🏁 KM Final:</strong> {parseFloat(rota.km_final).toFixed(1)} km
                </div>
              )}
              
              {/* Total de KM Rodados - Calcula se tiver inicial e final */}
              {rota.km_inicial && rota.km_final && (
                <div style={{ color: "#007BFF", fontWeight: "600" }}>
                  <strong>📏 Total Rodado:</strong> {(parseFloat(rota.km_final) - parseFloat(rota.km_inicial)).toFixed(1)} km
                  
                  {/* Comparação com Projetado - Se existir distância prevista */}
                  {rota.distancia_prevista && (() => {
                    const realizado = parseFloat(rota.km_final) - parseFloat(rota.km_inicial);
                    const projetado = parseFloat(rota.distancia_prevista);
                    const diferenca = realizado - projetado;
                    const percentual = ((diferenca / projetado) * 100).toFixed(1);
                    
                    return (
                      <span style={{ 
                        marginLeft: 10,
                        color: diferenca > 0 ? "#DC3545" : "#28A745",
                        fontSize: 13
                      }}>
                        ({diferenca > 0 ? "+" : ""}{diferenca.toFixed(1)} km / {percentual > 0 ? "+" : ""}{percentual}% vs projetado)
                      </span>
                    );
                  })()}
                </div>
              )}
              
              <div>
                <strong>Criada em:</strong>{" "}
                {new Date(rota.created_at).toLocaleString("pt-BR")}
              </div>
              
              {rota.data_conclusao && (
                <div>
                  <strong>Concluída em:</strong>{" "}
                  {new Date(rota.data_conclusao).toLocaleString("pt-BR")}
                </div>
              )}
            </div>
          </div>

          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            {/* Botão Iniciar Rota - visível apenas se status for pendente */}
            {rota.status === "pendente" && (
              <button
                onClick={(e) => {
                  e.stopPropagation(); // Não expandir/colapsar ao clicar no botão
                  onIniciarRota(rota.id);
                }}
                style={{
                  padding: "8px 16px",
                  backgroundColor: "#28A745",
                  color: "#fff",
                  border: "none",
                  borderRadius: 6,
                  cursor: "pointer",
                  fontWeight: "bold",
                  fontSize: 14,
                  display: "flex",
                  alignItems: "center",
                  gap: 5
                }}
              >
                🚀 Iniciar Rota
              </button>
            )}
            
            {/* Botão Finalizar Rota - visível quando rota em_rota e todas entregas concluídas */}
            {(rota.status === "em_rota" || rota.status === "em_andamento") && todasEntregue && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  finalizarRota(rota.id, rota.km_inicial);
                }}
                disabled={processandoFinalizacao}
                style={{
                  padding: "8px 16px",
                  backgroundColor: processandoFinalizacao ? "#ccc" : "#007BFF",
                  color: "#fff",
                  border: "none",
                  borderRadius: 6,
                  cursor: processandoFinalizacao ? "not-allowed" : "pointer",
                  fontWeight: "bold",
                  fontSize: 14,
                  display: "flex",
                  alignItems: "center",
                  gap: 5
                }}
              >
                {processandoFinalizacao ? "⏳ Processando..." : "✅ Finalizar Rota"}
              </button>
            )}
            
            {/* Botão Reverter Início - visível quando rota em_rota mas nenhuma entrega foi feita */}
            {(rota.status === "em_rota" || rota.status === "em_andamento") && paradasPendentes === paradasOrdenadas.length && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onReverterInicio(rota.id);
                }}
                style={{
                  padding: "8px 16px",
                  backgroundColor: "#FFC107",
                  color: "#000",
                  border: "none",
                  borderRadius: 6,
                  cursor: "pointer",
                  fontWeight: "bold",
                  fontSize: 14,
                  display: "flex",
                  alignItems: "center",
                  gap: 5
                }}
              >
                ↩️ Reverter Início
              </button>
            )}
            
            {/* Botão Excluir Rota - visível para rotas pendentes ou em_rota */}
            {(rota.status === "pendente" || rota.status === "em_rota" || rota.status === "em_andamento") && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onExcluirRota(rota.id);
                }}
                style={{
                  padding: "8px 16px",
                  backgroundColor: "#DC3545",
                  color: "#fff",
                  border: "none",
                  borderRadius: 6,
                  cursor: "pointer",
                  fontWeight: "bold",
                  fontSize: 14,
                  display: "flex",
                  alignItems: "center",
                  gap: 5
                }}
              >
                🗑️ Excluir
              </button>
            )}
            
            <div
              style={{
                padding: "5px 15px",
                borderRadius: 20,
                backgroundColor: getStatusColor(rota.status),
                color: "#fff",
                fontWeight: "bold",
                fontSize: 14,
                whiteSpace: "nowrap",
              }}
            >
              {getStatusLabel(rota.status)}
            </div>
          </div>
        </div>

        {rota.observacoes && (
          <div
            style={{
              marginTop: 10,
              padding: 10,
              backgroundColor: "#f8f9fa",
              borderRadius: 5,
              fontSize: 14,
              color: "#666",
            }}
          >
            <strong>Observações:</strong> {rota.observacoes}
          </div>
        )}
      </div>

      {/* Paradas Expandidas */}
      {expandida && paradasOrdenadas.length > 0 && (
        <div style={{ marginTop: 20, borderTop: "2px solid #eee", paddingTop: 15 }}>
          <h4 style={{ marginBottom: 15 }}>📍 Paradas da Rota (arraste para reordenar)</h4>
          
          {paradasOrdenadas.map((parada, index) => (
            <div key={parada.id}>
              <div
                draggable
                onDragStart={(e) => handleDragStart(e, index)}
                onDragOver={(e) => handleDragOver(e, index)}
                onDragEnd={handleDragEnd}
                style={{
                  padding: 12,
                  marginBottom: 10,
                  border: "1px solid #ddd",
                  borderRadius: 6,
                  backgroundColor: draggedIndex === index ? "#f0f8ff" : "#fafafa",
                  cursor: "move",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", marginBottom: 5 }}>
                    <span style={{ 
                      fontWeight: "bold", 
                      marginRight: 10,
                      fontSize: 18,
                      color: "#007BFF"
                    }}>
                      {parada.ordem}º
                    </span>
                    <span style={{ color: "#666", fontSize: 14 }}>
                      Venda #{parada.venda_id}
                    </span>
                    {parada.status && (
                      <span style={{
                        marginLeft: 10,
                        padding: "2px 8px",
                        borderRadius: 12,
                        fontSize: 12,
                        backgroundColor: 
                          parada.status === "entregue" ? "#d4edda" :
                          parada.status === "tentativa" ? "#fff3cd" : "#e2e3e5",
                        color: 
                          parada.status === "entregue" ? "#155724" :
                          parada.status === "tentativa" ? "#856404" : "#383d41",
                      }}>
                        {parada.status === "entregue" ? "✓ Entregue" :
                         parada.status === "tentativa" ? "⚠ Tentativa" : "Pendente"}
                      </span>
                    )}
                  </div>
                  
                  {/* Cliente e Informações em layout compacto */}
                  <div style={{ fontSize: 13, color: "#333", lineHeight: 1.6 }}>
                    {/* Nome e Telefones */}
                    {parada.cliente_nome && (
                      <div style={{ marginBottom: 4 }}>
                        <strong style={{ color: "#1565C0" }}>👤 {parada.cliente_nome}</strong>
                        {parada.cliente_telefone && (
                          <span style={{ marginLeft: 12, color: "#555" }}>
                            📞 {parada.cliente_telefone}
                          </span>
                        )}
                        {parada.cliente_celular && (
                          <span style={{ marginLeft: 12, color: "#555" }}>
                            📱 {parada.cliente_celular}
                          </span>
                        )}
                      </div>
                    )}
                    
                    {/* Endereço */}
                    <div style={{ color: "#555" }}>
                      📍 {parada.endereco}
                      {parada.distancia_acumulada && (
                        <span style={{ marginLeft: 12, color: "#777" }}>
                          • Dist: {parada.distancia_acumulada} km
                        </span>
                      )}
                      {parada.tempo_acumulado && (
                        <span style={{ marginLeft: 12, color: "#777" }}>
                          • Tempo aprox: {formatarTempo(parada.tempo_acumulado)}
                        </span>
                      )}
                    </div>
                  </div>
                  
                  {parada.data_entrega && (
                    <div style={{ color: "#28a745", fontSize: 12, marginTop: 3 }}>
                      ✓ Entregue em: {new Date(parada.data_entrega).toLocaleString("pt-BR")}
                    </div>
                  )}
                  
                  {/* Observações da parada */}
                  {parada.observacoes && (
                    <div style={{ 
                      marginTop: 6,
                      padding: 6,
                      backgroundColor: "#fff3cd",
                      borderRadius: 4,
                      fontSize: 12,
                      color: "#856404",
                      border: "1px solid #ffc107"
                    }}>
                      📋 {parada.observacoes}
                    </div>
                  )}
                </div>

                {/* Botões de Ação */}
                <div style={{ display: "flex", flexDirection: "column", gap: 6, alignItems: "flex-end" }}>
                  {/* Botão Entregue - só aparece se status != entregue */}
                  {parada.status !== "entregue" && rota.status === "em_rota" && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        marcarComoEntregue(parada.id, rota.id);
                      }}
                      disabled={processandoEntrega === parada.id}
                      style={{
                        padding: "8px 12px",
                        backgroundColor: processandoEntrega === parada.id ? "#ccc" : "#28A745",
                        color: "#fff",
                        border: "none",
                        borderRadius: 6,
                        cursor: processandoEntrega === parada.id ? "not-allowed" : "pointer",
                        fontWeight: "600",
                        fontSize: 12,
                        whiteSpace: "nowrap",
                        width: "130px",
                        textAlign: "center",
                      }}
                    >
                      {processandoEntrega === parada.id ? "⏳..." : "✅ Entregue"}
                    </button>
                  )}
                  
                  {/* Botão Não Entregue - só aparece para rotas em andamento */}
                  {parada.status !== "entregue" && (rota.status === "em_rota" || rota.status === "em_andamento") && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        marcarNaoEntregue(parada.id, rota.id, parada.venda_id);
                      }}
                      disabled={processandoNaoEntregue === parada.id}
                      style={{
                        padding: "8px 12px",
                        backgroundColor: processandoNaoEntregue === parada.id ? "#ccc" : "#FFC107",
                        color: "#000",
                        border: "none",
                        borderRadius: 6,
                        cursor: processandoNaoEntregue === parada.id ? "not-allowed" : "pointer",
                        fontWeight: "600",
                        fontSize: 12,
                        whiteSpace: "nowrap",
                        width: "130px",
                        textAlign: "center",
                      }}
                    >
                      {processandoNaoEntregue === parada.id ? "⏳..." : "⚠️ Falta Entregar"}
                    </button>
                  )}
                  
                  {/* Botão Observação */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      adicionarObservacao(parada.id, rota.id);
                    }}
                    style={{
                      padding: "8px 12px",
                      backgroundColor: "#6C757D",
                      color: "#fff",
                      border: "none",
                      borderRadius: 6,
                      cursor: "pointer",
                      fontSize: 12,
                      fontWeight: "600",
                      whiteSpace: "nowrap",
                      width: "130px",
                      textAlign: "center",
                    }}
                  >
                    📝 Observação
                  </button>
                  
                  {/* Botão Detalhes */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (paradaDetalhesAberta === parada.id) {
                        fecharDetalhes();
                      } else {
                        carregarDetalhesVenda(parada.id, parada.venda_id);
                      }
                    }}
                    style={{ 
                      padding: "8px 12px",
                      backgroundColor: "#17A2B8",
                      color: "#fff",
                      border: "none",
                      borderRadius: 6,
                      cursor: "pointer",
                      fontSize: 12,
                      fontWeight: "600",
                      whiteSpace: "nowrap",
                      width: "130px",
                      textAlign: "center",
                    }}
                  >
                    📄 Detalhes
                  </button>
                </div>
              </div>

              {/* Modal de Detalhes da Venda - Logo abaixo da parada */}
              {paradaDetalhesAberta === parada.id && (
                <div style={{
                  marginTop: 0,
                  marginBottom: 15,
                  padding: 15,
                  backgroundColor: "#f8f9fa",
                  borderRadius: 8,
                  border: "2px solid #007BFF",
                  boxShadow: "0 2px 8px rgba(0,123,255,0.2)"
                }}>
                  {loadingDetalhes ? (
                    <div style={{ textAlign: "center", color: "#666", padding: 20 }}>
                      Carregando detalhes da venda...
                    </div>
                  ) : vendaDetalhes ? (
                    <>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 15, borderBottom: "2px solid #007BFF", paddingBottom: 10 }}>
                        <h4 style={{ margin: 0, color: "#007BFF" }}>
                          🧾 Detalhes da Venda #{vendaDetalhes.id}
                        </h4>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            fecharDetalhes();
                          }}
                          style={{
                            background: "#dc3545",
                            color: "#fff",
                            border: "none",
                            borderRadius: 4,
                            padding: "6px 12px",
                            cursor: "pointer",
                            fontWeight: "bold",
                            fontSize: 13
                          }}
                        >
                          ✕ Fechar
                        </button>
                      </div>
                      
                      {/* Informações do Cliente */}
                      <div style={{
                        backgroundColor: "#e7f3ff",
                        padding: 12,
                        borderRadius: 6,
                        marginBottom: 15,
                        border: "1px solid #007BFF"
                      }}>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, fontSize: 14 }}>
                          <div>
                            <strong>👤 Cliente:</strong> {vendaDetalhes.cliente?.nome || vendaDetalhes.nome_cliente || "N/A"}
                          </div>
                          <div>
                            <strong>📅 Data:</strong> {vendaDetalhes.data_venda ? new Date(vendaDetalhes.data_venda).toLocaleString("pt-BR") : "N/A"}
                          </div>
                          
                          {vendaDetalhes.cliente?.telefone && (
                            <div>
                              <strong>📞 Telefone:</strong> {vendaDetalhes.cliente.telefone}
                            </div>
                          )}
                          {vendaDetalhes.cliente?.celular && (
                            <div>
                              <strong>📱 Celular:</strong> {vendaDetalhes.cliente.celular}
                            </div>
                          )}
                          {vendaDetalhes.cliente?.email && (
                            <div style={{ gridColumn: "1 / -1" }}>
                              <strong>📧 Email:</strong> {vendaDetalhes.cliente.email}
                            </div>
                          )}
                        </div>
                      </div>
                      
                      {/* Informações Financeiras */}
                      <div style={{ 
                        display: "grid", 
                        gridTemplateColumns: "1fr 1fr 1fr", 
                        gap: 10, 
                        fontSize: 14,
                        marginBottom: 15 
                      }}>
                        <div style={{ padding: 10, backgroundColor: "#d4edda", borderRadius: 4, border: "1px solid #28a745" }}>
                          <div style={{ fontSize: 11, color: "#155724", marginBottom: 3 }}>VALOR TOTAL</div>
                          <div style={{ fontWeight: "bold", fontSize: 16, color: "#155724" }}>
                            R$ {parseFloat(vendaDetalhes.valor_total || vendaDetalhes.total || 0).toFixed(2)}
                          </div>
                        </div>
                        <div style={{ padding: 10, backgroundColor: "#fff", borderRadius: 4, border: "1px solid #ddd" }}>
                          <div style={{ fontSize: 11, color: "#666", marginBottom: 3 }}>PAGAMENTO</div>
                          <div style={{ fontWeight: "bold", fontSize: 14 }}>
                            {vendaDetalhes.forma_pagamento || "N/A"}
                          </div>
                        </div>
                        <div style={{ padding: 10, backgroundColor: "#fff", borderRadius: 4, border: "1px solid #ddd" }}>
                          <div style={{ fontSize: 11, color: "#666", marginBottom: 3 }}>STATUS</div>
                          <div style={{ fontWeight: "bold", fontSize: 14 }}>
                            {vendaDetalhes.status_pagamento || "N/A"}
                          </div>
                        </div>
                      </div>

                      {vendaDetalhes.endereco_entrega && (
                        <div style={{ 
                          padding: 12, 
                          backgroundColor: "#e3f2fd", 
                          borderRadius: 6, 
                          marginBottom: 15,
                          border: "1px solid #2196F3"
                        }}>
                          <div style={{ fontWeight: "bold", marginBottom: 5, color: "#1976D2" }}>
                            📍 Endereço de Entrega
                          </div>
                          <div style={{ color: "#424242", fontSize: 14 }}>
                            {vendaDetalhes.endereco_entrega}
                          </div>
                        </div>
                      )}
                      
                      {vendaDetalhes.observacoes && (
                        <div style={{ 
                          padding: 12, 
                          backgroundColor: "#fff3cd", 
                          borderRadius: 6, 
                          marginBottom: 15,
                          border: "1px solid #ffc107"
                        }}>
                          <div style={{ fontWeight: "bold", marginBottom: 5, color: "#f57c00" }}>
                            💬 Observações
                          </div>
                          <div style={{ color: "#424242", fontSize: 14 }}>
                            {vendaDetalhes.observacoes}
                          </div>
                        </div>
                      )}

                      {vendaDetalhes.itens && vendaDetalhes.itens.length > 0 && (
                        <div>
                          <div style={{ 
                            fontWeight: "bold", 
                            fontSize: 15, 
                            marginBottom: 10,
                            color: "#424242"
                          }}>
                            🛒 Itens da Venda ({vendaDetalhes.itens.length})
                          </div>
                          <div style={{ 
                            backgroundColor: "#fff", 
                            borderRadius: 6, 
                            border: "1px solid #ddd",
                            overflow: "hidden",
                            boxShadow: "0 1px 3px rgba(0,0,0,0.1)"
                          }}>
                            {vendaDetalhes.itens.map((item, idx) => (
                              <div 
                                key={idx} 
                                style={{ 
                                  padding: 12,
                                  borderBottom: idx < vendaDetalhes.itens.length - 1 ? "1px solid #eee" : "none",
                                  display: "flex",
                                  justifyContent: "space-between",
                                  alignItems: "center",
                                  backgroundColor: idx % 2 === 0 ? "#fafafa" : "#fff"
                                }}
                              >
                                <div style={{ flex: 1 }}>
                                  <div style={{ fontWeight: "600", marginBottom: 3, color: "#333" }}>
                                    {item.produto?.nome || item.servico?.nome || item.produto_nome || item.servico_descricao || "Item"}
                                  </div>
                                  {(item.produto?.codigo || item.produto_codigo) && (
                                    <div style={{ fontSize: 12, color: "#999" }}>
                                      Cód: {item.produto?.codigo || item.produto_codigo}
                                    </div>
                                  )}
                                </div>
                                <div style={{ textAlign: "right", minWidth: 120 }}>
                                  <div style={{ color: "#666", fontSize: 13, marginBottom: 2 }}>
                                    {item.quantidade} × R$ {parseFloat(item.valor_unitario || item.preco_unitario || 0).toFixed(2)}
                                  </div>
                                  <div style={{ fontSize: 15, color: "#28a745", fontWeight: "bold" }}>
                                    R$ {parseFloat((item.quantidade || 0) * (item.valor_unitario || item.preco_unitario || 0)).toFixed(2)}
                                  </div>
                                </div>
                              </div>
                            ))}
                            
                            {/* Total geral */}
                            <div style={{
                              padding: 14,
                              backgroundColor: "#1976D2",
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center",
                              color: "#fff"
                            }}>
                              <span style={{ fontWeight: "bold", fontSize: 16 }}>TOTAL DA VENDA</span>
                              <span style={{ fontWeight: "bold", fontSize: 18 }}>
                                R$ {parseFloat(vendaDetalhes.valor_total || vendaDetalhes.total || 0).toFixed(2)}
                              </span>
                            </div>
                          </div>
                        </div>
                      )}
                    </>
                  ) : null}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
