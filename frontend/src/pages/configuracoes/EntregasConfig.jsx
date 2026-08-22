import { useEffect, useState } from "react";
import CurrencyInput from "../../components/CurrencyInput";
import { api } from "../../services/api";
import { formatMoneyBRL } from "../../utils/formatters";
import { getGuiaInlineStyle } from "../../utils/guiaHighlight";

const fieldStyle = {
  width: "100%",
  padding: "10px 12px",
  border: "1px solid #d1d5db",
  borderRadius: 8,
  fontSize: 14,
  color: "#111827",
  background: "#fff",
  boxSizing: "border-box",
};

function optionalNumber(value) {
  if (value === "" || value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function optionalPositiveNumber(value) {
  const parsed = optionalNumber(value);
  return parsed !== null && parsed > 0 ? parsed : null;
}

function nextTierLimit(tiers) {
  const lastTier = tiers[tiers.length - 1];
  const lastLimit = Number(lastTier?.ate_km);
  return Number.isFinite(lastLimit) && lastLimit > 0 ? String(lastLimit + 1) : "1";
}

export default function EntregasConfig() {
  const guiaAtiva = new URLSearchParams(window.location.search).get("guia");
  const destacarEntregaConfig = guiaAtiva === "entrega-config";
  const destaqueBloco = getGuiaInlineStyle(destacarEntregaConfig);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [buscandoCep, setBuscandoCep] = useState(false);
  const [entregadores, setEntregadores] = useState([]);
  const [form, setForm] = useState({
    entregador_padrao_id: "",
    ponto_inicial_rota: "",
    cep: "",
    logradouro: "",
    numero: "",
    complemento: "",
    bairro: "",
    cidade: "",
    estado: "",
    metodo_km_entrega: "auto_rota",
    entrega_ativa: true,
    retirada_ativa: true,
    modalidade_cobranca: "fixa",
    taxa_fixa: 0,
    valor_por_km_cobrado: 0,
    taxa_minima: 0,
    faixas_distancia: [],
    valor_km_excedente: 0,
    distancia_maxima_entrega_km: "",
    frete_gratis_acima: 0,
    distancia_maxima_frete_gratis_km: "",
    pedido_minimo: 0,
    prazo_entrega_texto: "",
  });

  useEffect(() => {
    async function load() {
      try {
        const [cfg, pessoas] = await Promise.all([
          api.get("/configuracoes/entregas"),
          api.get("/clientes/", {
            params: {
              is_entregador: true,
              entregador_ativo: true,
            },
          }),
        ]);

        // Agora os campos vêm separados do backend
        setForm({
          entregador_padrao_id: cfg.data.entregador_padrao_id ?? "",
          ponto_inicial_rota: "", // Campo legado (não usado mais)
          cep: cfg.data.cep ?? "",
          logradouro: cfg.data.logradouro ?? "",
          numero: cfg.data.numero ?? "",
          complemento: cfg.data.complemento ?? "",
          bairro: cfg.data.bairro ?? "",
          cidade: cfg.data.cidade ?? "",
          estado: cfg.data.estado ?? "",
          metodo_km_entrega: cfg.data.metodo_km_entrega ?? "auto_rota",
          entrega_ativa: cfg.data.entrega_ativa !== false,
          retirada_ativa: cfg.data.retirada_ativa !== false,
          modalidade_cobranca: cfg.data.modalidade_cobranca ?? "fixa",
          taxa_fixa: Number(cfg.data.taxa_fixa || 0),
          valor_por_km_cobrado: Number(cfg.data.valor_por_km_cobrado || 0),
          taxa_minima: Number(cfg.data.taxa_minima || 0),
          faixas_distancia: Array.isArray(cfg.data.faixas_distancia)
            ? cfg.data.faixas_distancia.map((faixa) => ({
                ate_km: String(faixa.ate_km ?? ""),
                valor: Number(faixa.valor || 0),
              }))
            : [],
          valor_km_excedente: Number(cfg.data.valor_km_excedente || 0),
          distancia_maxima_entrega_km: cfg.data.distancia_maxima_entrega_km ?? "",
          frete_gratis_acima: Number(cfg.data.frete_gratis_acima || 0),
          distancia_maxima_frete_gratis_km: cfg.data.distancia_maxima_frete_gratis_km ?? "",
          pedido_minimo: Number(cfg.data.pedido_minimo || 0),
          prazo_entrega_texto: cfg.data.prazo_entrega_texto ?? "",
        });

        // 🛡️ PROTEÇÃO: Garantir que entregadores seja SEMPRE um array
        const entregadoresList = Array.isArray(pessoas.data)
          ? pessoas.data
          : pessoas.data?.clientes || pessoas.data?.items || [];

        console.log("🚚 Entregadores carregados:", entregadoresList);
        setEntregadores(entregadoresList);
      } catch (e) {
        console.error("❌ Erro ao carregar configurações:", e);
        alert("Erro ao carregar configurações de entrega");
        // 🛡️ Garantir array vazio em caso de erro
        setEntregadores([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function buscarCep() {
    const cep = form.cep.replace(/\D/g, "");

    if (cep.length !== 8) {
      alert("CEP inválido. Digite 8 dígitos.");
      return;
    }

    setBuscandoCep(true);
    try {
      const response = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
      const data = await response.json();

      if (data.erro) {
        alert("CEP não encontrado");
        return;
      }

      setForm({
        ...form,
        logradouro: data.logradouro || "",
        bairro: data.bairro || "",
        cidade: data.localidade || "",
        estado: data.uf || "",
      });
    } catch (e) {
      console.error(e);
      alert("Erro ao buscar CEP");
    } finally {
      setBuscandoCep(false);
    }
  }

  function changeBillingMode(modalidade) {
    setForm((current) => ({
      ...current,
      modalidade_cobranca: modalidade,
      faixas_distancia:
        modalidade === "por_faixa" && current.faixas_distancia.length === 0
          ? [{ ate_km: "1", valor: 0 }]
          : current.faixas_distancia,
    }));
  }

  function updateDistanceTier(index, field, value) {
    setForm((current) => ({
      ...current,
      faixas_distancia: current.faixas_distancia.map((tier, tierIndex) =>
        tierIndex === index ? { ...tier, [field]: value } : tier,
      ),
    }));
  }

  function addDistanceTier() {
    setForm((current) => ({
      ...current,
      faixas_distancia: [
        ...current.faixas_distancia,
        { ate_km: nextTierLimit(current.faixas_distancia), valor: 0 },
      ],
    }));
  }

  function removeDistanceTier(index) {
    setForm((current) => ({
      ...current,
      faixas_distancia: current.faixas_distancia.filter((_tier, tierIndex) => tierIndex !== index),
    }));
  }

  async function handleSave(e) {
    e.preventDefault();
    if (form.modalidade_cobranca === "por_km" && Number(form.valor_por_km_cobrado || 0) <= 0) {
      alert("Informe um valor por km maior que zero.");
      return;
    }
    const distancePricing = ["por_km", "por_faixa"].includes(form.modalidade_cobranca);
    if (distancePricing && (!form.logradouro || !form.numero)) {
      alert("Para cobrar por distância, complete pelo menos logradouro e número da loja.");
      return;
    }
    const distanceTiers = form.faixas_distancia.map((tier) => ({
      ate_km: Number(tier.ate_km),
      valor: Number(tier.valor),
    }));
    if (form.modalidade_cobranca === "por_faixa") {
      if (
        distanceTiers.length === 0 ||
        distanceTiers.some(
          (tier) =>
            !Number.isFinite(tier.ate_km) ||
            tier.ate_km <= 0 ||
            !Number.isFinite(tier.valor) ||
            tier.valor < 0,
        )
      ) {
        alert("Preencha todas as faixas com uma distância maior que zero e um preço válido.");
        return;
      }
      if (
        distanceTiers.some(
          (tier, index) => index > 0 && tier.ate_km <= distanceTiers[index - 1].ate_km,
        )
      ) {
        alert("Organize as faixas em ordem crescente, sem repetir a distância.");
        return;
      }
    }
    setSaving(true);
    try {
      // Enviar campos separados para o backend
      await api.put("/configuracoes/entregas", {
        entregador_padrao_id: form.entregador_padrao_id || null,
        cep: form.cep || null,
        logradouro: form.logradouro || null,
        numero: form.numero || null,
        complemento: form.complemento || null,
        bairro: form.bairro || null,
        cidade: form.cidade || null,
        estado: form.estado || null,
        metodo_km_entrega: form.metodo_km_entrega || "auto_rota",
        entrega_ativa: form.entrega_ativa,
        retirada_ativa: form.retirada_ativa,
        modalidade_cobranca: form.modalidade_cobranca,
        taxa_fixa: Number(form.taxa_fixa || 0),
        valor_por_km_cobrado:
          form.modalidade_cobranca === "por_km" ? Number(form.valor_por_km_cobrado || 0) : null,
        taxa_minima: Number(form.taxa_minima || 0),
        faixas_distancia: distanceTiers,
        valor_km_excedente: optionalPositiveNumber(form.valor_km_excedente),
        distancia_maxima_entrega_km: optionalPositiveNumber(form.distancia_maxima_entrega_km),
        frete_gratis_acima: optionalPositiveNumber(form.frete_gratis_acima),
        distancia_maxima_frete_gratis_km: optionalPositiveNumber(
          form.distancia_maxima_frete_gratis_km,
        ),
        pedido_minimo: Number(form.pedido_minimo || 0),
        prazo_entrega_texto: form.prazo_entrega_texto.trim() || null,
      });
      alert("Configurações salvas com sucesso");
    } catch (e) {
      console.error(e);
      alert("Erro ao salvar configurações");
    } finally {
      setSaving(false);
    }
  }

  if (loading)
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: 200,
          color: "#64748b",
        }}
      >
        Carregando configurações...
      </div>
    );

  return (
    <div className="page">
      {destacarEntregaConfig && (
        <div
          style={{
            marginBottom: 16,
            border: "1px solid #f59e0b",
            background: "#fffbeb",
            color: "#92400e",
            borderRadius: 10,
            padding: "10px 14px",
            fontSize: 14,
          }}
        >
          Etapa da introducao guiada: revise entregador padrao, endereco de partida e metodo de km.
          Depois clique em <strong>Salvar Configuracoes</strong>.
        </div>
      )}

      <div style={{ marginBottom: 28 }}>
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: "#1e293b" }}>
          🚚 Configurações de Entregas
        </h1>
        <p style={{ margin: "6px 0 0", fontSize: 14, color: "#64748b" }}>
          Uma única regra de entrega para o aplicativo e para o e-commerce.
        </p>
      </div>

      <form onSubmit={handleSave} style={{ maxWidth: 760 }}>
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
          <div
            style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 12, marginBottom: 16 }}
          >
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
          <div
            style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 12, marginBottom: 4 }}
          >
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

          <div
            style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 18 }}
          >
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
                    O sistema escolhe a primeira faixa que comporta a distância calculada. Ex.: até
                    2 km por R$ 8,49 também atende rotas de 1,4 km.
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
            gratuidade, o frete normal continua sendo cobrado. Acima da distância máxima de entrega,
            o checkout informa que o endereço está fora da área atendida.
          </div>
        </div>

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
                  O entregador usa o app no celular para rastrear toda a rota em tempo real via GPS
                  — mesmo com a tela apagada. Distância real calculada automaticamente sem nenhuma
                  ação manual.
                </div>
              </div>
            </div>
          </div>
        </div>

        <button
          type="submit"
          disabled={saving}
          style={{
            backgroundColor: destacarEntregaConfig ? "#d97706" : "#2563eb",
            color: "white",
            padding: "12px 24px",
            border: "none",
            borderRadius: "6px",
            fontSize: "16px",
            fontWeight: "500",
            cursor: saving ? "not-allowed" : "pointer",
            opacity: saving ? 0.6 : 1,
            transition: "all 0.2s",
            boxShadow: destaqueBloco.boxShadow || "none",
          }}
          onMouseOver={(e) => {
            if (!saving)
              e.target.style.backgroundColor = destacarEntregaConfig ? "#b45309" : "#1d4ed8";
          }}
          onMouseOut={(e) => {
            if (!saving)
              e.target.style.backgroundColor = destacarEntregaConfig ? "#d97706" : "#2563eb";
          }}
        >
          {saving ? "Salvando..." : "Salvar Configurações"}
        </button>
      </form>
    </div>
  );
}
