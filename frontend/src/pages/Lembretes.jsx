import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiBell, FiCheckCircle, FiRefreshCw, FiTrash2 } from "react-icons/fi";
import api from "../api";
import "../styles/Lembretes.css";

export default function Lembretes() {
  const [lembretes, setLembretes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState("pendente"); // pendente, notificado, completado, todos
  const [alertasCampanhas, setAlertasCampanhas] = useState(null);

  useEffect(() => {
    carregarLembretes();
    carregarAlertasCampanhas();
    // Atualizar a cada 1 minuto
    const interval = setInterval(carregarLembretes, 60000);
    return () => clearInterval(interval);
  }, []);

  const carregarAlertasCampanhas = async () => {
    try {
      const res = await api.get("/campanhas/dashboard");
      setAlertasCampanhas(res.data);
    } catch {
      // silencioso — alertas são informativos, não críticos
    }
  };

  const carregarLembretes = async () => {
    setLoading(true);
    try {
      const response = await api.get("/api/lembretes/pendentes");
      setLembretes(response.data.lembretes || []);
    } catch (error) {
      console.error("Erro ao carregar lembretes:", error);
      toast.error("Erro ao carregar lembretes");
    } finally {
      setLoading(false);
    }
  };

  const completarLembrete = async (lembrete_id) => {
    try {
      await api.post(`/api/lembretes/${lembrete_id}/completar`, {});
      toast.success("Lembrete marcado como completado");
      carregarLembretes();
    } catch (error) {
      toast.error("Erro ao completar lembrete");
    }
  };

  const renovarLembrete = async (lembrete_id) => {
    try {
      await api.post(`/api/lembretes/${lembrete_id}/renovar`, {});
      toast.success("Lembrete renovado com sucesso");
      carregarLembretes();
    } catch (error) {
      toast.error("Erro ao renovar lembrete");
    }
  };

  const cancelarLembrete = async (lembrete_id) => {
    if (window.confirm("Tem certeza que deseja cancelar este lembrete?")) {
      try {
        await api.delete(`/api/lembretes/${lembrete_id}`);
        toast.success("Lembrete cancelado");
        carregarLembretes();
      } catch (error) {
        toast.error("Erro ao cancelar lembrete");
      }
    }
  };

  const proximosEmBreve = lembretes.filter((l) => l.dias_restantes <= 7);
  const vencidos = lembretes.filter((l) => l.dias_restantes < 0);

  return (
    <div className="lembretes-container">
      <div className="lembretes-header">
        <h1>📌 Lembretes de Recorrência</h1>
        <div className="stats-grid">
          <div className="stat-card">
            <span className="stat-number">{lembretes.length}</span>
            <span className="stat-label">Total de Lembretes</span>
          </div>
          <div className="stat-card warning">
            <span className="stat-number">{proximosEmBreve.length}</span>
            <span className="stat-label">Próximos em 7 dias</span>
          </div>
          <div className="stat-card danger">
            <span className="stat-number">{vencidos.length}</span>
            <span className="stat-label">Vencidos</span>
          </div>
        </div>
      </div>

      {/* ── Alertas de Campanhas ── */}
      {alertasCampanhas && (
        <div
          style={{
            marginBottom: "20px",
            borderRadius: "12px",
            border: "1px solid #e5e7eb",
            overflow: "hidden",
            background: "#fff",
          }}
        >
          <div
            style={{
              background: "#fef3c7",
              padding: "12px 20px",
              borderBottom: "1px solid #fde68a",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <span style={{ fontSize: "16px" }}>🔔</span>
            <span
              style={{ fontWeight: "600", color: "#92400e", fontSize: "14px" }}
            >
              Alertas de Campanhas
            </span>
          </div>
          <div
            style={{
              padding: "12px 20px",
              display: "flex",
              flexWrap: "wrap",
              gap: "12px",
            }}
          >
            {/* Aniversários amanhã */}
            {alertasCampanhas.proximos_eventos?.total_aniversarios_amanha >
              0 && (
              <div
                style={{
                  background: "#fdf2f8",
                  border: "1px solid #f9a8d4",
                  borderRadius: "8px",
                  padding: "10px 14px",
                  minWidth: "180px",
                }}
              >
                <p
                  style={{
                    fontWeight: "700",
                    color: "#9d174d",
                    fontSize: "22px",
                    margin: 0,
                  }}
                >
                  {alertasCampanhas.proximos_eventos.total_aniversarios_amanha}
                </p>
                <p
                  style={{
                    color: "#6b7280",
                    fontSize: "12px",
                    margin: "2px 0 6px",
                  }}
                >
                  🎂 Aniversário(s) amanhã
                </p>
                <div>
                  {alertasCampanhas.proximos_eventos.aniversarios_amanha
                    .slice(0, 3)
                    .map((a, i) => (
                      <p
                        key={i}
                        style={{
                          fontSize: "12px",
                          color: "#374151",
                          margin: "1px 0",
                        }}
                      >
                        {a.tipo === "pet" ? "🐕" : "👤"} {a.nome}
                      </p>
                    ))}
                  {alertasCampanhas.proximos_eventos.total_aniversarios_amanha >
                    3 && (
                    <p
                      style={{
                        fontSize: "11px",
                        color: "#9ca3af",
                        margin: "2px 0 0",
                      }}
                    >
                      +
                      {alertasCampanhas.proximos_eventos
                        .total_aniversarios_amanha - 3}{" "}
                      mais
                    </p>
                  )}
                </div>
              </div>
            )}
            {/* Aniversários de hoje */}
            {alertasCampanhas.total_aniversarios > 0 && (
              <div
                style={{
                  background: "#fff7ed",
                  border: "1px solid #fed7aa",
                  borderRadius: "8px",
                  padding: "10px 14px",
                  minWidth: "180px",
                }}
              >
                <p
                  style={{
                    fontWeight: "700",
                    color: "#c2410c",
                    fontSize: "22px",
                    margin: 0,
                  }}
                >
                  {alertasCampanhas.total_aniversarios}
                </p>
                <p
                  style={{
                    color: "#6b7280",
                    fontSize: "12px",
                    margin: "2px 0 6px",
                  }}
                >
                  🎉 Aniversário(s) hoje
                </p>
                <div>
                  {alertasCampanhas.aniversarios_hoje
                    .slice(0, 3)
                    .map((a, i) => (
                      <p
                        key={i}
                        style={{
                          fontSize: "12px",
                          color: "#374151",
                          margin: "1px 0",
                        }}
                      >
                        {a.tipo === "pet" ? "🐕" : "👤"} {a.nome}
                      </p>
                    ))}
                </div>
              </div>
            )}
            {/* Clientes inativos */}
            {alertasCampanhas.alertas?.inativos_30d > 0 && (
              <div
                style={{
                  background: "#fff7ed",
                  border: "1px solid #fdba74",
                  borderRadius: "8px",
                  padding: "10px 14px",
                  minWidth: "160px",
                }}
              >
                <p
                  style={{
                    fontWeight: "700",
                    color: "#c2410c",
                    fontSize: "22px",
                    margin: 0,
                  }}
                >
                  {alertasCampanhas.alertas.inativos_30d}
                </p>
                <p
                  style={{
                    color: "#6b7280",
                    fontSize: "12px",
                    margin: "2px 0 0",
                  }}
                >
                  😴 Inativos há +30 dias
                </p>
              </div>
            )}
            {/* Novos inativos hoje */}
            {alertasCampanhas.alertas?.novos_inativos_hoje > 0 && (
              <div
                style={{
                  background: "#fef2f2",
                  border: "1px solid #fca5a5",
                  borderRadius: "8px",
                  padding: "10px 14px",
                  minWidth: "160px",
                }}
              >
                <p
                  style={{
                    fontWeight: "700",
                    color: "#b91c1c",
                    fontSize: "22px",
                    margin: 0,
                  }}
                >
                  {alertasCampanhas.alertas.novos_inativos_hoje}
                </p>
                <p
                  style={{
                    color: "#6b7280",
                    fontSize: "12px",
                    margin: "2px 0 0",
                  }}
                >
                  🚨 Atingiram 30 dias de inatividade hoje
                </p>
              </div>
            )}
            {/* Sorteios pendentes */}
            {alertasCampanhas.alertas?.total_sorteios_pendentes > 0 && (
              <div
                style={{
                  background: "#fefce8",
                  border: "1px solid #fde047",
                  borderRadius: "8px",
                  padding: "10px 14px",
                  minWidth: "160px",
                }}
              >
                <p
                  style={{
                    fontWeight: "700",
                    color: "#a16207",
                    fontSize: "22px",
                    margin: 0,
                  }}
                >
                  {alertasCampanhas.alertas.total_sorteios_pendentes}
                </p>
                <p
                  style={{
                    color: "#6b7280",
                    fontSize: "12px",
                    margin: "2px 0 0",
                  }}
                >
                  🎲 Sorteio(s) pendente(s)
                </p>
              </div>
            )}
            {/* Sorteios esta semana */}
            {alertasCampanhas.proximos_eventos?.sorteios_esta_semana?.length >
              0 && (
              <div
                style={{
                  background: "#fffbeb",
                  border: "1px solid #fcd34d",
                  borderRadius: "8px",
                  padding: "10px 14px",
                  minWidth: "180px",
                }}
              >
                <p
                  style={{
                    fontWeight: "700",
                    color: "#92400e",
                    fontSize: "22px",
                    margin: 0,
                  }}
                >
                  {
                    alertasCampanhas.proximos_eventos.sorteios_esta_semana
                      .length
                  }
                </p>
                <p
                  style={{
                    color: "#6b7280",
                    fontSize: "12px",
                    margin: "2px 0 6px",
                  }}
                >
                  🎯 Sorteio(s) esta semana
                </p>
                <div>
                  {alertasCampanhas.proximos_eventos.sorteios_esta_semana
                    .slice(0, 3)
                    .map((s, i) => (
                      <p
                        key={i}
                        style={{
                          fontSize: "12px",
                          color: "#374151",
                          margin: "1px 0",
                        }}
                      >
                        {s.name}
                        {s.draw_date
                          ? ` • ${new Date(s.draw_date).toLocaleDateString("pt-BR")}`
                          : ""}
                      </p>
                    ))}
                </div>
              </div>
            )}
            {/* Brindes pendentes de retirada */}
            {alertasCampanhas.alertas?.total_brindes_pendentes > 0 && (
              <div
                style={{
                  background: "#fff7ed",
                  border: "1px solid #fdba74",
                  borderRadius: "8px",
                  padding: "10px 14px",
                  minWidth: "180px",
                }}
              >
                <p
                  style={{
                    fontWeight: "700",
                    color: "#c2410c",
                    fontSize: "22px",
                    margin: 0,
                  }}
                >
                  {alertasCampanhas.alertas.total_brindes_pendentes}
                </p>
                <p
                  style={{
                    color: "#6b7280",
                    fontSize: "12px",
                    margin: "2px 0 6px",
                  }}
                >
                  🎁 Brinde(s) pendente(s) de retirada
                </p>
                <div>
                  {alertasCampanhas.alertas.brindes_pendentes
                    .slice(0, 2)
                    .map((b, i) => (
                      <p
                        key={i}
                        style={{
                          fontSize: "12px",
                          color: "#374151",
                          margin: "1px 0",
                        }}
                      >
                        {b.nome_cliente}
                        {b.retirar_ate
                          ? ` • até ${new Date(b.retirar_ate).toLocaleDateString("pt-BR")}`
                          : ""}
                      </p>
                    ))}
                  {alertasCampanhas.alertas.total_brindes_pendentes > 2 && (
                    <p
                      style={{
                        fontSize: "11px",
                        color: "#9ca3af",
                        margin: "2px 0 0",
                      }}
                    >
                      +{alertasCampanhas.alertas.total_brindes_pendentes - 2}{" "}
                      mais
                    </p>
                  )}
                </div>
              </div>
            )}
            {/* Fim do mês - sempre visível */}
            {alertasCampanhas.proximos_eventos?.dias_ate_fim_mes != null && (
              <div
                style={{
                  background: alertasCampanhas.proximos_eventos.dias_ate_fim_mes <= 3 ? "#fefce8" : "#f0fdf4",
                  border: alertasCampanhas.proximos_eventos.dias_ate_fim_mes <= 3 ? "1px solid #fde047" : "1px solid #86efac",
                  borderRadius: "8px",
                  padding: "10px 14px",
                  minWidth: "160px",
                }}
              >
                <p
                  style={{
                    fontWeight: "700",
                    color: alertasCampanhas.proximos_eventos.dias_ate_fim_mes <= 3 ? "#a16207" : "#15803d",
                    fontSize: "22px",
                    margin: 0,
                  }}
                >
                  {alertasCampanhas.proximos_eventos.dias_ate_fim_mes}
                </p>
                <p
                  style={{
                    color: "#6b7280",
                    fontSize: "12px",
                    margin: "2px 0 0",
                  }}
                >
                  🌟{" "}
                  {alertasCampanhas.proximos_eventos.dias_ate_fim_mes === 0
                    ? "Último dia — calcule o destaque!"
                    : `dia(s) p/ Destaque Mensal`}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {loading && <div className="loading">Carregando lembretes...</div>}

      {lembretes.length === 0 ? (
        <div className="empty-state">
          <FiBell size={48} />
          <h2>Nenhum lembrete pendente</h2>
          <p>
            Lembretes serão criados automaticamente para produtos recorrentes.
          </p>
        </div>
      ) : (
        <div className="lembretes-list">
          {vencidos.length > 0 && (
            <div className="section">
              <h3 className="section-title danger">⚠️ Vencidos</h3>
              {vencidos.map((l) => (
                <LembretCard
                  key={l.id}
                  lembrete={l}
                  onCompletar={completarLembrete}
                  onRenovar={renovarLembrete}
                  onCancelar={cancelarLembrete}
                />
              ))}
            </div>
          )}

          {proximosEmBreve.length > 0 && (
            <div className="section">
              <h3 className="section-title warning">
                🔔 Próximos em até 7 dias
              </h3>
              {proximosEmBreve.map((l) => (
                <LembretCard
                  key={l.id}
                  lembrete={l}
                  onCompletar={completarLembrete}
                  onRenovar={renovarLembrete}
                  onCancelar={cancelarLembrete}
                />
              ))}
            </div>
          )}

          {lembretes.filter((l) => l.dias_restantes > 7).length > 0 && (
            <div className="section">
              <h3 className="section-title">📅 Próximos (mais de 7 dias)</h3>
              {lembretes
                .filter((l) => l.dias_restantes > 7)
                .map((l) => (
                  <LembretCard
                    key={l.id}
                    lembrete={l}
                    onCompletar={completarLembrete}
                    onRenovar={renovarLembrete}
                    onCancelar={cancelarLembrete}
                  />
                ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function LembretCard({ lembrete, onCompletar, onRenovar, onCancelar }) {
  const diasRestantes = lembrete.dias_restantes;
  const dataProxima = new Date(lembrete.data_proxima_dose);
  const statusClass =
    diasRestantes < 0 ? "vencido" : diasRestantes <= 7 ? "proximo" : "futuro";

  // Progresso de doses
  const temDoseTotal = lembrete.dose_total && lembrete.dose_total > 0;
  const progressoPercentual = temDoseTotal
    ? (lembrete.dose_atual / lembrete.dose_total) * 100
    : 0;

  return (
    <div className={`lembrete-card ${statusClass}`}>
      <div className="card-content">
        <div className="card-header">
          <h4>{lembrete.produto_nome}</h4>
          <div className="badges">
            {temDoseTotal && (
              <span className="dose-badge">
                Dose {lembrete.dose_atual}/{lembrete.dose_total}
              </span>
            )}
            <span className={`status-badge ${statusClass}`}>
              {diasRestantes < 0 ? "VENCIDO" : `${Math.abs(diasRestantes)}d`}
            </span>
          </div>
        </div>

        {temDoseTotal && (
          <div className="progress-bar-container">
            <div
              className="progress-bar"
              style={{ width: `${progressoPercentual}%` }}
            ></div>
          </div>
        )}

        <div className="card-details">
          <div className="detail-row">
            <span className="label">Pet:</span>
            <span className="value">{lembrete.pet_nome}</span>
          </div>
          <div className="detail-row">
            <span className="label">Data:</span>
            <span className="value">
              {dataProxima.toLocaleDateString("pt-BR")}
            </span>
          </div>
          <div className="detail-row">
            <span className="label">Quantidade:</span>
            <span className="value">{lembrete.quantidade}</span>
          </div>
          {lembrete.preco_estimado && (
            <div className="detail-row">
              <span className="label">Preço Est.:</span>
              <span className="value">
                R$ {lembrete.preco_estimado.toFixed(2)}
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="card-actions">
        <button
          className="btn btn-success"
          onClick={() => onCompletar(lembrete.id)}
          title="Marcar como completado"
        >
          <FiCheckCircle /> Comprado
        </button>
        <button
          className="btn btn-primary"
          onClick={() => onRenovar(lembrete.id)}
          title="Renovar lembrete"
        >
          <FiRefreshCw /> Renovar
        </button>
        <button
          className="btn btn-danger"
          onClick={() => onCancelar(lembrete.id)}
          title="Cancelar lembrete"
        >
          <FiTrash2 />
        </button>
      </div>
    </div>
  );
}
