export default function EntregadorPadraoSection({ destaqueBloco, entregadores, form, setForm }) {
  return (
    <>
      {/* ── Entregador Padrão ─────────────────────────────────────── */}
      <div
        style={{
          background: "#f8fafc",
          border: "1px solid #e2e8f0",
          borderRadius: 12,
          padding: "20px 24px",
          marginBottom: 16,
          ...destaqueBloco,
        }}
      >
        <h3 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 700, color: "#1e293b" }}>
          👤 Entregador padrão
        </h3>
        <select
          value={form.entregador_padrao_id}
          onChange={(e) => setForm({ ...form, entregador_padrao_id: e.target.value })}
          style={{
            width: "100%",
            padding: "8px 12px",
            borderRadius: 8,
            border: "1px solid #cbd5e1",
            fontSize: 14,
          }}
        >
          <option value="">Nenhum (escolher manualmente)</option>
          {Array.isArray(entregadores) &&
            entregadores.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nome}
              </option>
            ))}
        </select>
        <p style={{ fontSize: 12, color: "#64748b", marginTop: 8, marginBottom: 0 }}>
          Será pré-selecionado ao criar novas rotas de entrega.
        </p>
      </div>
    </>
  );
}
