import {
  formatarHorarioLocalizacao,
  getUltimaParadaPendente,
} from "./rotasEntregaUtils";

export default function MonitoramentoEntregadores({
  grupos = {},
  onAbrirMapaRota,
}) {
  const gruposOrdenados = Object.values(grupos);

  if (gruposOrdenados.length === 0) return null;

  return (
    <div
      style={{
        marginBottom: 24,
        padding: 16,
        borderRadius: 10,
        border: "1px solid #cde7d8",
        backgroundColor: "#f3fbf6",
      }}
    >
      <h3 style={{ marginTop: 0, marginBottom: 12 }}>
        📡 Entregas em andamento por entregador
      </h3>
      <p style={{ marginTop: 0, marginBottom: 14, color: "#4d5b52" }}>
        Acompanhe quem está na rua agora e abra o rastreio em tempo real com 1 clique.
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {gruposOrdenados.map((grupo) => (
          <div
            key={grupo.entregadorNome}
            style={{
              border: "1px solid #d7e6dc",
              borderRadius: 8,
              backgroundColor: "#fff",
              padding: 12,
            }}
          >
            <div style={{ fontWeight: 700, marginBottom: 8 }}>
              🧑‍🛵 {grupo.entregadorNome}
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {grupo.rotas.map((rota) => {
                const ultimaParada = getUltimaParadaPendente(rota);
                const temPosicaoAtual = rota?.lat_atual && rota?.lon_atual;

                return (
                  <div
                    key={rota.id}
                    style={{
                      padding: 10,
                      border: "1px solid #eef2ef",
                      borderRadius: 6,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: 10,
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600 }}>
                        🚚 {rota.numero || `Rota #${rota.id}`} •{" "}
                        {rota.paradas?.length || 0} parada(s)
                      </div>
                      <div
                        style={{
                          fontSize: 13,
                          color: "#59665e",
                          marginTop: 4,
                        }}
                      >
                        {temPosicaoAtual
                          ? `📍 Localização ao vivo atualizada às ${formatarHorarioLocalizacao(rota.localizacao_atualizada_em)}`
                          : "📍 Sem localização ao vivo no momento"}
                      </div>
                      <div
                        style={{
                          fontSize: 13,
                          color: "#59665e",
                          marginTop: 2,
                        }}
                      >
                        Próxima entrega:{" "}
                        {ultimaParada?.endereco || "Não informado"}
                      </div>
                    </div>

                    <button
                      onClick={() => onAbrirMapaRota(rota)}
                      style={{
                        padding: "8px 12px",
                        borderRadius: 6,
                        border: "none",
                        backgroundColor: "#1f7a4d",
                        color: "#fff",
                        fontWeight: 600,
                        cursor: "pointer",
                        whiteSpace: "nowrap",
                      }}
                    >
                      📡 Ver rastreio
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
