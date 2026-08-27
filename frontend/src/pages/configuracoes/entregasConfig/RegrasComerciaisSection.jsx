import CurrencyInput from "../../../components/CurrencyInput";
import { formatMoneyBRL } from "../../../utils/formatters";
import { fieldStyle } from "./entregasConfigUtils";

export default function RegrasComerciaisSection({
  addDistanceTier,
  changeBillingMode,
  form,
  removeDistanceTier,
  setForm,
  updateDistanceTier,
}) {
  return (
    <>
      {/* ── Regras comerciais compartilhadas ────────────────────── */}
      <div
        style={{
          background: "#f8fafc",
          border: "1px solid #e2e8f0",
          borderRadius: 12,
          padding: "20px 24px",
          marginBottom: 24,
        }}
      >
        <h3 style={{ margin: "0 0 4px", fontSize: 16, fontWeight: 700, color: "#1e293b" }}>
          💰 Preço e área de entrega
        </h3>
        <p style={{ margin: "0 0 18px", fontSize: 13, color: "#64748b", lineHeight: 1.5 }}>
          Esta regra é usada igualmente no aplicativo e no e-commerce. A distância é a rota de ida
          entre a loja e o cliente.
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 18 }}>
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "12px 14px",
              border: "1px solid #dbeafe",
              borderRadius: 9,
              background: "#eff6ff",
              fontSize: 14,
              fontWeight: 600,
              color: "#1e3a8a",
            }}
          >
            <input
              type="checkbox"
              checked={form.entrega_ativa}
              onChange={(event) => setForm({ ...form, entrega_ativa: event.target.checked })}
            />
            Oferecer entrega
          </label>
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "12px 14px",
              border: "1px solid #dbeafe",
              borderRadius: 9,
              background: "#eff6ff",
              fontSize: 14,
              fontWeight: 600,
              color: "#1e3a8a",
            }}
          >
            <input
              type="checkbox"
              checked={form.retirada_ativa}
              onChange={(event) => setForm({ ...form, retirada_ativa: event.target.checked })}
            />
            Oferecer retirada na loja
          </label>
        </div>

        <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#374151" }}>
          Como cobrar o frete
          <select
            value={form.modalidade_cobranca}
            onChange={(event) => changeBillingMode(event.target.value)}
            style={{ ...fieldStyle, marginTop: 6 }}
          >
            <option value="fixa">Taxa fixa</option>
            <option value="por_km">Distância × preço por km</option>
            <option value="por_faixa">Preço fixo por faixa de distância</option>
          </select>
        </label>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
            gap: 12,
            marginTop: 14,
          }}
        >
          {form.modalidade_cobranca === "fixa" && (
            <label style={{ fontSize: 13, fontWeight: 600, color: "#374151" }}>
              Taxa fixa (R$)
              <CurrencyInput
                value={form.taxa_fixa}
                onChange={(value) => setForm({ ...form, taxa_fixa: value })}
                aria-label="Taxa fixa"
                style={{ ...fieldStyle, marginTop: 6 }}
              />
            </label>
          )}

          {form.modalidade_cobranca === "por_km" && (
            <>
              <label style={{ fontSize: 13, fontWeight: 600, color: "#374151" }}>
                Preço por km (R$)
                <CurrencyInput
                  value={form.valor_por_km_cobrado}
                  onChange={(value) => setForm({ ...form, valor_por_km_cobrado: value })}
                  aria-label="Preço por km"
                  style={{ ...fieldStyle, marginTop: 6 }}
                  required
                />
              </label>
              <label style={{ fontSize: 13, fontWeight: 600, color: "#374151" }}>
                Taxa mínima (R$)
                <CurrencyInput
                  value={form.taxa_minima}
                  onChange={(value) => setForm({ ...form, taxa_minima: value })}
                  aria-label="Taxa mínima"
                  style={{ ...fieldStyle, marginTop: 6 }}
                />
              </label>
            </>
          )}

          {form.modalidade_cobranca === "por_faixa" && (
            <div
              style={{
                gridColumn: "1 / -1",
                border: "1px solid #bfdbfe",
                borderRadius: 10,
                background: "#eff6ff",
                padding: 14,
              }}
            >
              <div style={{ marginBottom: 12 }}>
                <strong style={{ display: "block", color: "#1e3a8a", fontSize: 14 }}>
                  Faixas com preço fechado
                </strong>
                <span style={{ color: "#475569", fontSize: 12, lineHeight: 1.5 }}>
                  O sistema escolhe a primeira faixa que comporta a distância calculada. Ex.: até 2
                  km por R$ 8,49 também atende rotas de 1,4 km.
                </span>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {form.faixas_distancia.map((tier, index) => (
                  <div
                    key={`distance-tier-${index}`}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "64px minmax(100px, 1fr) minmax(150px, 1.4fr) auto",
                      gap: 10,
                      alignItems: "end",
                      padding: 10,
                      background: "#fff",
                      border: "1px solid #dbeafe",
                      borderRadius: 8,
                    }}
                  >
                    <strong style={{ alignSelf: "center", color: "#1d4ed8", fontSize: 12 }}>
                      Faixa {index + 1}
                    </strong>
                    <label style={{ fontSize: 12, fontWeight: 600, color: "#374151" }}>
                      Até (km)
                      <input
                        type="number"
                        min="0.01"
                        step="0.01"
                        value={tier.ate_km}
                        onChange={(event) =>
                          updateDistanceTier(index, "ate_km", event.target.value)
                        }
                        aria-label={`Distância máxima da faixa ${index + 1}`}
                        style={{ ...fieldStyle, marginTop: 5 }}
                      />
                    </label>
                    <label style={{ fontSize: 12, fontWeight: 600, color: "#374151" }}>
                      Preço fechado (R$)
                      <CurrencyInput
                        value={tier.valor}
                        onChange={(value) => updateDistanceTier(index, "valor", value)}
                        aria-label={`Preço da faixa ${index + 1}`}
                        style={{ ...fieldStyle, marginTop: 5 }}
                      />
                    </label>
                    <button
                      type="button"
                      onClick={() => removeDistanceTier(index)}
                      aria-label={`Remover faixa ${index + 1}`}
                      title="Remover faixa"
                      style={{
                        height: 40,
                        width: 40,
                        border: "1px solid #fecaca",
                        borderRadius: 8,
                        background: "#fff1f2",
                        color: "#be123c",
                        cursor: "pointer",
                        fontSize: 18,
                      }}
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>

              <button
                type="button"
                onClick={addDistanceTier}
                disabled={form.faixas_distancia.length >= 50}
                style={{
                  marginTop: 10,
                  border: "1px solid #93c5fd",
                  borderRadius: 8,
                  padding: "8px 12px",
                  background: "#fff",
                  color: "#1d4ed8",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                + Adicionar faixa
              </button>

              <label
                style={{
                  display: "block",
                  marginTop: 14,
                  fontSize: 13,
                  fontWeight: 600,
                  color: "#374151",
                }}
              >
                Adicional por km iniciado acima da última faixa (R$)
                <CurrencyInput
                  value={form.valor_km_excedente}
                  onChange={(value) => setForm({ ...form, valor_km_excedente: value })}
                  aria-label="Adicional por km acima da última faixa"
                  style={{ ...fieldStyle, marginTop: 6, maxWidth: 320 }}
                />
              </label>
              <p style={{ margin: "8px 0 0", color: "#475569", fontSize: 12 }}>
                {Number(form.valor_km_excedente || 0) > 0
                  ? `Após a última faixa, cada km adicional iniciado soma ${formatMoneyBRL(form.valor_km_excedente)}.`
                  : "Com adicional em R$ 0,00, endereços acima da última faixa não serão atendidos."}
              </p>
            </div>
          )}

          <label style={{ fontSize: 13, fontWeight: 600, color: "#374151" }}>
            Distância máxima de entrega (km)
            <input
              type="number"
              min="0.01"
              step="0.01"
              value={form.distancia_maxima_entrega_km}
              onChange={(event) =>
                setForm({ ...form, distancia_maxima_entrega_km: event.target.value })
              }
              placeholder="Sem limite"
              style={{ ...fieldStyle, marginTop: 6 }}
            />
          </label>
          <label style={{ fontSize: 13, fontWeight: 600, color: "#374151" }}>
            Pedido mínimo (R$)
            <CurrencyInput
              value={form.pedido_minimo}
              onChange={(value) => setForm({ ...form, pedido_minimo: value })}
              aria-label="Pedido mínimo"
              style={{ ...fieldStyle, marginTop: 6 }}
            />
          </label>
          <label style={{ fontSize: 13, fontWeight: 600, color: "#374151" }}>
            Frete grátis acima de (R$)
            <CurrencyInput
              value={form.frete_gratis_acima}
              onChange={(value) => setForm({ ...form, frete_gratis_acima: value })}
              aria-label="Frete grátis acima de"
              style={{ ...fieldStyle, marginTop: 6 }}
            />
            <span style={{ display: "block", marginTop: 4, color: "#64748b", fontSize: 11 }}>
              Use R$ 0,00 para não oferecer.
            </span>
          </label>
          <label style={{ fontSize: 13, fontWeight: 600, color: "#374151" }}>
            Frete grátis somente até (km)
            <input
              type="number"
              min="0.01"
              step="0.01"
              value={form.distancia_maxima_frete_gratis_km}
              onChange={(event) =>
                setForm({ ...form, distancia_maxima_frete_gratis_km: event.target.value })
              }
              disabled={!form.frete_gratis_acima}
              placeholder="Sem limite próprio"
              style={{
                ...fieldStyle,
                marginTop: 6,
                background: form.frete_gratis_acima ? "#fff" : "#f1f5f9",
              }}
            />
          </label>
        </div>

        <label
          style={{
            display: "block",
            marginTop: 14,
            fontSize: 13,
            fontWeight: 600,
            color: "#374151",
          }}
        >
          Prazo informado ao cliente
          <input
            type="text"
            maxLength={120}
            value={form.prazo_entrega_texto}
            onChange={(event) => setForm({ ...form, prazo_entrega_texto: event.target.value })}
            placeholder="Ex.: Entrega em até 2 horas"
            style={{ ...fieldStyle, marginTop: 6 }}
          />
        </label>

        <div
          style={{
            marginTop: 14,
            padding: "10px 12px",
            borderRadius: 8,
            background: "#fff7ed",
            color: "#9a3412",
            fontSize: 12,
            lineHeight: 1.5,
          }}
        >
          Se o pedido atingir o valor de frete grátis, mas estiver além do limite de km da
          gratuidade, o frete normal continua sendo cobrado. Acima da distância máxima de entrega, o
          checkout informa que o endereço está fora da área atendida.
        </div>
      </div>
    </>
  );
}
