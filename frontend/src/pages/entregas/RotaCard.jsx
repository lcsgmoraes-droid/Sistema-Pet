import { useEffect, useState } from "react";
import api from "../../api";
import CustomerIdentity from "../../components/ui/CustomerIdentity";
import RotaVendaDetalhes from "./RotaVendaDetalhes";
import RotaCardHeader from "./RotaCardHeader";

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
  formatarTempo,
  metodoKm,
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
  const paradasPendentes = paradasOrdenadas.filter(
    (p) => p.status !== "entregue",
  ).length;
  const todasEntregue = paradasOrdenadas.length > 0 && paradasPendentes === 0;

  async function carregarDetalhesVenda(paradaId, vendaId) {
    try {
      setLoadingDetalhes(true);
      setParadaDetalhesAberta(paradaId);
      const response = await api.get(`/vendas/${vendaId}`);
      console.log("📦 Detalhes da venda carregados:", response.data);
      console.log("📞 Telefones do cliente:", {
        telefone: response.data.cliente?.telefone,
        celular: response.data.cliente?.celular,
        email: response.data.cliente?.email,
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
    if (
      !confirm(
        "✅ Confirmar entrega realizada?\n\nUma mensagem será enviada automaticamente para o próximo cliente da rota.",
      )
    ) {
      return;
    }

    try {
      setProcessandoEntrega(paradaId);

      const params = {};
      const metodo = metodoKm || "auto_rota";

      if (metodo === "manual") {
        // Entregador digita o km do odômetro manualmente
        const kmDigitado = prompt(
          "🏁 Digite o KM atual do odômetro (opcional):\n\nDeixe em branco para pular.",
        );
        if (kmDigitado && !isNaN(kmDigitado) && parseFloat(kmDigitado) > 0) {
          params.km_entrega = parseFloat(kmDigitado);
        }
      } else if (metodo === "auto_rota") {
        // Auto-calcular a partir da distância da rota otimizada
        const parada = paradasOrdenadas.find((p) => p.id === paradaId);
        if (parada?.distancia_acumulada && rota.km_inicial) {
          const kmAuto =
            parseFloat(rota.km_inicial) +
            parseFloat(parada.distancia_acumulada);
          params.km_entrega = parseFloat(kmAuto.toFixed(2));
        }
      }
      // Se metodo === "gps": não registra km_entrega, só coordenadas GPS abaixo

      // GPS: capturar localização silenciosamente em qualquer método (para rastreamento)
      try {
        const gps = await new Promise((resolve) => {
          if (!navigator.geolocation) {
            resolve(null);
            return;
          }
          navigator.geolocation.getCurrentPosition(
            (pos) =>
              resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
            () => resolve(null),
            { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 },
          );
        });
        if (gps) {
          params.lat_entrega = gps.lat;
          params.lon_entrega = gps.lon;
        }
      } catch (_) {
        // GPS não disponível — continua sem coordenadas
      }

      const response = await api.post(
        `/rotas-entrega/${rotaId}/paradas/${paradaId}/marcar-entregue`,
        null,
        { params },
      );
      alert("✅ " + response.data.message);

      // Atualizar estado local da parada
      setParadasOrdenadas((prev) =>
        prev.map((p) =>
          p.id === paradaId
            ? {
                ...p,
                status: "entregue",
                data_entrega: new Date().toISOString(),
                km_entrega: params.km_entrega || null,
              }
            : p,
        ),
      );

      // Recarregar a rota completa para garantir sincronização
      window.location.reload();
    } catch (err) {
      console.error("Erro ao marcar entrega:", err);
      const mensagem =
        err.response?.data?.detail || "Erro ao marcar entrega como concluída";
      alert("❌ " + mensagem);
    } finally {
      setProcessandoEntrega(null);
    }
  }

  async function adicionarObservacao(paradaId, rotaId) {
    const observacao = prompt(
      "📋 Digite a observação sobre esta entrega:\n\n(Ex: 'Sempre entregar no vizinho', 'Chamar na casa da frente')",
    );

    if (!observacao || observacao.trim() === "") {
      return;
    }

    try {
      await api.put(
        `/rotas-entrega/${rotaId}/paradas/${paradaId}/observacao`,
        null,
        {
          params: { observacao: observacao.trim() },
        },
      );

      alert("✅ Observação salva com sucesso!");

      // Atualizar localmente
      setParadasOrdenadas((prev) =>
        prev.map((p) =>
          p.id === paradaId ? { ...p, observacoes: observacao.trim() } : p,
        ),
      );
    } catch (err) {
      console.error("Erro ao salvar observação:", err);
      alert("❌ Erro ao salvar observação");
    }
  }

  async function marcarNaoEntregue(paradaId, rotaId, vendaId) {
    const motivo = prompt(
      "⚠️ Por que a entrega não foi realizada?\n\n(Ex: 'Cliente ausente', 'Cartão recusado', 'Endereço não encontrado')",
    );

    if (!motivo || motivo.trim() === "") {
      return;
    }

    if (
      !confirm(
        "⚠️ Confirmar que a entrega NÃO foi realizada?\n\nA venda voltará para entregas em aberto.",
      )
    ) {
      return;
    }

    try {
      setProcessandoNaoEntregue(paradaId);
      await api.post(
        `/rotas-entrega/${rotaId}/paradas/${paradaId}/nao-entregue`,
        null,
        {
          params: { motivo: motivo.trim() },
        },
      );

      alert(
        "✅ Entrega marcada como não realizada. Venda #" +
          vendaId +
          " voltou para entregas em aberto.",
      );
      window.location.reload();
    } catch (err) {
      console.error("Erro ao marcar como não entregue:", err);
      alert("❌ Erro ao processar");
    } finally {
      setProcessandoNaoEntregue(null);
    }
  }

  async function finalizarRota(rotaId, kmInicial) {
    const metodo = metodoKm || "auto_rota";

    // Distância total da rota otimizada (última parada com distancia_acumulada)
    const ultimaParadaComDistancia = [...paradasOrdenadas]
      .reverse()
      .find((p) => p.distancia_acumulada);
    const distanciaRouteTotal = ultimaParadaComDistancia
      ? parseFloat(ultimaParadaComDistancia.distancia_acumulada)
      : null;
    const distanciaGpsTotal = rota.distancia_total_km_real
      ? parseFloat(rota.distancia_total_km_real)
      : null;

    // Montar mensagem de confirmação com distância se disponível
    let msgConfirm =
      "✅ Finalizar esta rota?\n\nEsta ação não pode ser desfeita.";
    if (distanciaGpsTotal) {
      msgConfirm = `✅ Finalizar esta rota?\n\n📏 Distância real pelo GPS: ${distanciaGpsTotal.toFixed(2)} km\n\nEsta ação não pode ser desfeita.`;
    } else if (metodo === "auto_rota" && distanciaRouteTotal) {
      msgConfirm = `✅ Finalizar esta rota?\n\n📏 Distância percorrida estimada: ${distanciaRouteTotal.toFixed(2)} km\n\nEsta ação não pode ser desfeita.`;
    }

    if (!confirm(msgConfirm)) {
      return;
    }

    try {
      setProcessandoFinalizacao(true);

      const payload = {};

      if (metodo === "manual") {
        // Entregador digita km final do odômetro
        const kmFinalDigitado = prompt(
          "🏁 Digite o KM final do odômetro (opcional):\n\nDeixe em branco para pular.",
        );
        if (
          kmFinalDigitado &&
          !isNaN(kmFinalDigitado) &&
          parseFloat(kmFinalDigitado) > 0
        ) {
          payload.km_final = parseFloat(kmFinalDigitado);
          if (kmInicial) {
            payload.distancia_real =
              parseFloat(kmFinalDigitado) - parseFloat(kmInicial);
          }
        }
      } else if (distanciaGpsTotal) {
        payload.distancia_real = distanciaGpsTotal;
        if (kmInicial) {
          payload.km_final = parseFloat(kmInicial) + distanciaGpsTotal;
        }
      } else if (metodo === "auto_rota") {
        // Auto-calcular a partir da distância da rota
        if (distanciaRouteTotal) {
          payload.distancia_real = distanciaRouteTotal;
        }
        if (kmInicial && distanciaRouteTotal) {
          payload.km_final = parseFloat(kmInicial) + distanciaRouteTotal;
        }
      }
      // Se metodo === "gps": não calcula km, apenas registra a finalização

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
      <RotaCardHeader
        rota={rota}
        expandida={expandida}
        onToggleExpand={onToggleExpand}
        tempoEstimado={tempoEstimado}
        formatarTempo={formatarTempo}
        todasEntregue={todasEntregue}
        processandoFinalizacao={processandoFinalizacao}
        finalizarRota={finalizarRota}
        paradasPendentes={paradasPendentes}
        paradasOrdenadas={paradasOrdenadas}
        onIniciarRota={onIniciarRota}
        onReverterInicio={onReverterInicio}
        onExcluirRota={onExcluirRota}
        getStatusColor={getStatusColor}
        getStatusLabel={getStatusLabel}
      />

      {/* Paradas Expandidas */}
      {expandida && paradasOrdenadas.length > 0 && (
        <div
          style={{ marginTop: 20, borderTop: "2px solid #eee", paddingTop: 15 }}
        >
          <h4 style={{ marginBottom: 15 }}>
            📍 Paradas da Rota (arraste para reordenar)
          </h4>

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
                  backgroundColor:
                    draggedIndex === index ? "#f0f8ff" : "#fafafa",
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
                    <span style={{ color: "#666", fontSize: 14 }}>
                      Venda #{parada.venda_id}
                    </span>
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
                          • Acumulado real: {Number(parada.distancia_acumulada_real_km).toFixed(2)} km
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
                    <div
                      style={{ color: "#28a745", fontSize: 12, marginTop: 3 }}
                    >
                      ✓ Entregue em:{" "}
                      {new Date(parada.data_entrega).toLocaleString("pt-BR")}
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
                  {parada.status !== "entregue" &&
                    rota.status === "em_rota" && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          marcarComoEntregue(parada.id, rota.id);
                        }}
                        disabled={processandoEntrega === parada.id}
                        style={{
                          padding: "8px 12px",
                          backgroundColor:
                            processandoEntrega === parada.id
                              ? "#ccc"
                              : "#28A745",
                          color: "#fff",
                          border: "none",
                          borderRadius: 6,
                          cursor:
                            processandoEntrega === parada.id
                              ? "not-allowed"
                              : "pointer",
                          fontWeight: "600",
                          fontSize: 12,
                          whiteSpace: "nowrap",
                          width: "130px",
                          textAlign: "center",
                        }}
                      >
                        {processandoEntrega === parada.id
                          ? "⏳..."
                          : "✅ Entregue"}
                      </button>
                    )}

                  {/* Botão Não Entregue - só aparece para rotas em andamento */}
                  {parada.status !== "entregue" &&
                    (rota.status === "em_rota" ||
                      rota.status === "em_andamento") && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          marcarNaoEntregue(
                            parada.id,
                            rota.id,
                            parada.venda_id,
                          );
                        }}
                        disabled={processandoNaoEntregue === parada.id}
                        style={{
                          padding: "8px 12px",
                          backgroundColor:
                            processandoNaoEntregue === parada.id
                              ? "#ccc"
                              : "#FFC107",
                          color: "#000",
                          border: "none",
                          borderRadius: 6,
                          cursor:
                            processandoNaoEntregue === parada.id
                              ? "not-allowed"
                              : "pointer",
                          fontWeight: "600",
                          fontSize: 12,
                          whiteSpace: "nowrap",
                          width: "130px",
                          textAlign: "center",
                        }}
                      >
                        {processandoNaoEntregue === parada.id
                          ? "⏳..."
                          : "⚠️ Falta Entregar"}
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
    </div>
  );
}

export default RotaCard;
