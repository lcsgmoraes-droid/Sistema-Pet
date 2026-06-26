function MelhorOpcaoExplicacao({ comparativo, item }) {
  if (comparativo.length <= 1) return null;

  return (
    <div
      style={{
        marginTop: "12px",
        padding: "12px",
        backgroundColor: "#ecfdf5",
        borderLeft: "3px solid #10b981",
        borderRadius: "4px",
      }}
    >
      <p style={{ margin: "0 0 6px 0", fontSize: "13px", fontWeight: "600", color: "#065f46" }}>
        Por que esta e a melhor opcao?
      </p>
      <p style={{ margin: "0", fontSize: "13px", color: "#047857", lineHeight: "1.5" }}>
        Apesar de{" "}
        {item.classificacao === "premium" || item.classificacao === "super_premium"
          ? `ter um preco mais alto (R$ ${item.preco.toFixed(2)})`
          : `custar R$ ${item.preco.toFixed(2)}`}
        , esta racao{" "}
        {item.classificacao === "super_premium"
          ? "super premium e muito concentrada em nutrientes"
          : item.classificacao === "premium"
            ? "premium tem melhor densidade nutricional"
            : "tem excelente eficiencia alimentar"}
        , entao seu pet consome apenas <strong>{item.quantidade_diaria_g}g por dia</strong>.
        {comparativo[1] && (
          <>
            {" "}
            Em comparacao, a segunda opcao requer{" "}
            <strong>{comparativo[1].quantidade_diaria_g}g/dia</strong>, resultando em um custo
            diario{" "}
            <strong>
              R$ {(comparativo[1].custo_por_dia - item.custo_por_dia).toFixed(2)} maior
            </strong>{" "}
            (R$ {item.custo_por_dia.toFixed(2)} vs R$ {comparativo[1].custo_por_dia.toFixed(2)}).
          </>
        )}
      </p>
    </div>
  );
}

function ComparativoItem({ comparativo, item, menorCusto, produtoIdSelecionado }) {
  const isSelecionada = produtoIdSelecionado && item.produto_id === parseInt(produtoIdSelecionado);
  const isMelhor = item.custo_por_dia === menorCusto;

  return (
    <div
      className={`comparativo-item ${isMelhor ? "melhor" : ""} ${isSelecionada ? "selecionada" : ""}`}
    >
      {(isSelecionada || isMelhor) && (
        <div className="comparativo-badges">
          {isSelecionada && <span className="badge-selecionada">Selecionada</span>}
          {isMelhor && <span className="badge-melhor">Melhor Custo-Beneficio</span>}
        </div>
      )}

      <div className="item-header">
        <div>
          <h4>{item.produto_nome}</h4>
          <div style={{ display: "flex", gap: "8px", alignItems: "center", marginTop: "4px" }}>
            {item.classificacao && (
              <span className={`badge badge-${item.classificacao}`}>
                {item.classificacao.replace("_", " ")}
              </span>
            )}
            <span
              style={{
                fontSize: "13px",
                color: "#64748b",
                backgroundColor: "#f1f5f9",
                padding: "2px 8px",
                borderRadius: "4px",
              }}
            >
              {item.quantidade_diaria_g}g/dia
            </span>
          </div>
        </div>
        <div className="item-price">R$ {item.preco.toFixed(2)}</div>
      </div>

      <div className="item-stats">
        <div className="stat-small">
          <span className="label">Peso</span>
          <span>{item.peso_embalagem_kg}kg</span>
        </div>
        <div className="stat-small">
          <span className="label">Duracao</span>
          <span>{item.duracao_dias}d</span>
        </div>
        <div className="stat-small highlight">
          <span className="label">Custo/dia</span>
          <span>R$ {item.custo_por_dia.toFixed(2)}</span>
        </div>
        <div className="stat-small">
          <span className="label">Custo/mes</span>
          <span>R$ {item.custo_mensal.toFixed(2)}</span>
        </div>
      </div>

      {isMelhor && <MelhorOpcaoExplicacao comparativo={comparativo} item={item} />}
    </div>
  );
}

export default function CalculadoraRacaoComparativoCard({ comparativo, produtoIdSelecionado }) {
  if (comparativo.length === 0) return null;

  const menorCusto = Math.min(...comparativo.map((racao) => racao.custo_por_dia));

  return (
    <div className="comparativo-card">
      <h2>Comparativo de Racoes ({comparativo.length})</h2>
      <p className="subtitle">Ordenado por melhor custo-beneficio (menor custo diario)</p>

      <div className="comparativo-list">
        {comparativo.map((item) => (
          <ComparativoItem
            key={item.produto_id}
            comparativo={comparativo}
            item={item}
            menorCusto={menorCusto}
            produtoIdSelecionado={produtoIdSelecionado}
          />
        ))}
      </div>
    </div>
  );
}
