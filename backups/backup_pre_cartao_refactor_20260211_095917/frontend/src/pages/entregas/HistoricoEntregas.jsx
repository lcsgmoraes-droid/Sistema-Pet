import { useEffect, useState } from "react";
import api from "../../api";

export default function HistoricoEntregas() {
  const [rotas, setRotas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [rotaExpandida, setRotaExpandida] = useState(null);

  useEffect(() => {
    carregarHistorico();
  }, []);

  async function carregarHistorico() {
    try {
      setLoading(true);
      // Buscar apenas rotas concluídas
      const response = await api.get('/rotas-entrega/?status=concluida');
      setRotas(response.data);
    } catch (err) {
      console.error("Erro ao carregar histórico:", err);
      alert("Erro ao carregar histórico de entregas");
    } finally {
      setLoading(false);
    }
  }

  function toggleRotaExpandida(rotaId) {
    setRotaExpandida(rotaExpandida === rotaId ? null : rotaId);
  }

  function formatarTempo(segundos) {
    if (!segundos) return "N/A";
    const minutos = Math.floor(segundos / 60);
    const horas = Math.floor(minutos / 60);
    const mins = minutos % 60;
    if (horas > 0) {
      return `${horas}h${mins}min`;
    }
    return `${mins}min`;
  }

  if (loading) {
    return (
      <div className="page">
        <h1>📜 Histórico de Entregas</h1>
        <p>Carregando histórico...</p>
      </div>
    );
  }

  return (
    <div className="page">
      <h1>📜 Histórico de Entregas</h1>
      <p style={{ color: "#666", marginBottom: 20 }}>
        Rotas finalizadas e conferidas
      </p>

      <div style={{ marginBottom: 20, display: "flex", gap: 10, alignItems: "center" }}>
        <button
          onClick={carregarHistorico}
          className="btn-secondary"
          style={{ marginLeft: "auto" }}
        >
          🔄 Atualizar
        </button>
      </div>

      {!Array.isArray(rotas) || rotas.length === 0 ? (
        <div className="empty-state">
          <p>Nenhuma rota finalizada encontrada</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 15 }}>
          {rotas.map((rota) => (
            <div
              key={rota.id}
              style={{
                border: "1px solid #ddd",
                borderRadius: 8,
                padding: 15,
                backgroundColor: "#fff",
              }}
            >
              {/* Cabeçalho - Clicável */}
              <div
                style={{ cursor: "pointer" }}
                onClick={() => toggleRotaExpandida(rota.id)}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div style={{ flex: 1 }}>
                    <h3 style={{ margin: 0, marginBottom: 10 }}>
                      🚚 {rota.numero || `Rota #${rota.id}`}
                      {rotaExpandida === rota.id ? " 🔽" : " ▶️"}
                    </h3>
                    
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 10, color: "#555", fontSize: 14 }}>
                      <div>
                        <strong>Entregador:</strong> {rota.entregador?.nome || "Não informado"}
                      </div>
                      
                      <div>
                        <strong>Paradas:</strong> {rota.paradas?.length || 0} entrega(s)
                      </div>
                      
                      {/* Distância Prevista */}
                      {rota.distancia_prevista && (
                        <div>
                          <strong>📍 Previsto:</strong> {parseFloat(rota.distancia_prevista).toFixed(1)} km
                        </div>
                      )}
                      
                      {/* KM Inicial e Final */}
                      {rota.km_inicial && (
                        <div>
                          <strong>🏁 KM Inicial:</strong> {parseFloat(rota.km_inicial).toFixed(1)}
                        </div>
                      )}
                      
                      {rota.km_final && (
                        <div>
                          <strong>🏁 KM Final:</strong> {parseFloat(rota.km_final).toFixed(1)}
                        </div>
                      )}
                      
                      {/* Total Rodado */}
                      {rota.km_inicial && rota.km_final && (
                        <div style={{ color: "#007BFF", fontWeight: "600" }}>
                          <strong>📏 Total:</strong> {(parseFloat(rota.km_final) - parseFloat(rota.km_inicial)).toFixed(1)} km
                          
                          {/* Comparação com Projetado */}
                          {rota.distancia_prevista && (() => {
                            const realizado = parseFloat(rota.km_final) - parseFloat(rota.km_inicial);
                            const projetado = parseFloat(rota.distancia_prevista);
                            const diferenca = realizado - projetado;
                            const percentual = ((diferenca / projetado) * 100).toFixed(1);
                            
                            return (
                              <div style={{ 
                                fontSize: 12,
                                color: diferenca > 0 ? "#DC3545" : "#28A745",
                                marginTop: 2
                              }}>
                                {diferenca > 0 ? "↑" : "↓"} {Math.abs(diferenca).toFixed(1)} km ({diferenca > 0 ? "+" : ""}{percentual}%)
                              </div>
                            );
                          })()}
                        </div>
                      )}
                      
                      {/* Distância Real (fallback se não tiver KM inicial/final) */}
                      {rota.distancia_real && !(rota.km_inicial && rota.km_final) && (
                        <div>
                          <strong>Distância:</strong> {parseFloat(rota.distancia_real).toFixed(1)} km
                        </div>
                      )}
                      
                      <div>
                        <strong>Concluída em:</strong>{" "}
                        {new Date(rota.data_conclusao).toLocaleString("pt-BR")}
                      </div>
                      
                      {rota.custo_real && (
                        <div>
                          <strong>Custo:</strong> R$ {parseFloat(rota.custo_real).toFixed(2)}
                        </div>
                      )}
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

                  <div
                    style={{
                      padding: "5px 15px",
                      borderRadius: 20,
                      backgroundColor: "#28A745",
                      color: "#fff",
                      fontWeight: "bold",
                      fontSize: 14,
                      whiteSpace: "nowrap",
                    }}
                  >
                    ✅ Concluída
                  </div>
                </div>
              </div>

              {/* Paradas Expandidas */}
              {rotaExpandida === rota.id && rota.paradas && rota.paradas.length > 0 && (
                <div style={{ marginTop: 20, borderTop: "2px solid #eee", paddingTop: 15 }}>
                  <h4 style={{ marginBottom: 15 }}>📍 Entregas da Rota</h4>
                  
                  {rota.paradas.map((parada) => (
                    <div
                      key={parada.id}
                      style={{
                        padding: 12,
                        marginBottom: 10,
                        border: "1px solid #ddd",
                        borderRadius: 6,
                        backgroundColor: parada.status === "entregue" ? "#f0fff4" : "#fafafa",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
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
                            <span style={{
                              marginLeft: 10,
                              padding: "2px 8px",
                              borderRadius: 12,
                              fontSize: 12,
                              backgroundColor: parada.status === "entregue" ? "#d4edda" : "#e2e3e5",
                              color: parada.status === "entregue" ? "#155724" : "#383d41",
                            }}>
                              {parada.status === "entregue" ? "✓ Entregue" : parada.status}
                            </span>
                          </div>
                          
                          <div style={{ fontSize: 13, color: "#333", lineHeight: 1.6 }}>
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
                            
                            <div style={{ color: "#555" }}>
                              📍 {parada.endereco}
                              {parada.distancia_acumulada && (
                                <span style={{ marginLeft: 12, color: "#777" }}>
                                  • Dist: {parada.distancia_acumulada} km
                                </span>
                              )}
                              {parada.km_entrega && (
                                <span style={{ marginLeft: 12, color: "#777" }}>
                                  • KM: {parada.km_entrega}
                                </span>
                              )}
                            </div>
                          </div>
                          
                          {parada.data_entrega && (
                            <div style={{ color: "#28a745", fontSize: 12, marginTop: 3 }}>
                              ✓ Entregue em: {new Date(parada.data_entrega).toLocaleString("pt-BR")}
                            </div>
                          )}
                          
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
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
