export default function MetodoDistanciaSection({ destaqueBloco, form, setForm }) {
  return (
    <>
      {/* ── Método de KM ─────────────────────────────────────────── */}
      <div
        style={{
          background: "#f8fafc",
          border: "1px solid #e2e8f0",
          borderRadius: 12,
          padding: "20px 24px",
          marginBottom: 24,
          ...destaqueBloco,
        }}
      >
        <h3 style={{ margin: "0 0 4px", fontSize: 16, fontWeight: 700, color: "#1e293b" }}>
          📏 Como registrar a distância percorrida
        </h3>
        <p style={{ margin: "0 0 16px", fontSize: 13, color: "#64748b" }}>
          Define o que acontece quando o entregador marca uma entrega como concluída.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {/* Opção 1: Automático */}
          <label
            style={{
              display: "flex",
              gap: 14,
              alignItems: "flex-start",
              padding: "14px 16px",
              borderRadius: 10,
              border: `2px solid ${form.metodo_km_entrega === "auto_rota" ? "#2563eb" : "#e2e8f0"}`,
              backgroundColor: form.metodo_km_entrega === "auto_rota" ? "#eff6ff" : "#fff",
              cursor: "pointer",
              transition: "all 0.15s",
            }}
          >
            <input
              type="radio"
              name="metodo_km_entrega"
              value="auto_rota"
              checked={form.metodo_km_entrega === "auto_rota"}
              onChange={(e) => setForm({ ...form, metodo_km_entrega: e.target.value })}
              style={{ marginTop: 4, accentColor: "#2563eb", flexShrink: 0 }}
            />
            <div>
              <div style={{ fontWeight: 700, fontSize: 14, color: "#1e293b", marginBottom: 3 }}>
                ✨ Automático{" "}
                <span
                  style={{
                    background: "#dcfce7",
                    color: "#16a34a",
                    fontSize: 11,
                    fontWeight: 600,
                    padding: "1px 7px",
                    borderRadius: 999,
                    marginLeft: 6,
                  }}
                >
                  Recomendado
                </span>
              </div>
              <div style={{ fontSize: 13, color: "#475569", lineHeight: 1.5 }}>
                Se a rota foi otimizada, o sistema usa a distância calculada automaticamente —{" "}
                <strong>sem precisar de nenhuma ação do entregador</strong>. Se a rota não foi
                otimizada, o sistema pede para o entregador informar o km.
              </div>
              <div style={{ fontSize: 12, color: "#16a34a", fontWeight: 600, marginTop: 5 }}>
                Custo: zero
              </div>
            </div>
          </label>

          {/* Opção 2: Sempre manual */}
          <label
            style={{
              display: "flex",
              gap: 14,
              alignItems: "flex-start",
              padding: "14px 16px",
              borderRadius: 10,
              border: `2px solid ${form.metodo_km_entrega === "manual" ? "#2563eb" : "#e2e8f0"}`,
              backgroundColor: form.metodo_km_entrega === "manual" ? "#eff6ff" : "#fff",
              cursor: "pointer",
              transition: "all 0.15s",
            }}
          >
            <input
              type="radio"
              name="metodo_km_entrega"
              value="manual"
              checked={form.metodo_km_entrega === "manual"}
              onChange={(e) => setForm({ ...form, metodo_km_entrega: e.target.value })}
              style={{ marginTop: 4, accentColor: "#2563eb", flexShrink: 0 }}
            />
            <div>
              <div style={{ fontWeight: 700, fontSize: 14, color: "#1e293b", marginBottom: 3 }}>
                ✏️ Sempre manual
              </div>
              <div style={{ fontSize: 13, color: "#475569", lineHeight: 1.5 }}>
                O entregador digita o km do hodômetro em cada entrega e ao finalizar a rota. Útil
                para quem precisa de controle rigoroso de quilometragem real.
              </div>
              <div style={{ fontSize: 12, color: "#16a34a", fontWeight: 600, marginTop: 5 }}>
                Custo: zero
              </div>
            </div>
          </label>

          {/* Opção 3: App (em breve) */}
          <div
            style={{
              display: "flex",
              gap: 14,
              alignItems: "flex-start",
              padding: "14px 16px",
              borderRadius: 10,
              border: "2px solid #e2e8f0",
              backgroundColor: "#f8fafc",
              opacity: 0.6,
              cursor: "not-allowed",
              position: "relative",
            }}
          >
            <input type="radio" disabled style={{ marginTop: 4, flexShrink: 0 }} />
            <div>
              <div style={{ fontWeight: 700, fontSize: 14, color: "#94a3b8", marginBottom: 3 }}>
                📱 GPS via App Mobile
                <span
                  style={{
                    background: "#fef3c7",
                    color: "#b45309",
                    fontSize: 11,
                    fontWeight: 600,
                    padding: "1px 7px",
                    borderRadius: 999,
                    marginLeft: 6,
                  }}
                >
                  Em breve
                </span>
              </div>
              <div style={{ fontSize: 13, color: "#94a3b8", lineHeight: 1.5 }}>
                O entregador usa o app no celular para rastrear toda a rota em tempo real via GPS —
                mesmo com a tela apagada. Distância real calculada automaticamente sem nenhuma ação
                manual.
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
