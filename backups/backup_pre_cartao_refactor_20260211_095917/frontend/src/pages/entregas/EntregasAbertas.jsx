import { useEffect, useState } from "react";
import { api } from "../../services/api";
import "./Entregas.css";

export default function EntregasAbertas() {
  const [loading, setLoading] = useState(true);
  const [vendas, setVendas] = useState([]);
  const [selecionadas, setSelecionadas] = useState([]);
  const [configEntrega, setConfigEntrega] = useState(null);
  const [otimizando, setOtimizando] = useState(false);

  useEffect(() => {
    carregarDados();
  }, []);

  async function carregarDados() {
    setLoading(true);
    try {
      const [vendasRes, configRes] = await Promise.all([
        api.get("/rotas-entrega/vendas-pendentes/listar"),
        api.get("/configuracoes/entregas").catch(() => ({ data: null })),
      ]);

      setVendas(Array.isArray(vendasRes.data) ? vendasRes.data : []);
      setConfigEntrega(configRes.data);
    } catch (err) {
      console.error(err);
      alert("Erro ao carregar vendas pendentes");
      setVendas([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleOtimizarRotas() {
    if (vendas.length === 0) {
      alert("Não há vendas para otimizar");
      return;
    }

    if (!configEntrega || !configEntrega.logradouro) {
      alert("⚠️ Configure o endereço da loja em Configurações > Entregas antes de otimizar rotas");
      return;
    }

    const custoEstimado = "5 centavos";
    const confirmar = confirm(
      `⚠️ ATENÇÃO - ESTA OPERAÇÃO TEM CUSTO!\n\n` +
      `💵 Custo estimado: ${custoEstimado}\n` +
      `📍 Entregas a otimizar: ${vendas.length}\n` +
      `🗺️ Será feita 1 chamada ao Google Maps API\n` +
      `💾 A ordem será salva no banco (não cobra novamente)\n\n` +
      `Deseja continuar?`
    );
    
    if (!confirmar) {
      return;
    }

    setOtimizando(true);
    try {
      console.log("🗺️ Chamando endpoint de otimização...");
      const response = await api.post("/rotas-entrega/vendas-pendentes/otimizar");
      console.log("✅ Resposta da otimização:", response.data);
      
      alert(
        `✅ ROTAS OTIMIZADAS COM SUCESSO!\n\n` +
        `${response.data.message}\n\n` +
        `Total otimizado: ${response.data.total_otimizado || vendas.length} entregas`
      );
      
      await carregarDados();
    } catch (err) {
      console.error("❌ Erro ao otimizar:", err);
      console.error("Detalhes:", err.response?.data);
      const errorMsg = err.response?.data?.detail || "Erro ao otimizar rotas. Verifique se o Google Maps está configurado.";
      alert(`❌ ERRO AO OTIMIZAR ROTAS\n\n${errorMsg}`);
    } finally {
      setOtimizando(false);
    }
  }

  function toggleVenda(vendaId) {
    setSelecionadas((prev) =>
      prev.includes(vendaId)
        ? prev.filter((id) => id !== vendaId)
        : [...prev, vendaId]
    );
  }

  async function handleCriarRota() {
    if (selecionadas.length === 0) {
      alert("Selecione pelo menos uma entrega");
      return;
    }

    if (!confirm(`Deseja criar uma rota com ${selecionadas.length} entrega(s)?`)) {
      return;
    }

    try {
      setLoading(true);
      
      const vendasSelecionadas = vendas.filter(v => selecionadas.includes(v.id));
      
      const semEntregador = vendasSelecionadas.filter(v => !v.entregador_id);
      if (semEntregador.length > 0) {
        alert(`❌ As seguintes vendas não têm entregador atribuído:\n${semEntregador.map(v => v.numero_venda).join(', ')}\n\nAtribua um entregador antes de criar a rota.`);
        setLoading(false);
        return;
      }
      
      await api.post("/rotas-entrega/", {
        vendas_ids: selecionadas,
        entregador_id: vendasSelecionadas[0].entregador_id,
        moto_da_loja: false
      });

      alert(`✅ Rota criada com ${selecionadas.length} entrega(s)!\n\nAs entregas foram movidas para "Rotas de Entrega"`);
      setSelecionadas([]);
      carregarDados();
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || "Erro ao criar rota. Verifique se todas as entregas têm entregador atribuído.");
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <div className="page">Carregando...</div>;

  return (
    <div className="page">
      <h1>Entregas em Aberto</h1>
      <p style={{ color: "#666", marginBottom: 20 }}>
        Vendas com entrega que estão aguardando iniciar a rota
      </p>

      {!Array.isArray(vendas) || vendas.length === 0 ? (
        <div className="empty-state">
          <p>✅ Não há entregas pendentes</p>
        </div>
      ) : (
        <>
          <div style={{ marginBottom: 20, display: "flex", gap: 10, alignItems: "center" }}>
            <button
              onClick={handleOtimizarRotas}
              disabled={otimizando || loading}
              className="btn-secondary"
              title="Reorganizar entregas usando Google Maps para menor distância"
            >
              {otimizando ? "🔄 Otimizando..." : "🗺️ Otimizar Rotas"}
            </button>
            <span style={{ color: "#666", fontSize: "0.9em" }}>
              ℹ️ {vendas.filter(v => v.ordem_otimizada).length > 0 
                ? `${vendas.filter(v => v.ordem_otimizada).length} entregas já otimizadas. ` 
                : ""}
              Clique para ordenar pela rota mais eficiente
            </span>
          </div>

          <table className="table-entregas">
            <thead>
              <tr>
                <th style={{ width: 40 }}>
                  <input
                    type="checkbox"
                    checked={selecionadas.length === vendas.length && vendas.length > 0}
                    onChange={(e) =>
                      setSelecionadas(
                        e.target.checked ? vendas.map((v) => v.id) : []
                      )
                    }
                  />
                </th>
                <th>Ordem</th>
                <th>Venda</th>
                <th>Data da Venda</th>
                <th>Cliente</th>
                <th>Entregador</th>
                <th>Endereço</th>
                <th>Taxa Entrega</th>
                <th>Total</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {vendas.map((venda, index) => (
                <tr key={venda.id} style={{ 
                  backgroundColor: selecionadas.includes(venda.id) 
                    ? "#e3f2fd" 
                    : venda.ordem_otimizada ? "#f0f8ff" : "white" 
                }}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selecionadas.includes(venda.id)}
                      onChange={() => toggleVenda(venda.id)}
                    />
                  </td>
                  <td>
                    <strong style={{ 
                      color: venda.ordem_otimizada ? "#007bff" : "#999", 
                      fontSize: "1.1em" 
                    }}>
                      {index + 1}
                      {venda.ordem_otimizada && " 🗺️"}
                    </strong>
                  </td>
                  <td>{venda.numero_venda}</td>
                  <td style={{ fontSize: "0.9em" }}>
                    {venda.data_venda ? new Date(venda.data_venda).toLocaleDateString('pt-BR') : 'N/A'}
                  </td>
                  <td>{venda.cliente_nome}</td>
                  <td>
                    <span style={{ 
                      color: venda.entregador_nome ? "#28a745" : "#999",
                      fontWeight: venda.entregador_nome ? "600" : "normal"
                    }}>
                      {venda.entregador_nome || "Não atribuído"}
                    </span>
                  </td>
                  <td style={{ maxWidth: 300, fontSize: "0.9em" }}>{venda.endereco_entrega || "N/A"}</td>
                  <td>R$ {parseFloat(venda.taxa_entrega || 0).toFixed(2)}</td>
                  <td>R$ {parseFloat(venda.total || 0).toFixed(2)}</td>
                  <td>
                    <span style={{ 
                      padding: "4px 8px", 
                      borderRadius: 4, 
                      fontSize: 12, 
                      fontWeight: "bold",
                      color: "#fff",
                      backgroundColor: "#ffa500"
                    }}>
                      AGUARDANDO
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={{ marginTop: 20, display: "flex", gap: 10 }}>
            <button
              onClick={handleCriarRota}
              disabled={selecionadas.length === 0 || loading}
              className="btn-primary"
              style={{ 
                backgroundColor: selecionadas.length > 0 ? "#28a745" : "#ccc",
                cursor: selecionadas.length > 0 ? "pointer" : "not-allowed"
              }}
            >
              ✅ Criar Rota ({selecionadas.length} selecionada{selecionadas.length !== 1 ? "s" : ""})
            </button>
            <span style={{ color: "#666", fontSize: "0.9em", alignSelf: "center" }}>
              💡 Selecione as entregas e clique para criar uma rota
            </span>
          </div>
        </>
      )}
    </div>
  );
}
