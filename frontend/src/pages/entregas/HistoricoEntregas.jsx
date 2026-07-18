import { useCallback, useEffect, useMemo, useState } from "react";
import api from "../../api";
import CustomerIdentity from "../../components/ui/CustomerIdentity";
import SaleReference from "../../components/ui/SaleReference";
import { formatMoneyBRL } from "../../utils/formatters";
import "./Entregas.css";
import {
  calcularPeriodoRapidoHistorico,
  calcularResumoHistorico,
  formatarDuracao,
  montarParametrosHistorico,
  obterDistanciaRota,
  obterQuantidadeEntregas,
} from "./historicoEntregasUtils";

const PERIODOS_RAPIDOS = [
  ["hoje", "Hoje"],
  ["ontem", "Ontem"],
  ["esta_semana", "Esta semana"],
  ["ultimos_7_dias", "7 dias"],
  ["ultimos_30_dias", "30 dias"],
  ["este_mes", "Este mês"],
  ["todos", "Tudo"],
];

function dataLocal(diasAtras = 0) {
  const data = new Date();
  data.setDate(data.getDate() - diasAtras);
  const offset = data.getTimezoneOffset() * 60_000;
  return new Date(data.getTime() - offset).toISOString().slice(0, 10);
}

const FILTROS_INICIAIS = {
  // Intervalo inclusivo: hoje + 29 dias anteriores = 30 dias.
  dataInicio: dataLocal(29),
  dataFim: dataLocal(),
  entregadorId: "",
  busca: "",
  ordenarPor: "data_conclusao",
  direcao: "desc",
};

function formatarData(data) {
  if (!data) return "Não informado";
  const valor = new Date(data);
  return Number.isNaN(valor.getTime()) ? "Não informado" : valor.toLocaleString("pt-BR");
}

function formatarKm(valor) {
  return `${Number(valor || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 2,
  })} km`;
}

function rotuloModeloCusto(modelo) {
  return (
    {
      taxa_fixa: "Taxa fixa por entrega",
      por_km: "Custo por km",
      rateio_rh: "Rateio de RH por entrega",
      legado_rateado: "Histórico rateado",
      sem_configuracao: "Sem custo configurado",
    }[modelo] || "Não informado"
  );
}

function ResumoCard({ label, valor, detalhe, cor = "#1d4ed8" }) {
  return (
    <div
      style={{
        background: "#fff",
        border: "1px solid #e5e7eb",
        borderLeft: `4px solid ${cor}`,
        borderRadius: 10,
        padding: 14,
      }}
    >
      <div style={{ color: "#6b7280", fontSize: 12 }}>{label}</div>
      <div style={{ color: "#111827", fontSize: 22, fontWeight: 700, marginTop: 3 }}>{valor}</div>
      {detalhe && <div style={{ color: "#6b7280", fontSize: 12, marginTop: 3 }}>{detalhe}</div>}
    </div>
  );
}

