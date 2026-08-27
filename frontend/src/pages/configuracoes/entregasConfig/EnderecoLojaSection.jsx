export default function EnderecoLojaSection({
  buscandoCep,
  buscarCep,
  destaqueBloco,
  form,
  setForm,
}) {
  return (
    <>
      {/* ── Ponto Inicial ─────────────────────────────────────────── */}
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
        <h3 style={{ margin: "0 0 4px", fontSize: 16, fontWeight: 700, color: "#1e293b" }}>
          📍 Ponto inicial da rota
        </h3>
        <p style={{ margin: "0 0 20px", fontSize: 13, color: "#64748b" }}>
          Endereço usado como ponto de partida ao calcular rotas.
        </p>

        {/* CEP com busca */}
        <div style={{ marginBottom: 16 }}>
          <label
            htmlFor="cep"
            style={{
              display: "block",
              fontSize: 13,
              fontWeight: 600,
              color: "#374151",
              marginBottom: 6,
            }}
          >
            CEP *
          </label>
          <div style={{ display: "flex", gap: 10 }}>
            <input
              id="cep"
              type="text"
              value={form.cep.replace(/(\d{5})(\d)/, "$1-$2")}
              onChange={(e) => {
                const valor = e.target.value.replace(/\D/g, "");
                setForm({ ...form, cep: valor.slice(0, 8) });
              }}
              placeholder="00000-000"
              maxLength={9}
              style={{
                flex: 1,
                padding: "10px 14px",
                border: "1px solid #d1d5db",
                borderRadius: 8,
                fontSize: 14,
                color: "#111827",
                outline: "none",
                background: "#fff",
              }}
            />
            <button
              type="button"
              onClick={buscarCep}
              disabled={buscandoCep || form.cep.length < 8}
              style={{
                padding: "10px 20px",
                display: "flex",
                alignItems: "center",
                gap: 6,
                background: buscandoCep || form.cep.length < 8 ? "#e5e7eb" : "#2563eb",
                color: buscandoCep || form.cep.length < 8 ? "#9ca3af" : "#fff",
                border: "none",
                borderRadius: 8,
                fontSize: 13,
                fontWeight: 600,
                cursor: buscandoCep || form.cep.length < 8 ? "not-allowed" : "pointer",
                whiteSpace: "nowrap",
              }}
            >
              🔍 {buscandoCep ? "Buscando..." : "Buscar CEP"}
            </button>
          </div>
          <p style={{ fontSize: 12, color: "#6b7280", marginTop: 5, marginBottom: 0 }}>
            Digite o CEP e clique em Buscar para preencher automaticamente.
          </p>
        </div>

        {/* Logradouro */}
        <div style={{ marginBottom: 16 }}>
          <label
            htmlFor="logradouro"
            style={{
              display: "block",
              fontSize: 13,
              fontWeight: 600,
              color: "#374151",
              marginBottom: 6,
            }}
          >
            Logradouro *
          </label>
          <input
            id="logradouro"
            type="text"
            value={form.logradouro}
            onChange={(e) => setForm({ ...form, logradouro: e.target.value })}
            placeholder="Ex: Rua das Flores"
            style={{
              width: "100%",
              padding: "10px 14px",
              border: "1px solid #d1d5db",
              borderRadius: 8,
              fontSize: 14,
              color: "#111827",
              outline: "none",
              background: "#fff",
              boxSizing: "border-box",
            }}
          />
        </div>

        {/* Número e Complemento */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 12, marginBottom: 16 }}>
          <div>
            <label
              htmlFor="numero"
              style={{
                display: "block",
                fontSize: 13,
                fontWeight: 600,
                color: "#374151",
                marginBottom: 6,
              }}
            >
              Número *
            </label>
            <input
              id="numero"
              type="text"
              value={form.numero}
              onChange={(e) => setForm({ ...form, numero: e.target.value })}
              placeholder="123"
              style={{
                width: "100%",
                padding: "10px 14px",
                border: "1px solid #d1d5db",
                borderRadius: 8,
                fontSize: 14,
                color: "#111827",
                outline: "none",
                background: "#fff",
                boxSizing: "border-box",
              }}
            />
          </div>
          <div>
            <label
              htmlFor="complemento"
              style={{
                display: "block",
                fontSize: 13,
                fontWeight: 600,
                color: "#374151",
                marginBottom: 6,
              }}
            >
              Complemento <span style={{ fontWeight: 400, color: "#9ca3af" }}>(opcional)</span>
            </label>
            <input
              id="complemento"
              type="text"
              value={form.complemento}
              onChange={(e) => setForm({ ...form, complemento: e.target.value })}
              placeholder="Ex: Loja 1, Sala 2"
              style={{
                width: "100%",
                padding: "10px 14px",
                border: "1px solid #d1d5db",
                borderRadius: 8,
                fontSize: 14,
                color: "#111827",
                outline: "none",
                background: "#fff",
                boxSizing: "border-box",
              }}
            />
          </div>
        </div>

        {/* Bairro */}
        <div style={{ marginBottom: 16 }}>
          <label
            htmlFor="bairro"
            style={{
              display: "block",
              fontSize: 13,
              fontWeight: 600,
              color: "#374151",
              marginBottom: 6,
            }}
          >
            Bairro *
          </label>
          <input
            id="bairro"
            type="text"
            value={form.bairro}
            onChange={(e) => setForm({ ...form, bairro: e.target.value })}
            placeholder="Ex: Centro"
            style={{
              width: "100%",
              padding: "10px 14px",
              border: "1px solid #d1d5db",
              borderRadius: 8,
              fontSize: 14,
              color: "#111827",
              outline: "none",
              background: "#fff",
              boxSizing: "border-box",
            }}
          />
        </div>

        {/* Cidade e Estado */}
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 12, marginBottom: 4 }}>
          <div>
            <label
              htmlFor="cidade"
              style={{
                display: "block",
                fontSize: 13,
                fontWeight: 600,
                color: "#374151",
                marginBottom: 6,
              }}
            >
              Cidade *
            </label>
            <input
              id="cidade"
              type="text"
              value={form.cidade}
              onChange={(e) => setForm({ ...form, cidade: e.target.value })}
              placeholder="Ex: São Paulo"
              style={{
                width: "100%",
                padding: "10px 14px",
                border: "1px solid #d1d5db",
                borderRadius: 8,
                fontSize: 14,
                color: "#111827",
                outline: "none",
                background: "#fff",
                boxSizing: "border-box",
              }}
            />
          </div>
          <div>
            <label
              htmlFor="estado"
              style={{
                display: "block",
                fontSize: 13,
                fontWeight: 600,
                color: "#374151",
                marginBottom: 6,
              }}
            >
              Estado *
            </label>
            <input
              id="estado"
              type="text"
              value={form.estado}
              onChange={(e) => {
                const valor = e.target.value.toUpperCase().slice(0, 2);
                setForm({ ...form, estado: valor });
              }}
              placeholder="SP"
              maxLength={2}
              style={{
                width: "100%",
                padding: "10px 14px",
                border: "1px solid #d1d5db",
                borderRadius: 8,
                fontSize: 14,
                color: "#111827",
                outline: "none",
                background: "#fff",
                boxSizing: "border-box",
                textTransform: "uppercase",
              }}
            />
          </div>
        </div>

        <div
          style={{
            marginTop: 14,
            padding: "10px 14px",
            background: "#f0f9ff",
            border: "1px solid #bae6fd",
            borderRadius: 8,
            fontSize: 13,
            color: "#0369a1",
          }}
        >
          💡 Preencha o CEP acima para buscar o endereço automaticamente.
        </div>
      </div>
    </>
  );
}
