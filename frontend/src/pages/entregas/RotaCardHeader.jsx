import { formatBRL } from "../../utils/formatters";

function formatarKm(valor) {
  const numero = Number(valor);
  return Number.isFinite(numero) ? `${formatBRL(numero)} km` : null;
}

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
  onAbrirRastreio,
  onExcluirRota,
  getStatusColor,
  getStatusLabel,
}) {
  const emRota = rota.status === "em_rota" || rota.status === "em_andamento";
  const proximaParada = paradasOrdenadas.find((parada) => parada.status !== "entregue");
  const kmInicial = Number(rota.km_inicial);
  const kmFinal = Number(rota.km_final);
  const temKmInicial = rota.km_inicial != null && Number.isFinite(kmInicial);
  const temKmFinal = rota.km_final != null && Number.isFinite(kmFinal);
  const metricas = [
    ["Distância prevista", rota.distancia_prevista && formatarKm(rota.distancia_prevista)],
    [
      "Distância real (GPS)",
      rota.distancia_total_km_real && formatarKm(rota.distancia_total_km_real),
    ],
    [
      "Até a última entrega",
      rota.distancia_ate_ultima_entrega_km_real &&
        formatarKm(rota.distancia_ate_ultima_entrega_km_real),
    ],
    ["Retorno vazio", rota.distancia_retorno_km_real && formatarKm(rota.distancia_retorno_km_real)],
    ["Tempo estimado", tempoEstimado && formatarTempo(tempoEstimado)],
    ["KM inicial", temKmInicial && formatarKm(kmInicial)],
    ["KM final", temKmFinal && formatarKm(kmFinal)],
    [
      "Total rodado",
      temKmInicial && temKmFinal && kmFinal >= kmInicial && formatarKm(kmFinal - kmInicial),
    ],
  ].filter(([, valor]) => Boolean(valor));

  return (
    <div className="rota-card-cabecalho">
      <div className="rota-card-linha-principal">
        <button
          type="button"
          className="rota-card-resumo"
          onClick={onToggleExpand}
          aria-expanded={expandida}
          aria-label={`${expandida ? "Recolher" : "Abrir"} detalhes da rota ${rota.numero || rota.id}`}
        >
          <span className="rota-card-titulo">
            🚚 {rota.numero || `Rota #${rota.id}`}
            <span aria-hidden="true">{expandida ? "▾" : "▸"}</span>
          </span>
          <span className="rota-card-linha-info">
            <span>{rota.entregador?.nome || "Entregador não informado"}</span>
            <span>·</span>
            <span>{rota.paradas?.length || 0} entrega(s)</span>
            <span>·</span>
            <span>Criada em {new Date(rota.created_at).toLocaleString("pt-BR")}</span>
          </span>
          {proximaParada && emRota && (
            <span className="rota-card-proxima">
              Próxima:{" "}
              {proximaParada.cliente_nome || proximaParada.numero_venda || proximaParada.endereco}
            </span>
          )}
        </button>
        <span className="rota-card-status" style={{ backgroundColor: getStatusColor(rota.status) }}>
          {getStatusLabel(rota.status)}
        </span>
      </div>

      <div className="rota-card-acoes">
        {emRota && (
          <button
            type="button"
            className="rota-card-acao rota-card-acao-rastreio"
            onClick={() => onAbrirRastreio(rota)}
          >
            📡 Ver rastreio
          </button>
        )}
        {rota.status === "pendente" && (
          <button
            type="button"
            className="rota-card-acao rota-card-acao-iniciar"
            onClick={() => onIniciarRota(rota.id)}
          >
            🚀 Iniciar rota
          </button>
        )}
        {emRota && todasEntregue && (
          <button
            type="button"
            className="rota-card-acao rota-card-acao-finalizar"
            disabled={processandoFinalizacao}
            onClick={() => finalizarRota(rota.id, rota.km_inicial)}
          >
            {processandoFinalizacao ? "⏳ Processando..." : "✅ Finalizar rota"}
          </button>
        )}
        {emRota && paradasPendentes === paradasOrdenadas.length && (
          <button
            type="button"
            className="rota-card-acao rota-card-acao-secundaria"
            onClick={() => onReverterInicio(rota.id)}
          >
            ↩️ Reverter início
          </button>
        )}
        {(rota.status === "pendente" || emRota) && (
          <button
            type="button"
            className="rota-card-acao rota-card-acao-excluir"
            onClick={() => onExcluirRota(rota.id)}
          >
            🗑️ Excluir
          </button>
        )}
      </div>

      {expandida && (
        <div className="rota-card-detalhes">
          {metricas.map(([rotulo, valor]) => (
            <div key={rotulo}>
              <strong>{rotulo}:</strong> {valor}
            </div>
          ))}
          {rota.data_conclusao && (
            <div>
              <strong>Concluída em:</strong> {new Date(rota.data_conclusao).toLocaleString("pt-BR")}
            </div>
          )}
          {rota.observacoes && (
            <div className="rota-card-observacoes">
              <strong>Observações:</strong> {rota.observacoes}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default RotaCardHeader;
