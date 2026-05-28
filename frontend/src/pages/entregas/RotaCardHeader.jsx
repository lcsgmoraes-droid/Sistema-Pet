function RotaCardHeader({
  rota,
  expandida,
  onToggleExpand,
  tempoEstimado,
  formatarTempo,
  todasEntregue,
  processandoFinalizacao,
  finalizarRota,
  paradasPendentes,
  paradasOrdenadas,
  onIniciarRota,
  onReverterInicio,
  onExcluirRota,
  getStatusColor,
  getStatusLabel,
}) {
  return (
    <>
      {/* Cabeçalho do Card - Clicável */}
      <div
        style={{
          cursor: "pointer",
          transition: "all 0.2s",
        }}
        onClick={onToggleExpand}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
          }}
        >
          <div style={{ flex: 1 }}>
            <h3 style={{ margin: 0, marginBottom: 10 }}>
              🚚 {rota.numero || `Rota #${rota.id}`}
              {expandida ? " 🔽" : " ▶️"}
            </h3>

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 5,
                color: "#555",
              }}
            >
              <div>
                <strong>Entregador:</strong>{" "}
                {rota.entregador?.nome || "Não informado"}
              </div>

              <div>
                <strong>Paradas:</strong> {rota.paradas?.length || 0} entrega(s)
              </div>

              {rota.distancia_prevista && (
                <div>
                  <strong>Distância Prevista:</strong> {rota.distancia_prevista}{" "}
                  km
                </div>
              )}

              {rota.distancia_total_km_real && (
                <div style={{ color: "#0c4a6e", fontWeight: "600" }}>
                  <strong>📍 Distância Real (GPS):</strong>{" "}
                  {parseFloat(rota.distancia_total_km_real).toFixed(2)} km
                </div>
              )}

              {rota.distancia_ate_ultima_entrega_km_real && (
                <div>
                  <strong>📦 Até última entrega:</strong>{" "}
                  {parseFloat(rota.distancia_ate_ultima_entrega_km_real).toFixed(2)} km
                </div>
              )}

              {rota.distancia_retorno_km_real && (
                <div>
                  <strong>↩️ Retorno vazio:</strong>{" "}
                  {parseFloat(rota.distancia_retorno_km_real).toFixed(2)} km
                </div>
              )}

              {tempoEstimado && (
                <div>
                  <strong>Tempo Estimado:</strong>{" "}
                  {formatarTempo(tempoEstimado)}
                </div>
              )}

              {/* KM Inicial - Mostra quando a rota foi iniciada */}
              {rota.km_inicial && (
                <div>
                  <strong>🏁 KM Inicial:</strong>{" "}
                  {parseFloat(rota.km_inicial).toFixed(1)} km
                </div>
              )}

              {/* KM Final - Mostra quando a rota foi finalizada */}
              {rota.km_final && (
                <div>
                  <strong>🏁 KM Final:</strong>{" "}
                  {parseFloat(rota.km_final).toFixed(1)} km
                </div>
              )}

              {/* Total de KM Rodados - Calcula se tiver inicial e final */}
              {rota.km_inicial && rota.km_final && (
                <div style={{ color: "#007BFF", fontWeight: "600" }}>
                  <strong>📏 Total Rodado:</strong>{" "}
                  {(
                    parseFloat(rota.km_final) - parseFloat(rota.km_inicial)
                  ).toFixed(1)}{" "}
                  km
                  {/* Comparação com Projetado - Se existir distância prevista */}
                  {rota.distancia_prevista &&
                    (() => {
                      const realizado =
                        parseFloat(rota.km_final) - parseFloat(rota.km_inicial);
                      const projetado = parseFloat(rota.distancia_prevista);
                      const diferenca = realizado - projetado;
                      const percentual = (
                        (diferenca / projetado) *
                        100
                      ).toFixed(1);

                      return (
                        <span
                          style={{
                            marginLeft: 10,
                            color: diferenca > 0 ? "#DC3545" : "#28A745",
                            fontSize: 13,
                          }}
                        >
                          ({diferenca > 0 ? "+" : ""}
                          {diferenca.toFixed(1)} km /{" "}
                          {percentual > 0 ? "+" : ""}
                          {percentual}% vs projetado)
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
                  gap: 5,
                }}
              >
                🚀 Iniciar Rota
              </button>
            )}

            {/* Botão Finalizar Rota - visível quando rota em_rota e todas entregas concluídas */}
            {(rota.status === "em_rota" || rota.status === "em_andamento") &&
              todasEntregue && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    finalizarRota(rota.id, rota.km_inicial);
                  }}
                  disabled={processandoFinalizacao}
                  style={{
                    padding: "8px 16px",
                    backgroundColor: processandoFinalizacao
                      ? "#ccc"
                      : "#007BFF",
                    color: "#fff",
                    border: "none",
                    borderRadius: 6,
                    cursor: processandoFinalizacao ? "not-allowed" : "pointer",
                    fontWeight: "bold",
                    fontSize: 14,
                    display: "flex",
                    alignItems: "center",
                    gap: 5,
                  }}
                >
                  {processandoFinalizacao
                    ? "⏳ Processando..."
                    : "✅ Finalizar Rota"}
                </button>
              )}

            {/* Botão Reverter Início - visível quando rota em_rota mas nenhuma entrega foi feita */}
            {(rota.status === "em_rota" || rota.status === "em_andamento") &&
              paradasPendentes === paradasOrdenadas.length && (
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
                    gap: 5,
                  }}
                >
                  ↩️ Reverter Início
                </button>
              )}

            {/* Botão Excluir Rota - visível para rotas pendentes ou em_rota */}
            {(rota.status === "pendente" ||
              rota.status === "em_rota" ||
              rota.status === "em_andamento") && (
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
                  gap: 5,
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
    </>
  );
}

export default RotaCardHeader;
