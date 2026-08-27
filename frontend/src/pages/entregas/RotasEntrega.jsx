import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import api from "../../api";
import { api as apiServices } from "../../services/api";
import { confirmarCorePet } from "../../services/corepetDialog";
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
      toast.error("Erro ao carregar rotas de entrega");
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

      toast.success("Ordem das paradas atualizada");
    } catch (err) {
      console.error("Erro ao reordenar paradas:", err);
      toast.error("Erro ao reordenar paradas");
    }
  }

  async function iniciarRota(rotaId) {
    if (
      !(await confirmarCorePet({
        titulo: "Iniciar esta rota?",
        mensagem: "A rota passara para Em rota e o primeiro cliente recebera uma mensagem.",
        confirmarTexto: "Iniciar rota",
        variante: "success",
      }))
    ) {
      return;
    }

    // Sem prompt de km — motoqueiro não precisa digitar nada

    try {
      await api.post(`/rotas-entrega/${rotaId}/iniciar`, null, { params: {} });
      toast.success("Rota iniciada. Mensagem enviada ao primeiro cliente.");
      carregarRotas();
    } catch (err) {
      console.error("Erro ao iniciar rota:", err);
      const mensagem = err.response?.data?.detail || "Erro ao iniciar rota";
      toast.error(mensagem);
    }
  }

  async function excluirRota(rotaId) {
    if (
      !(await confirmarCorePet({
        titulo: "Excluir esta rota?",
        mensagem: "As vendas voltarao para a lista de entregas pendentes.",
        confirmarTexto: "Excluir rota",
        variante: "danger",
      }))
    ) {
      return;
    }

    try {
      const response = await api.delete(`/rotas-entrega/${rotaId}`);
      const { total_vendas } = response.data;
      toast.success(`Rota excluida. ${total_vendas} venda(s) voltaram para entregas pendentes.`);
      carregarRotas(); // Recarregar lista
    } catch (err) {
      console.error("Erro ao excluir rota:", err);
      const mensagem = err.response?.data?.detail || "Erro ao excluir rota";
      toast.error(mensagem);
    }
  }

  async function reverterInicioRota(rotaId) {
    if (
      !(await confirmarCorePet({
        titulo: "Reverter inicio da rota?",
        mensagem: "A rota voltara para Pendente e aceitara novas entregas.",
        confirmarTexto: "Reverter para pendente",
        variante: "warning",
      }))
    ) {
      return;
    }

    try {
      await api.post(`/rotas-entrega/${rotaId}/reverter-inicio`);
      toast.success("Rota revertida para pendente. Agora voce pode adicionar mais entregas.");
      carregarRotas(); // Recarregar lista
    } catch (err) {
      console.error("Erro ao reverter rota:", err);
      const mensagem = err.response?.data?.detail || "Erro ao reverter início da rota";
      toast.error(mensagem);
    }
  }

  function abrirMapaRota(rota) {
    const destino = montarDestinoMapaRota(rota);
    if (destino?.url) {
      window.open(destino.url, "_blank", "noopener,noreferrer");
      return;
    }

    toast.error("Esta rota ainda não tem localizacao ou endereco para abrir no mapa.");
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
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h1>Rotas de Entrega</h1>
          <p style={{ color: "#666", marginBottom: 20 }}>Rotas criadas e em andamento</p>
        </div>
        <button
          type="button"
          onClick={() => navigate("/entregas/rastreamento")}
          className="btn-primary"
          style={{ alignSelf: "flex-start" }}
        >
          📡 Abrir rastreamento ao vivo
        </button>
      </div>

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