export default function HistoricoEntregas() {
  const [rotas, setRotas] = useState([]);
  const [entregadores, setEntregadores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [rotaExpandida, setRotaExpandida] = useState(null);
  const [filtros, setFiltros] = useState(FILTROS_INICIAIS);
  const [filtrosAplicados, setFiltrosAplicados] = useState(FILTROS_INICIAIS);
  const [periodoRapido, setPeriodoRapido] = useState("ultimos_30_dias");

  const carregarHistorico = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get("/rotas-entrega/", {
        params: montarParametrosHistorico(filtrosAplicados),
      });
      setRotas(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      console.error("Erro ao carregar histórico:", err);
      alert("Não foi possível carregar o histórico de entregas.");
    } finally {
      setLoading(false);
    }
  }, [filtrosAplicados]);

  useEffect(() => {
    void carregarHistorico();
  }, [carregarHistorico]);

  useEffect(() => {
    api
      .get("/clientes/", {
        params: { is_entregador: true, incluir_inativos: true, limit: 200 },
      })
      .then((response) => {
        const lista = response.data?.items || response.data?.clientes || response.data || [];
        setEntregadores(Array.isArray(lista) ? lista : []);
      })
      .catch((err) => console.error("Erro ao carregar entregadores:", err));
  }, []);

  const resumo = useMemo(() => calcularResumoHistorico(rotas), [rotas]);

  function atualizarFiltro(campo, valor) {
    setFiltros((atual) => ({ ...atual, [campo]: valor }));
  }

  function aplicarFiltros(event) {
    event.preventDefault();
    setRotaExpandida(null);
    setFiltrosAplicados({ ...filtros });
  }

  function limparFiltros() {
    setFiltros(FILTROS_INICIAIS);
    setFiltrosAplicados(FILTROS_INICIAIS);
    setRotaExpandida(null);
    setPeriodoRapido("ultimos_30_dias");
  }

  function aplicarPeriodoRapido(periodo) {
    const datas = calcularPeriodoRapidoHistorico(periodo);
    const proximosFiltros = { ...filtros, ...datas };
    setFiltros(proximosFiltros);
    setFiltrosAplicados(proximosFiltros);
    setPeriodoRapido(periodo);
    setRotaExpandida(null);
  }

  return (
    <div className="page">
      <div style={{ display: "flex", gap: 12, justifyContent: "space-between", flexWrap: "wrap" }}>
        <div>
          <h1 style={{ marginBottom: 4 }}>📜 Histórico de Entregas</h1>
          <p style={{ color: "#666", marginTop: 0 }}>
            Rotas concluídas, entregas realizadas e resultado operacional.
          </p>
        </div>
        <button onClick={carregarHistorico} className="btn-secondary" disabled={loading}>
          🔄 {loading ? "Atualizando..." : "Atualizar"}
        </button>
      </div>

      <form
        onSubmit={aplicarFiltros}
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
          gap: 12,
          padding: 16,
          margin: "18px 0",
          background: "#f8fafc",
          border: "1px solid #e2e8f0",
          borderRadius: 10,
        }}
      >
        <div style={{ gridColumn: "1 / -1" }}>
          <span style={{ display: "block", fontSize: 12, color: "#475569", marginBottom: 7 }}>
            Período rápido
          </span>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>
            {PERIODOS_RAPIDOS.map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => aplicarPeriodoRapido(id)}
                aria-pressed={periodoRapido === id}
                style={{
                  border: periodoRapido === id ? "1px solid #2563eb" : "1px solid #cbd5e1",
                  background: periodoRapido === id ? "#dbeafe" : "#fff",
                  color: periodoRapido === id ? "#1d4ed8" : "#475569",
                  borderRadius: 999,
                  padding: "6px 11px",
                  cursor: "pointer",
                  fontWeight: periodoRapido === id ? 700 : 500,
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        <label>
          <span style={{ display: "block", fontSize: 12, color: "#475569", marginBottom: 4 }}>
            Data inicial
          </span>
          <input
            type="date"
            value={filtros.dataInicio}
            onChange={(event) => {
              atualizarFiltro("dataInicio", event.target.value);
              setPeriodoRapido(null);
            }}
            style={{ width: "100%", padding: 8, border: "1px solid #cbd5e1", borderRadius: 6 }}
          />
        </label>
        <label>
          <span style={{ display: "block", fontSize: 12, color: "#475569", marginBottom: 4 }}>
            Data final
          </span>
          <input
            type="date"
            value={filtros.dataFim}
            onChange={(event) => {
              atualizarFiltro("dataFim", event.target.value);
              setPeriodoRapido(null);
            }}
            style={{ width: "100%", padding: 8, border: "1px solid #cbd5e1", borderRadius: 6 }}
          />
        </label>
        <label>
          <span style={{ display: "block", fontSize: 12, color: "#475569", marginBottom: 4 }}>
            Entregador
          </span>
          <select
            value={filtros.entregadorId}
            onChange={(event) => atualizarFiltro("entregadorId", event.target.value)}
            style={{ width: "100%", padding: 8, border: "1px solid #cbd5e1", borderRadius: 6 }}
          >
            <option value="">Todos</option>
            {entregadores.map((entregador) => (
              <option key={entregador.id} value={entregador.id}>
                {entregador.nome}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span style={{ display: "block", fontSize: 12, color: "#475569", marginBottom: 4 }}>
            Buscar
          </span>
          <input
            value={filtros.busca}
            onChange={(event) => atualizarFiltro("busca", event.target.value)}
            placeholder="Rota, venda, cliente ou endereço"
            style={{ width: "100%", padding: 8, border: "1px solid #cbd5e1", borderRadius: 6 }}
          />
        </label>
        <label>
          <span style={{ display: "block", fontSize: 12, color: "#475569", marginBottom: 4 }}>
            Ordenar por
          </span>
          <select
            value={filtros.ordenarPor}
            onChange={(event) => atualizarFiltro("ordenarPor", event.target.value)}
            style={{ width: "100%", padding: 8, border: "1px solid #cbd5e1", borderRadius: 6 }}
          >
            <option value="data_conclusao">Data de conclusão</option>
            <option value="entregas">Quantidade de entregas</option>
            <option value="distancia">Distância</option>
            <option value="custo">Custo total</option>
            <option value="entregador">Entregador</option>
            <option value="numero">Número da rota</option>
          </select>
        </label>
        <label>
          <span style={{ display: "block", fontSize: 12, color: "#475569", marginBottom: 4 }}>
            Direção
          </span>
          <select
            value={filtros.direcao}
            onChange={(event) => atualizarFiltro("direcao", event.target.value)}
            style={{ width: "100%", padding: 8, border: "1px solid #cbd5e1", borderRadius: 6 }}
          >
            <option value="desc">Maior / mais recente</option>
            <option value="asc">Menor / mais antiga</option>
          </select>
        </label>
        <div style={{ display: "flex", alignItems: "end", gap: 8 }}>
          <button className="btn-primary" type="submit" style={{ flex: 1 }}>
            Filtrar
          </button>
          <button className="btn-secondary" type="button" onClick={limparFiltros}>
            Limpar
          </button>
        </div>
      </form>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(155px, 1fr))",
          gap: 10,
          marginBottom: 18,
        }}
      >
        <ResumoCard label="Rotas" valor={resumo.rotas} detalhe={`${resumo.entregas} entregas`} />
        <ResumoCard label="Distância" valor={formatarKm(resumo.distancia)} cor="#0f766e" />
        <ResumoCard label="Custo total" valor={formatMoneyBRL(resumo.custo)} cor="#dc2626" />
        <ResumoCard
          label="Custo por entrega"
          valor={formatMoneyBRL(resumo.custoMedio)}
          cor="#ea580c"
        />
        <ResumoCard label="Taxas cobradas" valor={formatMoneyBRL(resumo.taxas)} cor="#2563eb" />
        <ResumoCard
          label="Resultado das taxas"
          valor={formatMoneyBRL(resumo.resultadoEntrega)}
          detalhe="Taxas menos custo operacional"
          cor={resumo.resultadoEntrega >= 0 ? "#16a34a" : "#dc2626"}
        />
      </div>

      {loading ? (
        <div className="empty-state">Carregando histórico...</div>
      ) : rotas.length === 0 ? (
        <div className="empty-state">Nenhuma rota concluída encontrada com estes filtros.</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {rotas.map((rota) => {
            const expandida = rotaExpandida === rota.id;
            const quantidade = obterQuantidadeEntregas(rota);
            const distancia = obterDistanciaRota(rota);
            const custo = Number(rota.custo_real) || 0;
            const custoPorEntrega =
              Number(rota.custo_por_entrega) || (quantidade > 0 ? custo / quantidade : 0);
            const taxas = Number(rota.taxa_total_entregas ?? rota.taxa_entrega_cliente) || 0;

            return (
              <article
                key={rota.id}
                style={{ border: "1px solid #dbe2ea", borderRadius: 10, background: "#fff" }}
              >
                <button
                  type="button"
                  onClick={() => setRotaExpandida(expandida ? null : rota.id)}
                  style={{
                    width: "100%",
                    padding: 16,
                    border: 0,
                    background: "transparent",
                    cursor: "pointer",
                    textAlign: "left",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 12,
                      alignItems: "flex-start",
                      flexWrap: "wrap",
                    }}
                  >
                    <div style={{ flex: 1, minWidth: 260 }}>
                      <h3 style={{ margin: 0, color: "#0f172a" }}>
                        🚚 {rota.numero || `Rota #${rota.id}`} {expandida ? "▾" : "▸"}
                      </h3>
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                          gap: 8,
                          marginTop: 12,
                          color: "#475569",
                          fontSize: 13,
                        }}
                      >
                        <span>
                          <strong>Entregador:</strong> {rota.entregador?.nome || "Não informado"}
                        </span>
                        <span>
                          <strong>Entregas:</strong> {quantidade}
                        </span>
                        <span>
                          <strong>Concluída:</strong> {formatarData(rota.data_conclusao)}
                        </span>
                        <span>
                          <strong>Duração:</strong> {formatarDuracao(rota.duracao_minutos)}
                        </span>
                        <span>
                          <strong>Distância:</strong> {formatarKm(distancia)}
                        </span>
                        <span>
                          <strong>Custo total:</strong> {formatMoneyBRL(custo)}
                        </span>
                        <span>
                          <strong>Custo/entrega:</strong> {formatMoneyBRL(custoPorEntrega)}
                        </span>
                        <span>
                          <strong>Taxas:</strong> {formatMoneyBRL(taxas)}
                        </span>
                      </div>
                    </div>
                    <span
                      style={{
                        padding: "5px 12px",
                        borderRadius: 999,
                        background: "#dcfce7",
                        color: "#166534",
                        fontWeight: 700,
                        fontSize: 12,
                      }}
                    >
                      ✓ Concluída
                    </span>
                  </div>
                </button>

                {expandida && (
                  <div style={{ borderTop: "1px solid #e5e7eb", padding: 16 }}>
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
                        gap: 8,
                        padding: 12,
                        background: "#f8fafc",
                        borderRadius: 8,
                        marginBottom: 14,
                        fontSize: 13,
                      }}
                    >
                      <span>
                        <strong>Início:</strong> {formatarData(rota.data_inicio)}
                      </span>
                      <span>
                        <strong>Previsto:</strong> {formatarKm(rota.distancia_prevista)}
                      </span>
                      <span>
                        <strong>KM inicial:</strong> {rota.km_inicial ?? "Não informado"}
                      </span>
                      <span>
                        <strong>KM final:</strong> {rota.km_final ?? "Não informado"}
                      </span>
                      <span>
                        <strong>Custo entregador:</strong> {formatMoneyBRL(rota.custo_entregador)}
                      </span>
                      <span>
                        <strong>Custo moto:</strong> {formatMoneyBRL(rota.custo_moto)}
                      </span>
                      <span>
                        <strong>Vendas transportadas:</strong>{" "}
                        {formatMoneyBRL(rota.valor_total_vendas)}
                      </span>
                      <span>
                        <strong>Tentativas:</strong> {rota.tentativas || 1}
                      </span>
                    </div>

                    {rota.observacoes && (
                      <div
                        style={{
                          padding: 10,
                          background: "#fffbeb",
                          borderRadius: 7,
                          marginBottom: 12,
                        }}
                      >
                        <strong>Observações da rota:</strong> {rota.observacoes}
                      </div>
                    )}

                    <h4 style={{ margin: "0 0 10px" }}>📍 Entregas da rota</h4>
                    <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
                      {(rota.paradas || []).map((parada) => (
                        <div
                          key={parada.id}
                          style={{
                            border: "1px solid #e2e8f0",
                            borderRadius: 8,
                            padding: 12,
                            background: parada.status === "entregue" ? "#f0fdf4" : "#fff",
                          }}
                        >
                          <div
                            style={{ display: "flex", justifyContent: "space-between", gap: 10 }}
                          >
                            <div style={{ flex: 1 }}>
                              <div
                                style={{
                                  display: "flex",
                                  gap: 8,
                                  alignItems: "center",
                                  flexWrap: "wrap",
                                }}
                              >
                                <strong style={{ color: "#1d4ed8" }}>{parada.ordem}º</strong>
                                <SaleReference value={parada.numero_venda || parada.venda_id} />
                                <span style={{ color: "#166534", fontSize: 12 }}>✓ Entregue</span>
                              </div>
                              <div style={{ marginTop: 7 }}>
                                <CustomerIdentity
                                  nameClassName="font-semibold text-blue-700"
                                  record={parada}
                                />
                                {(parada.cliente_celular || parada.cliente_telefone) && (
                                  <span style={{ marginLeft: 10, color: "#64748b", fontSize: 12 }}>
                                    📞 {parada.cliente_celular || parada.cliente_telefone}
                                  </span>
                                )}
                              </div>
                              <div style={{ color: "#475569", fontSize: 13, marginTop: 5 }}>
                                📍 {parada.endereco}
                              </div>
                              <div
                                style={{
                                  display: "flex",
                                  flexWrap: "wrap",
                                  gap: "5px 14px",
                                  color: "#64748b",
                                  fontSize: 12,
                                  marginTop: 7,
                                }}
                              >
                                <span>Venda: {formatMoneyBRL(parada.valor_venda)}</span>
                                <span>Taxa: {formatMoneyBRL(parada.taxa_entrega)}</span>
                                {parada.custo_operacional != null && (
                                  <span>
                                    Custo operacional: {formatMoneyBRL(parada.custo_operacional)}
                                  </span>
                                )}
                                {Number(parada.custo_moto_rateado) > 0 && (
                                  <span>
                                    Moto rateada: {formatMoneyBRL(parada.custo_moto_rateado)}
                                  </span>
                                )}
                                {parada.custo_operacional != null && (
                                  <span>
                                    Custo total da entrega:{" "}
                                    {formatMoneyBRL(
                                      Number(parada.custo_operacional || 0) +
                                        Number(parada.custo_moto_rateado || 0),
                                    )}
                                  </span>
                                )}
                                {parada.modelo_custo_operacional && (
                                  <span>
                                    Critério: {rotuloModeloCusto(parada.modelo_custo_operacional)}
                                  </span>
                                )}
                                {parada.modelo_custo_operacional === "por_km" && (
                                  <span>
                                    Base registrada:{" "}
                                    {formatMoneyBRL(parada.valor_base_custo_operacional)}/km ×{" "}
                                    {formatarKm(parada.distancia_custo_km)}
                                  </span>
                                )}
                                {["taxa_fixa", "rateio_rh"].includes(
                                  parada.modelo_custo_operacional,
                                ) && (
                                  <span>
                                    Base registrada:{" "}
                                    {formatMoneyBRL(parada.valor_base_custo_operacional)} por
                                    entrega
                                  </span>
                                )}
                                {Number(parada.tentativas) > 1 && (
                                  <span>Tentativas desta entrega: {parada.tentativas}</span>
                                )}
                                <span>Pagamento: {parada.status_pagamento || "Não informado"}</span>
                                {parada.forma_pagamento && (
                                  <span>Forma: {parada.forma_pagamento}</span>
                                )}
                                <span>Entregue: {formatarData(parada.data_entrega)}</span>
                                {parada.distancia_trecho_real_km != null && (
                                  <span>
                                    Trecho real: {formatarKm(parada.distancia_trecho_real_km)}
                                  </span>
                                )}
                              </div>
                              {(parada.observacoes || parada.observacoes_entrega) && (
                                <div style={{ marginTop: 7, color: "#854d0e", fontSize: 12 }}>
                                  📝 {parada.observacoes || parada.observacoes_entrega}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                      {(!rota.paradas || rota.paradas.length === 0) && (
                        <div style={{ color: "#64748b" }}>
                          Detalhes das paradas não disponíveis.
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
