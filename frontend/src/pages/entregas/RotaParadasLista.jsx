import CustomerIdentity from "../../components/ui/CustomerIdentity";
import RotaVendaDetalhes from "./RotaVendaDetalhes";

function RotaParadasLista({
  expandida,
  paradasOrdenadas,
  draggedIndex,
  handleDragStart,
  handleDragOver,
  handleDragEnd,
  formatarTempo,
  rota,
  marcarComoEntregue,
  processandoEntrega,
  marcarNaoEntregue,
  processandoNaoEntregue,
  adicionarObservacao,
  paradaDetalhesAberta,
  fecharDetalhes,
  carregarDetalhesVenda,
  loadingDetalhes,
  vendaDetalhes,
}) {
  return (
    <>
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
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      marginBottom: 5,
                    }}
                  >
                    <span
                      style={{
                        fontWeight: "bold",
                        marginRight: 10,
                        fontSize: 18,
                        color: "#007BFF",
                      }}
                    >
                      {parada.ordem}º
                    </span>
                    <span style={{ color: "#666", fontSize: 14 }}>Venda #{parada.venda_id}</span>
                    {parada.status && (
                      <span
                        style={{
                          marginLeft: 10,
                          padding: "2px 8px",
                          borderRadius: 12,
                          fontSize: 12,
                          backgroundColor:
                            parada.status === "entregue"
                              ? "#d4edda"
                              : parada.status === "tentativa"
                                ? "#fff3cd"
                                : "#e2e3e5",
                          color:
                            parada.status === "entregue"
                              ? "#155724"
                              : parada.status === "tentativa"
                                ? "#856404"
                                : "#383d41",
                        }}
                      >
                        {parada.status === "entregue"
                          ? "✓ Entregue"
                          : parada.status === "tentativa"
                            ? "⚠ Tentativa"
                            : "Pendente"}
                      </span>
                    )}
                  </div>

                  {/* Cliente e Informações em layout compacto */}
                  <div style={{ fontSize: 13, color: "#333", lineHeight: 1.6 }}>
                    {/* Nome e Telefones */}
                    {parada.cliente_nome && (
                      <div style={{ marginBottom: 4 }}>
                        <span style={{ color: "#1565C0" }}>
                          <CustomerIdentity
                            nameClassName="font-semibold text-blue-700"
                            record={parada}
                          />
                        </span>
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
                      {parada.distancia_trecho_real_km && (
                        <span style={{ marginLeft: 12, color: "#0f766e", fontWeight: 600 }}>
                          • Trecho real: {Number(parada.distancia_trecho_real_km).toFixed(2)} km
                        </span>
                      )}
                      {parada.distancia_acumulada_real_km && (
                        <span style={{ marginLeft: 12, color: "#0f766e" }}>
                          • Acumulado real: {Number(parada.distancia_acumulada_real_km).toFixed(2)}{" "}
                          km
                        </span>
                      )}
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
                    <div
                      style={{
                        marginTop: 6,
                        padding: 6,
                        backgroundColor: "#fff3cd",
                        borderRadius: 4,
                        fontSize: 12,
                        color: "#856404",
                        border: "1px solid #ffc107",
                      }}
                    >
                      📋 {parada.observacoes}
                    </div>
                  )}
                </div>

                {/* Botões de Ação */}
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 6,
                    alignItems: "flex-end",
                  }}
                >
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
                  {parada.status !== "entregue" &&
                    (rota.status === "em_rota" || rota.status === "em_andamento") && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          marcarNaoEntregue(parada.id, rota.id, parada.venda_id);
                        }}
                        disabled={processandoNaoEntregue === parada.id}
                        style={{
                          padding: "8px 12px",
                          backgroundColor:
                            processandoNaoEntregue === parada.id ? "#ccc" : "#FFC107",
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

              {paradaDetalhesAberta === parada.id && (
                <RotaVendaDetalhes
                  loading={loadingDetalhes}
                  venda={vendaDetalhes}
                  onFechar={(e) => {
                    e.stopPropagation();
                    fecharDetalhes();
                  }}
                />
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}

export default RotaParadasLista;
