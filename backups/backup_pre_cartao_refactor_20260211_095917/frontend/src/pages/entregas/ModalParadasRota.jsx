import { useEffect, useState } from "react";
import { api } from "../../services/api";
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy, useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

/**
 * ETAPA 9.4+ - Gera link do Google Maps com rota otimizada e ponto final configurável
 */
function gerarLinkGoogleMaps(origem, paradas, pontoFinal = null, retornaOrigem = true) {
  if (!paradas || paradas.length === 0) return null;
  
  // Waypoints: todas as paradas exceto a última
  const waypoints = paradas
    .slice(0, -1)
    .map(p => encodeURIComponent(p.endereco))
    .join("|");
  
  // Destino final: depende da configuração
  let destino;
  if (retornaOrigem) {
    // Volta à origem: destino = origem, última parada vira waypoint
    destino = encodeURIComponent(origem);
    const todasParadas = paradas.map(p => encodeURIComponent(p.endereco)).join("|");
    return `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(origem)}&destination=${destino}&waypoints=${todasParadas}&travelmode=driving`;
  } else if (pontoFinal) {
    // Ponto final customizado
    destino = encodeURIComponent(pontoFinal);
  } else {
    // Finaliza na última entrega
    destino = encodeURIComponent(paradas[paradas.length - 1].endereco);
  }
  
  const origemEncoded = encodeURIComponent(origem);
  
  if (waypoints) {
    return `https://www.google.com/maps/dir/?api=1&origin=${origemEncoded}&destination=${destino}&waypoints=${waypoints}&travelmode=driving`;
  } else {
    return `https://www.google.com/maps/dir/?api=1&origin=${origemEncoded}&destination=${destino}&travelmode=driving`;
  }
}

/**
 * ETAPA 9.3/9.4 - Componente de Parada Ordenável (Drag & Drop)
 */
