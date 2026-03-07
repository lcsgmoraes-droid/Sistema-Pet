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

  if (loading) return <div>Carregando...</div>;

  return (
    <div className="page">
      <h1>Configurações de Entregas</h1>

      <form onSubmit={handleSave} style={{ maxWidth: 600 }}>
        <div className="form-group">
          <label>Entregador padrão</label>
          <select
            value={form.entregador_padrao_id}
            onChange={(e) =>
              setForm({ ...form, entregador_padrao_id: e.target.value })
            }
          >
            <option value="">Nenhum (escolher manualmente)</option>
            {Array.isArray(entregadores) && entregadores.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nome}
              </option>
            ))}
          </select>
          <p style={{ fontSize: 12, color: "#666", marginTop: 5 }}>
            Este entregador será pré-selecionado ao criar novas rotas.
          </p>
        </div>

        <hr style={{ margin: "30px 0", border: "none", borderTop: "1px solid #ddd" }} />

        <h3 style={{ marginBottom: 20 }}>Ponto Inicial Padrão da Rota</h3>

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

        <p style={{ fontSize: 12, color: "#666", marginTop: 15, marginBottom: 20 }}>
          Este endereço será usado como ponto de partida para calcular as rotas de entrega.
        </p>

        <hr style={{ margin: "30px 0", border: "none", borderTop: "1px solid #ddd" }} />

        <h3 style={{ marginBottom: 8 }}>Método de Registro ao Marcar Entregue</h3>
        <p style={{ fontSize: 13, color: "#666", marginBottom: 16 }}>
          Escolha como o sistema vai registrar o km percorrido quando o entregador clicar em ✅ Entregue.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {[
            {
              valor: "auto_rota",
              titulo: "🗺️ Distância da rota otimizada (recomendado)",
              descricao: "Usa automaticamente a distância calculada pelo Google Maps ao otimizar a rota. Nenhuma ação do entregador. Só funciona se a rota foi otimizada antes.",
              custo: "Custo: zero (usa dados já calculados)",
            },
            {
              valor: "gps",
              titulo: "📍 GPS do celular",
              descricao: "Captura as coordenadas exatas do celular no momento da entrega. O entregador só precisa aceitar a permissão de localização no navegador, uma única vez.",
              custo: "Custo: zero (usa o GPS do próprio telefone, sem chamada ao Google)",
            },
            {
              valor: "manual",
              titulo: "✏️ Preenchimento manual",
              descricao: "O entregador digita o km atual do odômetro da moto ao clicar em Entregue. Útil para empresas que precisam controlar o hodômetro com precisão real.",
              custo: "Custo: zero",
            },
          ].map((opcao) => (
            <label
              key={opcao.valor}
              style={{
                display: "flex",
                gap: 14,
                alignItems: "flex-start",
                padding: "14px 16px",
                borderRadius: 8,
                border: `2px solid ${form.metodo_km_entrega === opcao.valor ? "#2563eb" : "#e5e7eb"}`,
                backgroundColor: form.metodo_km_entrega === opcao.valor ? "#eff6ff" : "#fafafa",
                cursor: "pointer",
                transition: "all 0.15s",
              }}
            >
              <input
                type="radio"
                name="metodo_km_entrega"
                value={opcao.valor}
                checked={form.metodo_km_entrega === opcao.valor}
                onChange={(e) => setForm({ ...form, metodo_km_entrega: e.target.value })}
                style={{ marginTop: 3, accentColor: "#2563eb" }}
              />
              <div>
                <div style={{ fontWeight: "600", fontSize: 14, marginBottom: 4 }}>{opcao.titulo}</div>
                <div style={{ fontSize: 13, color: "#555", marginBottom: 4 }}>{opcao.descricao}</div>
                <div style={{ fontSize: 12, color: "#16a34a", fontWeight: "500" }}>{opcao.custo}</div>
              </div>
            </label>
          ))}
        </div>

        <p style={{ fontSize: 12, color: "#888", marginTop: 12, marginBottom: 24 }}>
          💡 Dica: todas as opções também capturam a posição GPS silenciosamente para o rastreio público do cliente (quando disponível).
        </p>

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
