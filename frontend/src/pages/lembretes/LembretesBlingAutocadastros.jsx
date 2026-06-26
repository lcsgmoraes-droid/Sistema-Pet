import { formatarDataHora } from "./lembretesFormatters";

export default function LembretesBlingAutocadastros({ autocadastrosBling, onAbrirProduto }) {
  if (autocadastrosBling.total <= 0) return null;

  return (
    <div
      style={{
        marginBottom: "20px",
        borderRadius: "12px",
        border: "1px solid #86efac",
        overflow: "hidden",
        background: "#fff",
      }}
    >
      <div
        style={{
          background: "#dcfce7",
          padding: "12px 20px",
          borderBottom: "1px solid #86efac",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "10px",
          flexWrap: "wrap",
        }}
      >
        <span style={{ fontWeight: "700", color: "#166534", fontSize: "14px" }}>
          Auto cadastro Bling (ultimas 24h)
        </span>
        <span style={{ fontWeight: "700", color: "#166534", fontSize: "14px" }}>
          {autocadastrosBling.total}
        </span>
      </div>
      <div style={{ padding: "12px 20px" }}>
        <p style={{ margin: "0 0 8px", color: "#065f46", fontSize: "13px" }}>
          O sistema ja identificou SKU sem cadastro, criou o produto e seguiu com a baixa
          automaticamente. Este aviso some sozinho apos 1 dia.
        </p>
        <div style={{ display: "grid", gap: "6px" }}>
          {autocadastrosBling.items.slice(0, 8).map((item) => (
            <button
              key={item.produto_id}
              type="button"
              style={{
                width: "100%",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                background: "#f0fdf4",
                border: "1px solid #bbf7d0",
                borderRadius: "8px",
                padding: "8px 10px",
                cursor: "pointer",
                textAlign: "left",
              }}
              onClick={() => onAbrirProduto(item)}
            >
              <span style={{ fontSize: "13px", color: "#14532d" }}>
                {item.codigo} - {item.nome}
              </span>
              <span style={{ fontSize: "12px", color: "#166534" }}>
                {formatarDataHora(item.created_at)}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
