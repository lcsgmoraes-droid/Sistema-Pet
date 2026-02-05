import { useEffect, useState } from "react";
import { api } from "../../services/api";
import ModalParadasRota from "./ModalParadasRota";
import "./Entregas.css";

export default function RotasEntrega() {
  const [loading, setLoading] = useState(true);
  const [rotas, setRotas] = useState([]);
  const [filtroStatus, setFiltroStatus] = useState("todos");
  const [pontoInicial, setPontoInicial] = useState("");
  
  // Modal fechar rota
  const [showModalFechar, setShowModalFechar] = useState(false);
  const [rotaSelecionada, setRotaSelecionada] = useState(null);
  const [formFechar, setFormFechar] = useState({
    distancia_real: "",
    tentativas: 1,
    observacoes: "",
  });
  
  // ETAPA 9.3: Modal de paradas
  const [showModalParadas, setShowModalParadas] = useState(false);
  const [rotaParadasSelecionada, setRotaParadasSelecionada] = useState(null);

  useEffect(() => {
    carregarDados();
  }, [filtroStatus]);

  async function carregarDados() {
    setLoading(true);
    try {
      const params = filtroStatus !== "todos" ? { status: filtroStatus } : {};
      const [rotasRes, configRes] = await Promise.all([
        api.get("/rotas-entrega", { params }),
        api.get("/configuracoes/entregas").catch(() => ({ data: null })),
      ]);
      
      setRotas(rotasRes.data || []);
      
      // Montar endereço completo do ponto inicial
      if (configRes.data) {
        const config = configRes.data;
        const endereco = [
          config.logradouro,
          config.numero ? `, ${config.numero}` : "",
          config.complemento ? ` - ${config.complemento}` : "",
          config.bairro ? ` - ${config.bairro}` : "",
          config.cidade ? ` - ${config.cidade}` : "",
          config.estado ? `/${config.estado}` : "",
        ].join("");
        setPontoInicial(endereco);
      }
    } catch (err) {
      console.error(err);
      alert("Erro ao carregar dados");
    } finally {
      setLoading(false);
    }
  }

  async function carregarRotas() {
    await carregarDados();
  }

  async function handleIniciarRota(rota) {
    if (!confirm(`Iniciar rota ${rota.numero}?`)) return;

    try {
      await api.put(`/rotas-entrega/${rota.id}`, { status: "em_rota" });
      alert("Rota iniciada!");
      carregarRotas();
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || "Erro ao iniciar rota");
    }
  }

  function abrirModalFechar(rota) {
    setRotaSelecionada(rota);
    setFormFechar({
      distancia_real: rota.distancia_prevista || "",
      tentativas: 1,
      observacoes: "",
    });
    setShowModalFechar(true);
  }

  async function handleFecharRota(e) {
    e.preventDefault();

    if (!formFechar.distancia_real || parseFloat(formFechar.distancia_real) <= 0) {
      alert("Informe a distância real percorrida");
      return;
    }

    if (!formFechar.tentativas || parseInt(formFechar.tentativas) < 1) {
      alert("Informe o número de tentativas (mínimo 1)");
      return;
    }

    try {
      await api.post(`/rotas-entrega/${rotaSelecionada.id}/fechar`, {
        distancia_real: parseFloat(formFechar.distancia_real),
        tentativas: parseInt(formFechar.tentativas),
        observacoes: formFechar.observacoes,
      });

      alert("Rota finalizada com sucesso!");
      setShowModalFechar(false);
      carregarRotas();
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || "Erro ao fechar rota");
    }
  }

  async function handleCancelarRota(rota) {
    const obs = prompt("Motivo do cancelamento:");
    if (!obs) return;

    try {
      await api.put(`/rotas-entrega/${rota.id}`, {
        status: "cancelada",
        observacoes: obs,
      });

      alert("Rota cancelada!");
      carregarRotas();
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || "Erro ao cancelar rota");
    }
  }

  function getStatusBadge(status) {
    const badges = {
      pendente: { text: "Pendente", color: "#ffa500" },
      em_rota: { text: "Em Rota", color: "#2196f3" },
      concluida: { text: "Concluída", color: "#4caf50" },
      cancelada: { text: "Cancelada", color: "#f44336" },
    };

    const badge = badges[status] || badges.pendente;

    return (
      <span
        style={{
          padding: "4px 8px",
          borderRadius: 4,
          fontSize: 12,
          fontWeight: "bold",
          color: "#fff",
          backgroundColor: badge.color,
        }}
      >
        {badge.text}
      </span>
    );
  }

  function abrirModalParadas(rota) {
    setRotaParadasSelecionada(rota);
    setShowModalParadas(true);
  }

  if (loading) return <div className="page">Carregando...</div>;

  return (
    <div className="page">
      <h1>Rotas de Entrega</h1>

      <div className="filters" style={{ marginBottom: 20 }}>
        <label>Status:</label>
        <select value={filtroStatus} onChange={(e) => setFiltroStatus(e.target.value)}>
          <option value="todos">Todos</option>
          <option value="pendente">Pendente</option>
          <option value="em_rota">Em Rota</option>
          <option value="concluida">Concluída</option>
          <option value="cancelada">Cancelada</option>
        </select>
      </div>

      {rotas.length === 0 ? (
        <div className="empty-state">
          <p>Nenhuma rota encontrada</p>
        </div>
      ) : (
        <table className="table-rotas">
          <thead>
            <tr>
              <th>Rota</th>
              <th>Venda</th>
              <th>Entregador</th>
              <th>Status</th>
              <th>KM Previsto</th>
              <th>KM Real</th>
              <th>Custo Previsto</th>
              <th>Custo Real</th>
              <th>Paradas</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {rotas.map((rota) => (
              <tr key={rota.id}>
                <td>{rota.numero}</td>
                <td>#{rota.venda_id || "N/A"}</td>
                <td>{rota.entregador?.nome || `ID ${rota.entregador_id}`}</td>
                <td>{getStatusBadge(rota.status)}</td>
                <td>{rota.distancia_prevista || "-"}</td>
                <td>{rota.distancia_real || "-"}</td>
                <td>R$ {parseFloat(rota.custo_previsto || 0).toFixed(2)}</td>
                <td>R$ {parseFloat(rota.custo_real || 0).toFixed(2)}</td>
                <td>
                  {/* ETAPA 9.3: Botão para ver paradas */}
                  {rota.paradas && rota.paradas.length > 0 ? (
                    <button
                      className="btn-small"
                      onClick={() => abrirModalParadas(rota)}
                      title="Ver sequência de paradas"
                    >
                      🗺️ {rota.paradas.length}
                    </button>
                  ) : (
                    <span style={{ color: "#999" }}>-</span>
                  )}
                </td>
                <td>
                  {rota.status === "pendente" && (
                    <>
                      <button
                        className="btn-small btn-primary"
                        onClick={() => handleIniciarRota(rota)}
                        title="Iniciar rota"
                      >
                        ▶️
                      </button>
                      {" "}
                      <button
                        className="btn-small btn-danger"
                        onClick={() => handleCancelarRota(rota)}
                        title="Cancelar"
                      >
                        ❌
                      </button>
                    </>
                  )}

                  {rota.status === "em_rota" && (
                    <>
                      <button
                        className="btn-small btn-success"
                        onClick={() => abrirModalFechar(rota)}
                        title="Fechar rota"
                      >
                        ✅
                      </button>
                      {" "}
                      <button
                        className="btn-small btn-danger"
                        onClick={() => handleCancelarRota(rota)}
                        title="Cancelar"
                      >
                        ❌
                      </button>
                    </>
                  )}

                  {(rota.status === "concluida" || rota.status === "cancelada") && (
                    <span style={{ color: "#999" }}>-</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Modal Fechar Rota */}
      {showModalFechar && (
        <div className="modal-overlay" onClick={() => setShowModalFechar(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Fechar Rota: {rotaSelecionada.numero}</h2>

            <form onSubmit={handleFecharRota}>
              <div className="form-group">
                <label>Distância Real (km) *</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={formFechar.distancia_real}
                  onChange={(e) =>
                    setFormFechar({ ...formFechar, distancia_real: e.target.value })
                  }
                  required
                  autoFocus
                />
              </div>

              <div className="form-group">
                <label>Tentativas *</label>
                <input
                  type="number"
                  min="1"
                  value={formFechar.tentativas}
                  onChange={(e) =>
                    setFormFechar({ ...formFechar, tentativas: e.target.value })
                  }
                  required
                />
                <small style={{ display: "block", color: "#666", marginTop: 5 }}>
                  Número de tentativas de entrega realizadas
                </small>
              </div>

              <div className="form-group">
                <label>Observações</label>
                <textarea
                  value={formFechar.observacoes}
                  onChange={(e) =>
                    setFormFechar({ ...formFechar, observacoes: e.target.value })
                  }
                  rows={3}
                  placeholder="Ex: Cliente recebeu normalmente"
                />
              </div>

              <div className="modal-actions">
                <button type="button" onClick={() => setShowModalFechar(false)}>
                  Cancelar
                </button>
                <button type="submit" className="btn-success">
                  Finalizar Entrega
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ETAPA 9.3: Modal Paradas da Rota */}
      {showModalParadas && rotaParadasSelecionada && (
        <ModalParadasRota
          rota={rotaParadasSelecionada}
          pontoInicial={pontoInicial}
          onClose={() => setShowModalParadas(false)}
          onSave={carregarRotas}
        />
      )}
    </div>
  );
}
