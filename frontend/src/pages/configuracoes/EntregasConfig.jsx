import { useEffect, useState } from "react";
import { api } from "../../services/api";

export default function EntregasConfig() {
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
  });

  useEffect(() => {
    async function load() {
      try {
        const [cfg, pessoas] = await Promise.all([
          api.get("/configuracoes/entregas"),
          api.get("/clientes/", {
            params: {
              is_entregador: true,
              entregador_ativo: true
            }
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
        });

        // 🛡️ PROTEÇÃO: Garantir que entregadores seja SEMPRE um array
        const entregadoresList = Array.isArray(pessoas.data)
          ? pessoas.data
          : (pessoas.data?.clientes || pessoas.data?.items || []);

        console.log('🚚 Entregadores carregados:', entregadoresList);
        setEntregadores(entregadoresList);
      } catch (e) {
        console.error('❌ Erro ao carregar configurações:', e);
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

  async function handleSave(e) {
    e.preventDefault();
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
      });
      alert("Configurações salvas com sucesso");
    } catch (e) {
      console.error(e);
      alert("Erro ao salvar configurações");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 200, color: "#64748b" }}>
      Carregando configurações...
    </div>
  );

  return (
    <div className="page">
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: "#1e293b" }}>🚚 Configurações de Entregas</h1>
        <p style={{ margin: "6px 0 0", fontSize: 14, color: "#64748b" }}>Gerencie entregadores, ponto de partida e como o sistema registra a distância percorrida.</p>
      </div>

      <form onSubmit={handleSave} style={{ maxWidth: 640 }}>

        {/* ── Entregador Padrão ─────────────────────────────────────── */}
        <div style={{
          background: "#f8fafc",
          border: "1px solid #e2e8f0",
          borderRadius: 12,
          padding: "20px 24px",
          marginBottom: 16,
        }}>
          <h3 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 700, color: "#1e293b" }}>👤 Entregador padrão</h3>
          <select
            value={form.entregador_padrao_id}
            onChange={(e) => setForm({ ...form, entregador_padrao_id: e.target.value })}
            style={{ width: "100%", padding: "8px 12px", borderRadius: 8, border: "1px solid #cbd5e1", fontSize: 14 }}
          >
            <option value="">Nenhum (escolher manualmente)</option>
            {Array.isArray(entregadores) && entregadores.map((p) => (
              <option key={p.id} value={p.id}>{p.nome}</option>
            ))}
          </select>
          <p style={{ fontSize: 12, color: "#64748b", marginTop: 8, marginBottom: 0 }}>
            Será pré-selecionado ao criar novas rotas de entrega.
          </p>
        </div>

        {/* ── Ponto Inicial ─────────────────────────────────────────── */}
        <div style={{
          background: "#f8fafc",
          border: "1px solid #e2e8f0",
          borderRadius: 12,
          padding: "20px 24px",
          marginBottom: 16,
        }}>
          <h3 style={{ margin: "0 0 4px", fontSize: 16, fontWeight: 700, color: "#1e293b" }}>📍 Ponto inicial da rota</h3>
          <p style={{ margin: "0 0 16px", fontSize: 13, color: "#64748b" }}>Endereço usado como ponto de partida ao calcular rotas.</p>

        {/* CEP com busca */}
        <div className="form-group">
          <label>CEP *</label>
          <div style={{ display: "flex", gap: 10 }}>
            <input
              type="text"
              value={form.cep.replace(/(\d{5})(\d)/, "$1-$2")}
              onChange={(e) => {
                const valor = e.target.value.replace(/\D/g, "");
                setForm({ ...form, cep: valor.slice(0, 8) });
              }}
              placeholder="00000-000"
              maxLength={9}
              style={{ flex: 1 }}
            />
            <button
              type="button"
              onClick={buscarCep}
              disabled={buscandoCep || form.cep.length < 8}
              style={{
                padding: "0 20px",
                display: "flex",
                alignItems: "center",
                gap: 5,
              }}
            >
              {buscandoCep ? (
                "Buscando..."
              ) : (
                <>
                  <span>🔍</span>
                  Buscar
                </>
              )}
            </button>
          </div>
          <p style={{ fontSize: 12, color: "#666", marginTop: 5 }}>
            Digite o CEP e clique em Buscar para preencher automaticamente.
          </p>
        </div>

        {/* Logradouro */}
        <div className="form-group">
          <label>Logradouro (Rua/Avenida) *</label>
          <input
            type="text"
            value={form.logradouro}
            onChange={(e) => setForm({ ...form, logradouro: e.target.value })}
            placeholder="Ex: Rua das Flores"
          />
        </div>

        {/* Número e Complemento */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 15 }}>
          <div className="form-group">
            <label>Número *</label>
            <input
              type="text"
              value={form.numero}
              onChange={(e) => setForm({ ...form, numero: e.target.value })}
              placeholder="123"
            />
          </div>

          <div className="form-group">
            <label>Complemento</label>
            <input
              type="text"
              value={form.complemento}
              onChange={(e) => setForm({ ...form, complemento: e.target.value })}
              placeholder="Ex: Loja 1"
            />
          </div>
        </div>

        {/* Bairro */}
        <div className="form-group">
          <label>Bairro *</label>
          <input
            type="text"
            value={form.bairro}
            onChange={(e) => setForm({ ...form, bairro: e.target.value })}
            placeholder="Ex: Centro"
          />
        </div>

        {/* Cidade e Estado */}
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 15 }}>
          <div className="form-group">
            <label>Cidade *</label>
            <input
              type="text"
              value={form.cidade}
              onChange={(e) => setForm({ ...form, cidade: e.target.value })}
              placeholder="Ex: São Paulo"
            />
          </div>

          <div className="form-group">
            <label>Estado *</label>
            <input
              type="text"
              value={form.estado}
              onChange={(e) => {
                const valor = e.target.value.toUpperCase().slice(0, 2);
                setForm({ ...form, estado: valor });
              }}
              placeholder="SP"
              maxLength={2}
            />
          </div>
        </div>

        <p style={{ fontSize: 12, color: "#64748b", marginTop: 12, marginBottom: 0 }}>
          💡 Endereço da loja: preencha o CEP acima para buscar automaticamente.
        </p>
        </div>


        {/* ── Método de KM ─────────────────────────────────────────── */}
        <div style={{
          background: "#f8fafc",
          border: "1px solid #e2e8f0",
          borderRadius: 12,
          padding: "20px 24px",
          marginBottom: 24,
        }}>
          <h3 style={{ margin: "0 0 4px", fontSize: 16, fontWeight: 700, color: "#1e293b" }}>
            📏 Como registrar a distância percorrida
          </h3>
          <p style={{ margin: "0 0 16px", fontSize: 13, color: "#64748b" }}>
            Define o que acontece quando o entregador marca uma entrega como concluída.
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {/* Opção 1: Automático */}
            <label style={{
              display: "flex",
              gap: 14,
              alignItems: "flex-start",
              padding: "14px 16px",
              borderRadius: 10,
              border: `2px solid ${form.metodo_km_entrega === "auto_rota" ? "#2563eb" : "#e2e8f0"}`,
              backgroundColor: form.metodo_km_entrega === "auto_rota" ? "#eff6ff" : "#fff",
              cursor: "pointer",
              transition: "all 0.15s",
            }}>
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
                  ✨ Automático <span style={{ background: "#dcfce7", color: "#16a34a", fontSize: 11, fontWeight: 600, padding: "1px 7px", borderRadius: 999, marginLeft: 6 }}>Recomendado</span>
                </div>
                <div style={{ fontSize: 13, color: "#475569", lineHeight: 1.5 }}>
                  Se a rota foi otimizada, o sistema usa a distância calculada automaticamente — <strong>sem precisar de nenhuma ação do entregador</strong>. Se a rota não foi otimizada, o sistema pede para o entregador informar o km.
                </div>
                <div style={{ fontSize: 12, color: "#16a34a", fontWeight: 600, marginTop: 5 }}>Custo: zero</div>
              </div>
            </label>

            {/* Opção 2: Sempre manual */}
            <label style={{
              display: "flex",
              gap: 14,
              alignItems: "flex-start",
              padding: "14px 16px",
              borderRadius: 10,
              border: `2px solid ${form.metodo_km_entrega === "manual" ? "#2563eb" : "#e2e8f0"}`,
              backgroundColor: form.metodo_km_entrega === "manual" ? "#eff6ff" : "#fff",
              cursor: "pointer",
              transition: "all 0.15s",
            }}>
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
                  O entregador digita o km do hodômetro em cada entrega e ao finalizar a rota. Útil para quem precisa de controle rigoroso de quilometragem real.
                </div>
                <div style={{ fontSize: 12, color: "#16a34a", fontWeight: 600, marginTop: 5 }}>Custo: zero</div>
              </div>
            </label>

            {/* Opção 3: App (em breve) */}
            <div style={{
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
            }}>
              <input type="radio" disabled style={{ marginTop: 4, flexShrink: 0 }} />
              <div>
                <div style={{ fontWeight: 700, fontSize: 14, color: "#94a3b8", marginBottom: 3 }}>
                  📱 GPS via App Mobile
                  <span style={{ background: "#fef3c7", color: "#b45309", fontSize: 11, fontWeight: 600, padding: "1px 7px", borderRadius: 999, marginLeft: 6 }}>Em breve</span>
                </div>
                <div style={{ fontSize: 13, color: "#94a3b8", lineHeight: 1.5 }}>
                  O entregador usa o app no celular para rastrear toda a rota em tempo real via GPS — mesmo com a tela apagada. Distância real calculada automaticamente sem nenhuma ação manual.
                </div>
              </div>
            </div>
          </div>
        </div>

        <button
          type="submit"
          disabled={saving}
          style={{
            backgroundColor: "#2563eb",
            color: "white",
            padding: "12px 24px",
            border: "none",
            borderRadius: "6px",
            fontSize: "16px",
            fontWeight: "500",
            cursor: saving ? "not-allowed" : "pointer",
            opacity: saving ? 0.6 : 1,
            transition: "all 0.2s",
          }}
          onMouseOver={(e) => {
            if (!saving) e.target.style.backgroundColor = "#1d4ed8";
          }}
          onMouseOut={(e) => {
            if (!saving) e.target.style.backgroundColor = "#2563eb";
          }}
        >
          {saving ? "Salvando..." : "Salvar Configurações"}
        </button>
      </form>
    </div>
  );
}
