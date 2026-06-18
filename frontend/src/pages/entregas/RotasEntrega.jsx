import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../../api";
import { api as apiServices } from "../../services/api";
import MonitoramentoEntregadores from "./MonitoramentoEntregadores";
import RotaCard from "./RotaCard";
import {
  agruparRotasPorEntregador,
  calcularTempoEstimado,
  filtrarRotasEmAndamento,
  formatarTempo,
  getStatusColor,
  getStatusLabel,
  montarDestinoMapaRota,
} from "./rotasEntregaUtils";

export default function RotasEntrega() {
  const navigate = useNavigate();
  const [rotas, setRotas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtroStatus, setFiltroStatus] = useState("");
  const [rotaExpandida, setRotaExpandida] = useState(null);
  const [metodoKm, setMetodoKm] = useState("auto_rota"); // default seguro

  useEffect(() => {
    carregarRotas();
    // Carregar config de entrega para saber o método configurado
    apiServices
      .get("/configuracoes/entregas")
      .then((r) => setMetodoKm(r.data?.metodo_km_entrega || "auto_rota"))
      .catch(() => {}); // silencioso — usa default se falhar
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
      const novaOrdem = paradasOrdenadas.map((p) => p.id);

      await api.put(`/rotas-entrega/${rotaId}/paradas/reordenar`, novaOrdem);

      // Atualizar localmente
      setRotas((prev) =>
        prev.map((r) =>
          r.id === rotaId
            ? {
                ...r,
                paradas: paradasOrdenadas.map((p, idx) => ({
                  ...p,
                  ordem: idx + 1,
                })),
              }
            : r,
        ),
      );

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

    // Sem prompt de km — motoqueiro não precisa digitar nada

    try {
      await api.post(`/rotas-entrega/${rotaId}/iniciar`, null, { params: {} });
      alert("✅ Rota iniciada! Mensagem enviada ao primeiro cliente.");
      carregarRotas();
    } catch (err) {
      console.error("Erro ao iniciar rota:", err);
      const mensagem = err.response?.data?.detail || "Erro ao iniciar rota";
      alert(`❌ ${mensagem}`);
    }
  }

  async function excluirRota(rotaId) {
    if (
      !confirm(
        "⚠️ Tem certeza que deseja excluir esta rota?\n\nAs vendas voltarão para a listagem de entregas pendentes.",
      )
    ) {
      return;
    }

    try {
      const response = await api.delete(`/rotas-entrega/${rotaId}`);
      const { total_vendas } = response.data;
      alert(
        `✅ Rota excluída com sucesso!\n${total_vendas} venda(s) voltaram para entregas pendentes.`,
      );
      carregarRotas(); // Recarregar lista
    } catch (err) {
      console.error("Erro ao excluir rota:", err);
      const mensagem = err.response?.data?.detail || "Erro ao excluir rota";
      alert(`❌ ${mensagem}`);
    }
  }

  async function reverterInicioRota(rotaId) {
    if (
      !confirm(
        "↩️ Reverter início desta rota?\n\nA rota voltará para status pendente e você poderá adicionar mais entregas.",
      )
    ) {
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

  function abrirMapaRota(rota) {
    const destino = montarDestinoMapaRota(rota);
    if (destino?.url) {
      window.open(destino.url, "_blank", "noopener,noreferrer");
      return;
    }

    alert("Esta rota ainda não tem localização ou endereço para abrir no mapa.");
  }

  const rotasEmAndamento = filtrarRotasEmAndamento(rotas);
  const monitoramentoEntregadores = agruparRotasPorEntregador(rotasEmAndamento);

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
      <p style={{ color: "#666", marginBottom: 20 }}>Rotas criadas e em andamento</p>

      <div
        style={{
          marginBottom: 20,
          display: "flex",
          gap: 10,
          alignItems: "center",
        }}
      >
        <label>
          Filtrar por status:
          <select
            value={filtroStatus}
            onChange={(e) => setFiltroStatus(e.target.value)}
            style={{ marginLeft: 10, padding: "5px 10px" }}
          >
            <option value="">Todos</option>
            <option value="pendente">Pendente</option>
            <option value="em_rota">Em Rota</option>
            <option value="em_andamento">Em Andamento</option>
            <option value="concluida">Concluída</option>
            <option value="cancelada">Cancelada</option>
          </select>
        </label>

        <button onClick={carregarRotas} className="btn-secondary" style={{ marginLeft: "auto" }}>
          🔄 Atualizar
        </button>
      </div>

      <MonitoramentoEntregadores
        grupos={monitoramentoEntregadores}
        onAbrirMapaRota={abrirMapaRota}
      />

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
              metodoKm={metodoKm}
            />
          ))}
        </div>
      )}
    </div>
  );
}
