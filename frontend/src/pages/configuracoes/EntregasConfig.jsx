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
        });
        
        setEntregadores(pessoas.data ?? []);
      } catch (e) {
        console.error(e);
        alert("Erro ao carregar configurações de entrega");
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
            {entregadores.map((p) => (
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
