export default function CalculadoraRacaoResultadoCard({ resultado }) {
  if (!resultado) return null;

  return (
    <div className="result-card">
      <h2>Resultado do Calculo</h2>
      <div className="result-header">
        <h3>{resultado.produto_nome}</h3>
        {resultado.classificacao && (
          <span className={`badge badge-${resultado.classificacao}`}>
            {resultado.classificacao.replace("_", " ")}
          </span>
        )}
      </div>

      <div className="result-stats">
        <div className="stat">
          <span className="label">Peso Embalagem</span>
          <span className="value">{resultado.peso_embalagem_kg} kg</span>
        </div>
        <div className="stat">
          <span className="label">Preco</span>
          <span className="value">R$ {resultado.preco.toFixed(2)}</span>
        </div>
      </div>

      <div className="result-details">
        <div className="detail-item">
          <span className="icon">D</span>
          <div>
            <strong>Duracao</strong>
            <p>
              {resultado.duracao_dias} dias ({resultado.duracao_meses} meses)
            </p>
          </div>
        </div>
        <div className="detail-item">
          <span className="icon">G</span>
          <div>
            <strong>Consumo diario</strong>
            <p>{resultado.quantidade_diaria_g}g</p>
          </div>
        </div>
        <div className="detail-item">
          <span className="icon">KG</span>
          <div>
            <strong>Custo/kg</strong>
            <p>R$ {resultado.custo_por_kg.toFixed(2)}</p>
          </div>
        </div>
        <div className="detail-item">
          <span className="icon">D</span>
          <div>
            <strong>Custo/dia</strong>
            <p>R$ {resultado.custo_por_dia.toFixed(2)}</p>
          </div>
        </div>
        <div className="detail-item">
          <span className="icon">M</span>
          <div>
            <strong>Custo mensal</strong>
            <p>R$ {resultado.custo_mensal.toFixed(2)}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