function ParadaItem({ parada, index, onMarcarEntregue, onMarcarTentativa, rotaEmAndamento }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: parada.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };
  
  // Badge de status
  const getStatusBadge = (status) => {
    const badges = {
      pendente: { text: "Pendente", color: "#ffa500", icon: "⏳" },
      entregue: { text: "Entregue", color: "#4caf50", icon: "✅" },
      tentativa: { text: "Tentativa", color: "#f44336", icon: "🔁" },
    };
    const badge = badges[status] || badges.pendente;
    return (
      <span style={{
        padding: "4px 8px",
        borderRadius: 4,
        fontSize: 12,
        fontWeight: "bold",
        color: "#fff",
        backgroundColor: badge.color,
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
      }}>
        {badge.icon} {badge.text}
      </span>
    );
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="parada-item"
      {...attributes}
      {...listeners}
    >
      <div className="parada-ordem">
        <span className="ordem-numero">{index + 1}</span>
        {!rotaEmAndamento && <span className="drag-handle">☰</span>}
      </div>
      
      <div className="parada-info">
        <div className="parada-header">
          <strong>Venda #{parada.venda_id}</strong>
          {getStatusBadge(parada.status)}
        </div>
        
        <div className="parada-endereco">{parada.endereco}</div>
        
        <div className="parada-metricas">
          {parada.distancia_acumulada && (
            <span className="metrica">
              📍 {parseFloat(parada.distancia_acumulada).toFixed(2)} km acumulados
            </span>
          )}
          {parada.tempo_acumulado && (
            <span className="metrica">
              ⏱️ {Math.round(parada.tempo_acumulado / 60)} min acumulados
            </span>
          )}
          {parada.data_entrega && (
            <span className="metrica">
              ✅ Entregue: {new Date(parada.data_entrega).toLocaleString('pt-BR')}
            </span>
          )}
        </div>
        
        {/* ETAPA 9.4: Botões de controle */}
        {rotaEmAndamento && parada.status === "pendente" && (
          <div className="parada-acoes" style={{ marginTop: 12, display: "flex", gap: 8 }}>
            <button
              className="btn-success btn-small"
              onClick={(e) => {
                e.stopPropagation();
                onMarcarEntregue(parada.id);
              }}
            >
              ✅ Entregue
            </button>
            <button
              className="btn-warning btn-small"
              onClick={(e) => {
                e.stopPropagation();
                onMarcarTentativa(parada.id);
              }}
            >
              🔁 Tentativa
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * ETAPA 9.3/9.4 - Modal de Gestão de Paradas da Rota
 */
export default function ModalParadasRota({ rota, onClose, onSave, pontoInicial }) {
  const [loading, setLoading] = useState(true);
  const [paradas, setParadas] = useState([]);
  const [saving, setSaving] = useState(false);
  const [ordenAlterada, setOrdemAlterada] = useState(false);
  const [iniciandoRota, setIniciandoRota] = useState(false);
  const [mostrarConfigPontoFinal, setMostrarConfigPontoFinal] = useState(false);
  const [pontoFinalConfig, setPontoFinalConfig] = useState({
    retorna_origem: rota.retorna_origem !== false, // Por padrão true
    ponto_final: rota.ponto_final_rota || "",
  });

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );
  
  const rotaEmAndamento = rota.status === "em_rota";
  const rotaConcluida = rota.status === "concluida";

  useEffect(() => {
    carregarParadas();
  }, [rota.id]);

  async function carregarParadas() {
    setLoading(true);
    try {
      const res = await api.get(`/rotas-entrega/${rota.id}/paradas`);
      setParadas(res.data || []);
    } catch (err) {
      console.error("Erro ao carregar paradas:", err);
      alert("Erro ao carregar paradas da rota");
    } finally {
      setLoading(false);
    }
  }

  function handleDragEnd(event) {
    const { active, over } = event;

    if (active.id !== over.id) {
      setParadas((items) => {
        const oldIndex = items.findIndex((item) => item.id === active.id);
        const newIndex = items.findIndex((item) => item.id === over.id);
        return arrayMove(items, oldIndex, newIndex);
      });
      setOrdemAlterada(true);
    }
  }

  async function salvarNovaOrdem() {
    if (!ordenAlterada) {
      onClose();
      return;
    }

    setSaving(true);
    try {
      const novaOrdem = paradas.map((p) => p.id);
      await api.put(`/rotas-entrega/${rota.id}/paradas/reordenar`, novaOrdem);
      
      alert("Ordem das paradas atualizada com sucesso!");
      if (onSave) onSave();
      onClose();
    } catch (err) {
      console.error("Erro ao salvar ordem:", err);
      alert(err.response?.data?.detail || "Erro ao salvar nova ordem");
    } finally {
      setSaving(false);
    }
  }
  
  // ETAPA 9.4: Iniciar navegação
  async function iniciarNavegacao() {
    if (!pontoInicial) {
      alert("Configure o ponto inicial da rota em Configurações antes de iniciar.");
      return;
    }
    
    if (!confirm("Deseja iniciar a navegação desta rota?")) return;
    
    setIniciandoRota(true);
    try {
      // Atualizar configuração de ponto final no backend (se alterado)
      if (mostrarConfigPontoFinal) {
        await api.put(`/rotas-entrega/${rota.id}`, {
          retorna_origem: pontoFinalConfig.retorna_origem,
          ponto_final_rota: pontoFinalConfig.retorna_origem ? pontoInicial : (pontoFinalConfig.ponto_final || paradas[paradas.length - 1]?.endereco),
        });
      }
      
      // Marcar rota como iniciada no backend
      await api.post(`/rotas-entrega/${rota.id}/iniciar`);
      
      // Gerar link do Google Maps com ponto final configurável
      const linkMaps = gerarLinkGoogleMaps(
        pontoInicial, 
        paradas,
        pontoFinalConfig.ponto_final,
        pontoFinalConfig.retorna_origem
      );
      
      if (linkMaps) {
        // Abrir Google Maps
        window.open(linkMaps, "_blank");
        
        alert("Rota iniciada! Google Maps foi aberto em uma nova aba.");
        if (onSave) onSave();
        onClose();
      } else {
        alert("Erro ao gerar link do Google Maps");
      }
    } catch (err) {
      console.error("Erro ao iniciar rota:", err);
      alert(err.response?.data?.detail || "Erro ao iniciar rota");
    } finally {
      setIniciandoRota(false);
    }
  }
  
  // ETAPA 9.4: Marcar parada como entregue
  async function marcarEntregue(paradaId) {
    if (!confirm("Confirma que a entrega foi realizada?")) return;
    
    try {
      await api.post(`/rotas-entrega/${rota.id}/paradas/${paradaId}/marcar-entregue`, {}, {
        params: { tentativa: false }
      });
      
      // Recarregar paradas
      await carregarParadas();
      alert("Parada marcada como entregue!");
    } catch (err) {
      console.error("Erro:", err);
      alert(err.response?.data?.detail || "Erro ao marcar entrega");
    }
  }
  
  // ETAPA 9.4: Marcar tentativa (cliente ausente)
  async function marcarTentativa(paradaId) {
    if (!confirm("Cliente ausente? Registrar tentativa?")) return;
    
    try {
      await api.post(`/rotas-entrega/${rota.id}/paradas/${paradaId}/marcar-entregue`, {}, {
        params: { tentativa: true }
      });
      
      // Recarregar paradas
      await carregarParadas();
      alert("Tentativa registrada. Continue para a próxima parada.");
    } catch (err) {
      console.error("Erro:", err);
      alert(err.response?.data?.detail || "Erro ao registrar tentativa");
    }
  }

  if (loading) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content" onClick={(e) => e.stopPropagation()}>
          <h2>Carregando paradas...</h2>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-paradas" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>🗺️ Sequência de Entregas - {rota.numero}</h2>
          <button className="btn-close" onClick={onClose}>✕</button>
        </div>

        <div className="modal-body">
          {paradas.length === 0 ? (
            <div className="empty-state">
              <p>Nenhuma parada cadastrada nesta rota</p>
            </div>
          ) : (
            <>
              <div className="info-box">
                {rota.status === "pendente" && (
                  <p><strong>💡 Dica:</strong> Arraste as paradas para reorganizar a ordem de entrega</p>
                )}
                {rotaEmAndamento && (
                  <p><strong>🚗 Rota em andamento:</strong> Marque cada parada como entregue ou tentativa</p>
                )}
                {ordenAlterada && (
                  <p className="ordem-alterada">⚠️ Ordem alterada! Clique em "Salvar" para confirmar.</p>
                )}
              </div>

              <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragEnd={handleDragEnd}
              >
                <SortableContext
                  items={paradas.map((p) => p.id)}
                  strategy={verticalListSortingStrategy}
                >
                  <div className="paradas-list">
                    {paradas.map((parada, index) => (
                      <ParadaItem 
                        key={parada.id} 
                        parada={parada} 
                        index={index}
                        onMarcarEntregue={marcarEntregue}
                        onMarcarTentativa={marcarTentativa}
                        rotaEmAndamento={rotaEmAndamento}
                      />
                    ))}
                  </div>
                </SortableContext>
              </DndContext>

              <div className="resumo-rota">
                <h3>Resumo da Rota</h3>
                <div className="resumo-grid">
                  <div className="resumo-item">
                    <span className="label">Total de Paradas:</span>
                    <span className="value">{paradas.length}</span>
                  </div>
                  {paradas[paradas.length - 1]?.distancia_acumulada && (
                    <div className="resumo-item">
                      <span className="label">Distância Total:</span>
                      <span className="value">
                        {parseFloat(paradas[paradas.length - 1].distancia_acumulada).toFixed(2)} km
                      </span>
                    </div>
                  )}
                  {paradas[paradas.length - 1]?.tempo_acumulado && (
                    <div className="resumo-item">
                      <span className="label">Tempo Estimado:</span>
                      <span className="value">
                        {Math.round(paradas[paradas.length - 1].tempo_acumulado / 60)} minutos
                      </span>
                    </div>
                  )}
                </div>
                
                {/* Configuração de Ponto Final */}
                {rota.status === "pendente" && (
                  <div style={{ marginTop: 20, padding: 15, backgroundColor: "#f5f5f5", borderRadius: 8 }}>
                    <h4 style={{ marginBottom: 10, fontSize: 14, display: "flex", alignItems: "center", gap: 8 }}>
                      📍 Ponto Final da Rota
                      <button
                        type="button"
                        onClick={() => setMostrarConfigPontoFinal(!mostrarConfigPontoFinal)}
                        style={{
                          background: "none",
                          border: "none",
                          cursor: "pointer",
                          fontSize: 12,
                          color: "#007bff",
                          marginLeft: "auto",
                        }}
                      >
                        {mostrarConfigPontoFinal ? "Ocultar" : "Configurar"}
                      </button>
                    </h4>
                    
                    {mostrarConfigPontoFinal ? (
                      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                        <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
                          <input
                            type="radio"
                            name="pontoFinal"
                            checked={pontoFinalConfig.retorna_origem}
                            onChange={() => setPontoFinalConfig({ ...pontoFinalConfig, retorna_origem: true })}
                          />
                          Retornar à origem (loja)
                        </label>
                        
                        <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
                          <input
                            type="radio"
                            name="pontoFinal"
                            checked={!pontoFinalConfig.retorna_origem}
                            onChange={() => setPontoFinalConfig({ ...pontoFinalConfig, retorna_origem: false })}
                          />
                          Finalizar na última entrega
                        </label>
                        
                        {!pontoFinalConfig.retorna_origem && (
                          <input
                            type="text"
                            placeholder="Ou digite outro endereço final..."
                            value={pontoFinalConfig.ponto_final}
                            onChange={(e) => setPontoFinalConfig({ ...pontoFinalConfig, ponto_final: e.target.value })}
                            style={{
                              padding: 8,
                              border: "1px solid #ddd",
                              borderRadius: 4,
                              fontSize: 12,
                              marginTop: 5,
                            }}
                          />
                        )}
                        
                        <p style={{ fontSize: 11, color: "#666", margin: 0 }}>
                          {pontoFinalConfig.retorna_origem 
                            ? "🔄 Entregador voltará ao ponto de origem após todas as entregas"
                            : "🏁 Entregador finalizará no local da última entrega"
                          }
                        </p>
                      </div>
                    ) : (
                      <p style={{ fontSize: 12, color: "#666", margin: 0 }}>
                        {rota.retorna_origem !== false
                          ? "🔄 Volta à origem (padrão)"
                          : "🏁 Finaliza na última entrega"
                        }
                      </p>
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose} disabled={saving || iniciandoRota}>
            Cancelar
          </button>
          
          {/* ETAPA 9.4: Botão Iniciar Navegação (apenas quando pendente) */}
          {rota.status === "pendente" && paradas.length > 0 && (
            <button
              className="btn-success"
              onClick={iniciarNavegacao}
              disabled={saving || iniciandoRota || ordenAlterada}
              style={{ marginLeft: "auto" }}
            >
              {iniciandoRota ? "Iniciando..." : "🚀 Iniciar Navegação"}
            </button>
          )}
          
          {/* Botão salvar ordem (apenas quando alterada) */}
          {ordenAlterada && (
            <button
              className="btn-primary"
              onClick={salvarNovaOrdem}
              disabled={saving || iniciandoRota}
            >
              {saving ? "Salvando..." : "Salvar Ordem"}
            </button>
          )}
          
          {/* Botão fechar padrão (quando nada alterado e não pendente) */}
          {!ordenAlterada && rota.status !== "pendente" && (
            <button
              className="btn-primary"
              onClick={onClose}
              disabled={saving}
            >
              Fechar
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
