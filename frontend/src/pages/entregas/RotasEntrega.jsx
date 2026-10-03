import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import api from "../../api";
import { api as apiServices } from "../../services/api";
import { confirmarCorePet } from "../../services/corepetDialog";
import "./Entregas.css";
import RotaCard from "./RotaCard";
import {
  calcularTempoEstimado,
  filtrarRotasPorStatus,
  formatarTempo,
  getStatusColor,
  getStatusLabel,
  ordenarRotasRecentes,
  separarRotasAtivas,
  statusApiRotas,
} from "./rotasEntregaUtils";

const FILTROS_STATUS = [
  ["ativas", "Todas ativas"],
  ["pendente", "Aguardando início"],
  ["em_execucao", "Em andamento"],
  ["concluida", "Concluídas"],
  ["cancelada", "Canceladas"],
];

export default function RotasEntrega() {
  const navigate = useNavigate();
  const [rotas, setRotas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtroStatus, setFiltroStatus] = useState("ativas");
  const [busca, setBusca] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");
  const [entregadorId, setEntregadorId] = useState("");
  const [entregadores, setEntregadores] = useState([]);
  const [rotaExpandida, setRotaExpandida] = useState(null);
  const [metodoKm, setMetodoKm] = useState("auto_rota"); // default seguro

  useEffect(() => {
    carregarRotas();
  }, [filtroStatus, buscaAplicada, entregadorId]);

  useEffect(() => {
    apiServices
      .get("/configuracoes/entregas")
      .then((r) => setMetodoKm(r.data?.metodo_km_entrega || "auto_rota"))
      .catch(() => {});
    apiServices
      .get("/clientes/", { params: { is_entregador: true, limit: 200 } })
      .then((r) => {
        const lista = r.data?.items || r.data?.clientes || r.data || [];
        setEntregadores(Array.isArray(lista) ? lista : []);
      })
      .catch(() => {});
  }, []);

  async function carregarRotas() {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      const statusApi = statusApiRotas(filtroStatus);
      if (statusApi) params.append("status", statusApi);
      if (buscaAplicada) params.append("busca", buscaAplicada);
      if (entregadorId) params.append("entregador_id", entregadorId);
      params.append("direcao", "desc");
      params.append("ordenar_por", "criacao");
      params.append("limite", "500");

      const response = await api.get(`/rotas-entrega/?${params.toString()}`);
      setRotas(ordenarRotasRecentes(filtrarRotasPorStatus(response.data, filtroStatus)));
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

  function abrirRastreioRota(rota) {
    navigate(`/entregas/rastreamento?rota=${encodeURIComponent(rota.id)}`);
  }

  const gruposAtivos = separarRotasAtivas(rotas);
  const secoes =
    filtroStatus === "ativas"
      ? [
          {
            titulo: "Rotas ativas",
            descricao: "Última rota criada primeiro, com a situação de cada uma no cartão",
            rotas,
          },
        ]
      : [{ titulo: FILTROS_STATUS.find(([id]) => id === filtroStatus)?.[1], rotas }];

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
          <p style={{ color: "#666", marginBottom: 20 }}>
            Acompanhe as rotas ativas e consulte as concluídas no arquivo.
          </p>
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

      <nav className="rotas-filtros-status" aria-label="Situação das rotas">
        {FILTROS_STATUS.map(([id, label]) => (
          <button
            key={id}
            type="button"
            aria-pressed={filtroStatus === id}
            className={filtroStatus === id ? "ativo" : ""}
            onClick={() => setFiltroStatus(id)}
          >
            {label}
          </button>
        ))}
      </nav>

      <div className="rotas-filtros-detalhes">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            setBuscaAplicada(busca.trim());
          }}
        >
          <label htmlFor="busca-rotas">Buscar rota, venda, cliente ou endereço</label>
          <div>
            <input
              id="busca-rotas"
              value={busca}
              onChange={(event) => setBusca(event.target.value)}
              placeholder="Digite para buscar"
            />
            <button type="submit" className="btn-secondary">
              Buscar
            </button>
          </div>
        </form>
        <label htmlFor="entregador-rotas">
          Entregador
          <select
            id="entregador-rotas"
            value={entregadorId}
            onChange={(event) => setEntregadorId(event.target.value)}
          >
            <option value="">Todos</option>
            {entregadores.map((entregador) => (
              <option key={entregador.id} value={entregador.id}>
                {entregador.nome_fantasia || entregador.nome}
              </option>
            ))}
          </select>
        </label>
        <button onClick={carregarRotas} className="btn-secondary">
          🔄 Atualizar
        </button>
      </div>

      {filtroStatus === "ativas" && (
        <div className="rotas-resumo-etapas">
          <button type="button" onClick={() => setFiltroStatus("em_execucao")}>
            <strong>{gruposAtivos.emAndamento.length}</strong>
            <span>Em andamento</span>
          </button>
          <button type="button" onClick={() => setFiltroStatus("pendente")}>
            <strong>{gruposAtivos.pendentes.length}</strong>
            <span>Aguardando início</span>
          </button>
        </div>
      )}

      {filtroStatus === "concluida" && (
        <p className="rotas-arquivo-aviso">
          As rotas concluídas ficam guardadas aqui. Para consultar períodos antigos e resultados,
          abra o{" "}
          <button type="button" onClick={() => navigate("/entregas/historico")}>
            Histórico de Entregas
          </button>
          .
        </p>
      )}

      {!Array.isArray(rotas) || rotas.length === 0 ? (
        <div className="empty-state">
          <p>
            {buscaAplicada || entregadorId
              ? "Nenhuma rota corresponde aos filtros."
              : "Nenhuma rota nesta situação."}
          </p>
          {(filtroStatus === "ativas" || filtroStatus === "pendente") && (
            <button
              onClick={() => navigate("/entregas/abertas")}
              className="btn-primary"
              style={{ marginTop: 10 }}
            >
              Criar Nova Rota
            </button>
          )}
        </div>
      ) : (
        secoes.map(
          (secao) =>
            secao.rotas.length > 0 && (
              <section key={secao.titulo} className="rotas-secao">
                <div className="rotas-secao-cabecalho">
                  <div>
                    <h2>{secao.titulo}</h2>
                    {secao.descricao && <p>{secao.descricao}</p>}
                  </div>
                  <span>{secao.rotas.length} rota(s)</span>
                </div>
                <div className="rotas-secao-lista">
                  {secao.rotas.map((rota) => (
                    <RotaCard
                      key={rota.id}
                      rota={rota}
                      expandida={rotaExpandida === rota.id}
                      onToggleExpand={() => toggleRotaExpandida(rota.id)}
                      onReordenar={reordenarParadas}
                      onIniciarRota={iniciarRota}
                      onExcluirRota={excluirRota}
                      onReverterInicio={reverterInicioRota}
                      onAbrirRastreio={abrirRastreioRota}
                      getStatusColor={getStatusColor}
                      getStatusLabel={getStatusLabel}
                      calcularTempoEstimado={calcularTempoEstimado}
                      formatarTempo={formatarTempo}
                      metodoKm={metodoKm}
                    />
                  ))}
                </div>
              </section>
            ),
        )
      )}
    </div>
  );
}
