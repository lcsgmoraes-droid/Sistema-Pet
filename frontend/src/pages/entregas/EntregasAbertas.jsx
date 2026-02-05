import { useEffect, useState } from "react";
import { api } from "../../services/api";
import "./Entregas.css";

export default function EntregasAbertas() {
  const [loading, setLoading] = useState(true);
  const [vendas, setVendas] = useState([]);
  const [selecionadas, setSelecionadas] = useState([]);
  const [entregadores, setEntregadores] = useState([]);
  const [configEntrega, setConfigEntrega] = useState(null);
  
  // Modal criar rota
  const [showModal, setShowModal] = useState(false);
  const [vendaSelecionada, setVendaSelecionada] = useState(null);
  const [formRota, setFormRota] = useState({
    entregador_id: "",
    endereco_destino: "",
    distancia_prevista: "",
    moto_da_loja: false,
    observacoes: "",
  });

  useEffect(() => {
    carregarDados();
  }, []);

  async function carregarDados() {
    setLoading(true);
    try {
      const [vendasRes, entregadoresRes, configRes] = await Promise.all([
        api.get("/vendas", { params: { tem_entrega: true, sem_rota: true } }),
        api.get("/clientes", { 
          params: { 
            is_entregador: true, 
            entregador_ativo: true 
          } 
        }),
        api.get("/configuracoes/entregas").catch(() => ({ data: null })),
      ]);

      // Garantir que vendas seja sempre um array
      const vendasData = vendasRes.data;
      setVendas(Array.isArray(vendasData) ? vendasData : []);
      
      // Garantir que entregadores seja sempre um array
      const entregadoresData = entregadoresRes.data;
      setEntregadores(Array.isArray(entregadoresData) ? entregadoresData : []);
      
      setConfigEntrega(configRes.data);
    } catch (err) {
      console.error(err);
      alert("Erro ao carregar vendas com entrega");
      // Resetar para arrays vazios em caso de erro
      setVendas([]);
      setEntregadores([]);
    } finally {
      setLoading(false);
    }
  }

  function toggleVenda(vendaId) {
    setSelecionadas((prev) =>
      prev.includes(vendaId)
        ? prev.filter((id) => id !== vendaId)
        : [...prev, vendaId]
    );
  }

  function abrirModalCriarRota() {
    if (selecionadas.length === 0) {
      alert("Selecione pelo menos uma venda");
      return;
    }

    // Por enquanto, criar uma rota por venda
    const venda = vendas.find((v) => v.id === selecionadas[0]);
    setVendaSelecionada(venda);

    // Pré-preencher formulário
    const entregadorPadrao = configEntrega?.entregador_padrao_id || "";
    const entregador = entregadores.find((e) => e.id === entregadorPadrao);

    setFormRota({
      entregador_id: entregadorPadrao,
      endereco_destino: venda.endereco_entrega || "",
      distancia_prevista: venda.distancia_km || "",
      moto_da_loja: entregador?.moto_propria === false,
      observacoes: "",
    });

    setShowModal(true);
  }

  async function handleCriarRota(e) {
    e.preventDefault();

    if (!formRota.entregador_id) {
      alert("Selecione um entregador");
      return;
    }

    if (!formRota.distancia_prevista || parseFloat(formRota.distancia_prevista) <= 0) {
      alert("Informe a distância prevista");
      return;
    }

    try {
      await api.post("/rotas-entrega", {
        venda_id: vendaSelecionada.id,
        entregador_id: parseInt(formRota.entregador_id),
        endereco_destino: formRota.endereco_destino,
        distancia_prevista: parseFloat(formRota.distancia_prevista),
        moto_da_loja: formRota.moto_da_loja,
        observacoes: formRota.observacoes,
      });

      alert("Rota criada com sucesso!");
      setShowModal(false);
      setSelecionadas([]);
      carregarDados();
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || "Erro ao criar rota");
    }
  }

  function handleChangeEntregador(entregadorId) {
    setFormRota((prev) => ({ ...prev, entregador_id: entregadorId }));

    // Atualizar moto da loja baseado no entregador
    const entregador = entregadores.find((e) => e.id === parseInt(entregadorId));
    if (entregador) {
      setFormRota((prev) => ({
        ...prev,
        moto_da_loja: entregador.moto_propria === false,
      }));
    }
  }

  if (loading) return <div className="page">Carregando...</div>;

  return (
    <div className="page">
      <h1>Entregas em Aberto</h1>
      <p style={{ color: "#666", marginBottom: 20 }}>
        Vendas finalizadas com entrega que ainda não possuem rota criada
      </p>

      {!Array.isArray(vendas) || vendas.length === 0 ? (
        <div className="empty-state">
          <p>✅ Não há entregas pendentes</p>
        </div>
      ) : (
        <>
          <table className="table-entregas">
            <thead>
              <tr>
                <th style={{ width: 40 }}>
                  <input
                    type="checkbox"
                    checked={selecionadas.length === vendas.length}
                    onChange={(e) =>
                      setSelecionadas(
                        e.target.checked ? vendas.map((v) => v.id) : []
                      )
                    }
                  />
                </th>
                <th>Venda</th>
                <th>Cliente</th>
                <th>Endereço</th>
                <th>Distância (km)</th>
                <th>Valor Total</th>
              </tr>
            </thead>
            <tbody>
              {vendas.map((venda) => (
                <tr key={venda.id}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selecionadas.includes(venda.id)}
                      onChange={() => toggleVenda(venda.id)}
                    />
                  </td>
                  <td>#{venda.numero || venda.id}</td>
                  <td>{venda.cliente_nome || "N/A"}</td>
                  <td>{venda.endereco_entrega || "N/A"}</td>
                  <td>{venda.distancia_km || "-"}</td>
                  <td>R$ {parseFloat(venda.total || 0).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={{ marginTop: 20 }}>
            <button
              onClick={abrirModalCriarRota}
              disabled={selecionadas.length === 0}
              className="btn-primary"
            >
              Criar Rota ({selecionadas.length} selecionada{selecionadas.length !== 1 ? "s" : ""})
            </button>
          </div>
        </>
      )}

      {/* Modal Criar Rota */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Criar Rota de Entrega</h2>

            <form onSubmit={handleCriarRota}>
              <div className="form-group">
                <label>Venda</label>
                <input
                  type="text"
                  value={`#${vendaSelecionada.numero || vendaSelecionada.id} - ${vendaSelecionada.cliente_nome}`}
                  disabled
                />
              </div>

              <div className="form-group">
                <label>Entregador *</label>
                <select
                  value={formRota.entregador_id}
                  onChange={(e) => handleChangeEntregador(e.target.value)}
                  required
                >
                  <option value="">Selecione...</option>
                  {entregadores.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.nome}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Endereço de Destino</label>
                <input
                  type="text"
                  value={formRota.endereco_destino}
                  onChange={(e) =>
                    setFormRota({ ...formRota, endereco_destino: e.target.value })
                  }
                  placeholder="Endereço completo"
                />
              </div>

              <div className="form-group">
                <label>Distância Prevista (km) *</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={formRota.distancia_prevista}
                  onChange={(e) =>
                    setFormRota({ ...formRota, distancia_prevista: e.target.value })
                  }
                  required
                />
              </div>

              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={formRota.moto_da_loja}
                    onChange={(e) =>
                      setFormRota({ ...formRota, moto_da_loja: e.target.checked })
                    }
                  />
                  {" "}Moto da loja?
                </label>
                <small style={{ display: "block", color: "#666", marginTop: 5 }}>
                  Herdado do cadastro do entregador, mas pode ser alterado
                </small>
              </div>

              <div className="form-group">
                <label>Observações</label>
                <textarea
                  value={formRota.observacoes}
                  onChange={(e) =>
                    setFormRota({ ...formRota, observacoes: e.target.value })
                  }
                  rows={3}
                />
              </div>

              <div className="modal-actions">
                <button type="button" onClick={() => setShowModal(false)}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary">
                  Criar Rota
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
