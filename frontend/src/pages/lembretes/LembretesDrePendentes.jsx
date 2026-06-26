export default function LembretesDrePendentes({ dresPendentes, onAbrirDre }) {
  if (dresPendentes <= 0) return null;

  return (
    <div
      style={{
        marginBottom: "20px",
        borderRadius: "12px",
        border: "1px solid #c4b5fd",
        overflow: "hidden",
        background: "#fff",
      }}
    >
      <div
        style={{
          background: "#ede9fe",
          padding: "12px 20px",
          borderBottom: "1px solid #c4b5fd",
          display: "flex",
          alignItems: "center",
          gap: "8px",
        }}
      >
        <span style={{ fontSize: "16px" }}>#</span>
        <span style={{ fontWeight: "600", color: "#5b21b6", fontSize: "14px" }}>
          DRE - Lancamentos pendentes de classificacao
        </span>
      </div>
      <div
        style={{
          padding: "14px 20px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "16px",
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <p style={{ fontWeight: "700", color: "#7c3aed", fontSize: "28px", margin: 0 }}>
            {dresPendentes}
          </p>
          <p style={{ color: "#4b5563", fontSize: "13px", margin: 0 }}>
            lancamento{dresPendentes !== 1 ? "s" : ""} sem categoria DRE.
            <br />O DRE pode estar incompleto ou incorreto.
          </p>
        </div>
        <button
          type="button"
          onClick={onAbrirDre}
          style={{
            background: "linear-gradient(to right, #7c3aed, #4f46e5)",
            color: "#fff",
            border: "none",
            borderRadius: "8px",
            padding: "8px 18px",
            fontWeight: "600",
            fontSize: "13px",
            cursor: "pointer",
            whiteSpace: "nowrap",
          }}
        >
          Ir para o DRE e Classificar
        </button>
      </div>
    </div>
  );
}
